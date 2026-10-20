"""Camino ÚNICO para aceptar un archivo nuevo en el tablero.

Lo usan la página "Actualizar datos" (carga manual) y la sincronización con SharePoint
(sharepoint.py). Así ambos pasan por las mismas protecciones, en el mismo orden:

  1. Validación con los VALORES que verá el tablero (data_only=True).
  2. Prueba de lectura con el mismo lector del tablero, sobre una copia temporal.
  3. Solo si ambas pasan: copia de la versión anterior, escritura del archivo nuevo,
     limpieza de la caché y respaldo en Mongo (si está configurado).

Si algo falla en 1 o 2, el archivo anterior queda intacto.
"""
import io
import os
import shutil
import tempfile

import openpyxl

import data_sources as ds
import respaldo
import validators as val


def fuentes():
    """Las 8 fuentes del tablero. Es una función (y no una lista fija) para que las rutas
    se lean en el momento de usarlas: así los tests pueden redirigirlas."""
    return [
        dict(clave="recaudo", nombre="Recaudo", archivo=ds.F_RECAUDO, validador=val.validar_recaudo, cache=ds.leer_recaudo,
             descripcion="Proyeccion_Recaudo.xlsx — usado en la página principal (rubros 14 a 19)."),
        dict(clave="inventario", nombre="Inventario / Ventas", archivo=ds.F_INVENTARIO, validador=val.validar_inventario,
             cache=ds.leer_inventario,
             descripcion="Inventario_2026.xlsx — usado en la página principal (rubros 8 a 13, 20, 21)."),
        dict(clave="conciliacion", nombre="Conciliación SISMO ↔ Wava", archivo=ds.F_CONCILIACION, validador=val.validar_conciliacion,
             cache=ds.leer_conciliacion, solo_directores=True,
             descripcion="Cruce_SISMO_Wava.xlsx — panel de conciliación en la página principal."),
        dict(clave="tesoreria", nombre="Tesorería", archivo=ds.F_TESORERIA, validador=val.validar_tesoreria,
             cache=ds.leer_tesoreria, solo_directores=True, alias=["Flujo de pagos deudas.xlsx"],
             descripcion="Flujo_Pagos_Deudas.xlsx — página Tesorería."),
        dict(clave="rrhh", nombre="RRHH / Nómina", archivo=ds.F_RRHH, validador=val.validar_rrhh,
             cache=ds.leer_rrhh, solo_directores=True,
             descripcion="Control_RRHH_Nomina_RODDOS_2026.xlsx — página RRHH."),
        dict(clave="embudo", nombre="Embudo comercial (Marketing / leads)", archivo=ds.F_EMBUDO, validador=val.validar_embudo,
             cache=ds.leer_embudo,
             descripcion="Embudo_Comercial_RODDOS.xlsx — rubros 1 a 7 de la página principal. "
                         "Este es el único que empieza vacío: descarga la plantilla en la "
                         "página principal si aún no la tienes."),
        dict(clave="metas", nombre="Metas del mes", archivo=ds.F_METAS, validador=val.validar_metas,
             cache=ds.leer_metas, solo_directores=True,
             descripcion="Metas_RODDOS.xlsx — objetivos que fija la dirección cada mes "
                         "(ventas, % aprobación, % agendas, tope de mora, gasto fijo). "
                         "Agrega una fila nueva cada mes, no borres las anteriores."),
        dict(clave="cobranza", nombre="Cobranza semanal", archivo=ds.F_COBRANZA, validador=val.validar_cobranza_semanal,
             cache=ds.leer_cobranza_semanal,
             descripcion="Cobranza_Semanal.xlsx — seguimiento de las cuotas a cobrar de la semana "
                         "(hojas: Dashboard, Cuotas de la semana, Cuotas vencidas). Marca 'Pagada' a medida "
                         "que cobras; alimenta la sección Cobranza de la semana en la página principal."),
    ]


def _probar_lectura(fuente, contenido):
    """Lee el archivo nuevo con el lector del tablero sobre una copia temporal.
    Devuelve None si todo bien, o la excepción."""
    fd, ruta_tmp = tempfile.mkstemp(suffix=".xlsx", prefix="prueba_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contenido)
        fuente["cache"](ruta=ruta_tmp)
        return None
    except Exception as e:
        return e
    finally:
        fuente["cache"].clear()  # no dejar en caché la lectura de la copia temporal
        try:
            os.remove(ruta_tmp)
        except OSError:
            pass


def revisar(fuente, contenido):
    """Pasos 1 y 2, sin guardar nada. Devuelve la lista de errores (vacía = se puede aceptar)."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
    except Exception as e:
        return [f"No se pudo abrir el archivo como Excel ({type(e).__name__}: {e})."]
    errores = fuente["validador"](wb)
    if errores:
        return errores
    fallo = _probar_lectura(fuente, contenido)
    if fallo is not None:
        return [f"El archivo tiene las hojas y columnas esperadas, pero el tablero no lo pudo leer "
                f"({type(fallo).__name__}: {fallo}). Revisa que no tenga celdas con error "
                "(#¡REF!, #¡VALOR!) ni filas de encabezado movidas."]
    return []


def procesar(fuente, contenido):
    """Revisa el archivo y, si está bien, reemplaza al anterior.

    Devuelve dict(ok=bool, errores=[...], aviso=str o None). `aviso` se llena cuando el archivo
    se aceptó pero el respaldo en Mongo falló (el tablero ya lo muestra igual)."""
    errores = revisar(fuente, contenido)
    if errores:
        return dict(ok=False, errores=errores, aviso=None)

    destino = fuente["archivo"]
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if os.path.exists(destino):
        carpeta_versiones = os.path.join(os.path.dirname(destino), "versiones")
        os.makedirs(carpeta_versiones, exist_ok=True)
        shutil.copy2(destino, os.path.join(carpeta_versiones, os.path.basename(destino) + ".anterior.xlsx"))
    with open(destino, "wb") as f:
        f.write(contenido)
    fuente["cache"].clear()

    aviso = None
    db = ds.db_respaldo()
    if db is not None:
        try:
            respaldo.guardar(db, os.path.basename(destino), contenido)
        except Exception as e:  # PyMongoError u otro: el archivo ya quedó cargado
            aviso = f"Se cargó, pero NO quedó respaldado en la nube: {e}."
    return dict(ok=True, errores=[], aviso=aviso)
