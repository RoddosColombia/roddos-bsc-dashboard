"""Revisa Excel reales con las MISMAS reglas de la página "Actualizar datos",
sin subir nada y sin tocar MongoDB. Úsalo antes de publicar cambios en los
validadores, o cuando un archivo sea rechazado y quieras ver el detalle.

Uso (desde la raíz del proyecto):
    python scripts/verificar_archivos.py                  # revisa data_raw/
    python scripts/verificar_archivos.py "C:/ruta/a/1 Fuentes al día"

Los archivos deben tener los nombres que usa la app (Proyeccion_Recaudo.xlsx,
Inventario_2026.xlsx...). Los que no estén en la carpeta se reportan como faltantes.
"""
import logging
import os
import sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)
import warnings  # noqa: E402

# openpyxl avisa que no soporta algunas extensiones (formato condicional, validación de datos).
# Solo importa al GUARDAR, y este script nunca guarda: los archivos quedan intactos.
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
logging.disable(logging.WARNING)  # Streamlit avisa "missing ScriptRunContext" fuera de una app: inofensivo

import openpyxl  # noqa: E402

import data_sources as ds  # noqa: E402
import validators as val  # noqa: E402

# Fuera de una app, Streamlit avisa "missing ScriptRunContext" en cada lectura: es inofensivo.
for _nombre in list(logging.root.manager.loggerDict):
    if _nombre.startswith("streamlit"):
        logging.getLogger(_nombre).setLevel(logging.CRITICAL)

FUENTES = [
    ("Proyeccion_Recaudo.xlsx", "recaudo", ds.leer_recaudo),
    ("Inventario_2026.xlsx", "inventario", ds.leer_inventario),
    ("Cruce_SISMO_Wava.xlsx", "conciliacion", ds.leer_conciliacion),
    ("Flujo_Pagos_Deudas.xlsx", "tesoreria", ds.leer_tesoreria),
    ("Control_RRHH_Nomina_RODDOS_2026.xlsx", "rrhh", ds.leer_rrhh),
    ("Embudo_Comercial_RODDOS.xlsx", "embudo", ds.leer_embudo),
    ("Metas_RODDOS.xlsx", "metas", ds.leer_metas),
    ("Cobranza_Semanal.xlsx", "cobranza", ds.leer_cobranza_semanal),
]


# Nombres con los que los archivos pueden venir de SharePoint, además del nombre que usa la app.
ALIAS = {
    "Flujo_Pagos_Deudas.xlsx": ["Flujo de pagos deudas.xlsx"],
}


def _normalizar(nombre):
    return nombre.lower().replace(" ", "").replace("_", "")


def _buscar(carpeta, nombre):
    """Busca el archivo en la carpeta y sus subcarpetas (al descomprimir un zip suele quedar
    una carpeta de más), sin importar mayúsculas, espacios ni guiones bajos."""
    buscados = {_normalizar(n) for n in [nombre] + ALIAS.get(nombre, [])}
    for raiz, _, archivos in os.walk(carpeta):
        for a in archivos:
            if _normalizar(a) in buscados and not a.startswith("~$"):
                return os.path.join(raiz, a)
    return None


def revisar(carpeta):
    carpeta = os.path.abspath(carpeta)
    if not os.path.isdir(carpeta):
        print(f"✗ La carpeta no existe: {carpeta}")
        print("  Revisa la ruta. Si tu Escritorio está en OneDrive, suele ser:")
        print(r"  C:\Users\<usuario>\OneDrive\Escritorio\<carpeta>")
        return 1

    print(f"Revisando: {carpeta}\n")
    revisados, mal, faltan = 0, 0, []
    for nombre, clave, lector in FUENTES:
        ruta = _buscar(carpeta, nombre)
        if ruta is None:
            faltan.append(nombre)
            print(f"  ·  {nombre}: no se encontró")
            continue
        revisados += 1
        try:
            errores = val.VALIDADORES[clave](openpyxl.load_workbook(ruta, data_only=True))
            if not errores:
                lector(ruta=ruta)  # misma "prueba de lectura" que hace la página antes de reemplazar
        except Exception as e:
            errores = [f"El tablero no lo pudo leer: {type(e).__name__}: {e}"]
        etiqueta = os.path.relpath(ruta, carpeta)
        if errores:
            mal += 1
            print(f"  ✗  {etiqueta}: {len(errores)} problema(s)")
            for err in errores:
                print(f"       - {err}")
        else:
            print(f"  ✓  {etiqueta}: OK")

    if faltan:
        encontrados = sorted(os.path.relpath(os.path.join(r, a), carpeta)
                             for r, _, archs in os.walk(carpeta) for a in archs
                             if a.lower().endswith((".xlsx", ".xlsm")) and not a.startswith("~$"))
        print("\nArchivos de Excel que sí hay en la carpeta (y subcarpetas):")
        for e in encontrados or ["(ninguno)"]:
            print(f"     {e}")

    print()
    if revisados == 0:
        print("No se revisó ningún archivo: no se encontró ninguno con los nombres esperados.")
        return 1
    if mal:
        print(f"{mal} de {revisados} archivo(s) revisados con problemas.")
    else:
        print(f"Los {revisados} archivo(s) revisados están en orden.")
    if faltan:
        print(f"Faltan {len(faltan)}: {', '.join(faltan)}")
    return 1 if (mal or faltan) else 0


if __name__ == "__main__":
    sys.exit(revisar(sys.argv[1] if len(sys.argv) > 1 else ds.RAW_DIR))
