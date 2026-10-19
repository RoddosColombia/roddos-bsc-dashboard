"""La promesa del instructivo: "si el archivo tiene problemas, la app NO reemplaza nada".

1. Cada Excel de prueba bueno pasa su validador.
2. Cada daño típico se rechaza con un mensaje entendible.
3. Para los daños que antes pasaban la validación y tumbaban el tablero, se
   comprueba también que el lector efectivamente se cae: así sabemos que la
   regla nueva protege algo real y no es un adorno.
"""
import datetime
import io

import openpyxl
import pytest

import data_sources as ds
import fixtures_excel as fx
import validators as val

FUTURO = datetime.datetime.now() + datetime.timedelta(days=30)


def _como_se_sube(wb):
    """Igual que la página Actualizar datos: guardar y reabrir con data_only=True."""
    b = io.BytesIO()
    wb.save(b)
    b.seek(0)
    return openpyxl.load_workbook(b, data_only=True)


def _borrar_columna(ws, fila_header, nombre):
    for c in ws[fila_header]:
        if c.value == nombre:
            ws.delete_cols(c.column)
            return
    raise AssertionError(f"no existe la columna {nombre}")


def _poner(ws, fila_header, nombre, fila, valor):
    col = next(c.column for c in ws[fila_header] if c.value == nombre)
    ws.cell(fila, col, valor)


def _vaciar(ws, celdas):
    for c in celdas:
        ws[c] = None


# ---------------------------------------------------------------- 1. los buenos pasan

@pytest.mark.parametrize("clave, fabrica", [
    ("recaudo", fx.wb_recaudo), ("inventario", fx.wb_inventario), ("conciliacion", fx.wb_conciliacion),
    ("tesoreria", fx.wb_tesoreria), ("rrhh", fx.wb_rrhh), ("embudo", fx.wb_embudo),
    ("metas", fx.wb_metas), ("cobranza", fx.wb_cobranza),
])
def test_archivo_bueno_pasa(clave, fabrica):
    assert val.VALIDADORES[clave](_como_se_sube(fabrica())) == []


# ---------------------------------------------------------------- 2. los dañados se rechazan

def _recaudo_sin(col):
    def dañar(wb):
        _borrar_columna(wb["Detalle Cuotas"], 2, col)
    return dañar


CASOS = [
    # (id, validador, fábrica, daño, texto esperado en el error)
    ("recaudo sin Fecha pago SISMO", "recaudo", fx.wb_recaudo, _recaudo_sin("Fecha pago SISMO"), "Fecha pago SISMO"),
    ("recaudo sin Pagado SISMO", "recaudo", fx.wb_recaudo, _recaudo_sin("Pagado SISMO"), "Pagado SISMO"),
    ("recaudo sin Saldo a cobrar", "recaudo", fx.wb_recaudo, _recaudo_sin("Saldo a cobrar"), "Saldo a cobrar"),
    ("recaudo sin hoja", "recaudo", fx.wb_recaudo, lambda wb: wb.remove(wb["Resumen Semanal"]), "Resumen Semanal"),
    ("recaudo sin recalcular", "recaudo", fx.wb_recaudo,
     lambda wb: _vaciar(wb["Dashboard"], val.RECAUDO_CELDAS_DASHBOARD), "Ctrl+S"),
    ("recaudo celda con error", "recaudo", fx.wb_recaudo,
     lambda wb: wb["Dashboard"].__setitem__("H5", "#REF!"), "H5"),
    ("recaudo pago en el futuro", "recaudo", fx.wb_recaudo,
     lambda wb: _poner(wb["Detalle Cuotas"], 2, "Fecha pago SISMO", 3, FUTURO), "fecha futura"),
    ("recaudo pagado con texto", "recaudo", fx.wb_recaudo,
     lambda wb: _poner(wb["Detalle Cuotas"], 2, "Pagado SISMO", 3, "quinientos mil"), "debe ser un número"),
    ("recaudo fecha como texto", "recaudo", fx.wb_recaudo,
     lambda wb: _poner(wb["Detalle Cuotas"], 2, "Fecha prog.", 3, "01/10/2026"), "fecha de Excel"),
    ("recaudo sin cuotas", "recaudo", fx.wb_recaudo,
     lambda wb: wb["Detalle Cuotas"].delete_rows(3, 500), "ninguna cuota"),

    ("inventario sin columna Estado", "inventario", fx.wb_inventario,
     lambda wb: _borrar_columna(wb["Inventario motos"], 1, "Estado"), "Estado"),
    ("inventario sin recalcular", "inventario", fx.wb_inventario,
     lambda wb: _vaciar(wb["Dashboard"], val.INVENTARIO_CELDAS_DASHBOARD), "Ctrl+S"),

    ("conciliación sin hoja de pagos", "conciliacion", fx.wb_conciliacion,
     lambda wb: wb.remove(wb["Pagos sin registrar SISMO"]), "Pagos sin registrar SISMO"),

    ("tesorería ingresos sin Valor", "tesoreria", fx.wb_tesoreria,
     lambda wb: _borrar_columna(wb["Base real ingresos"], 1, "Valor"), "Valor"),
    ("tesorería egresos sin categoría", "tesoreria", fx.wb_tesoreria,
     lambda wb: _borrar_columna(wb["Base real egresos"], 1, "Categoría normalizada"), "Categoría normalizada"),
    ("tesorería sin fecha de corte", "tesoreria", fx.wb_tesoreria,
     lambda wb: (wb["Tablero mes"].__setitem__("J4", "sin fecha"), wb["Base real egresos"].delete_rows(2, 500)),
     "fecha de corte"),
    ("tesorería sin recalcular", "tesoreria", fx.wb_tesoreria,
     lambda wb: _vaciar(wb["Tablero mes"], ["B8", "E8", "H8", "E14"]), "Ctrl+S"),

    ("rrhh nómina sin costo total", "rrhh", fx.wb_rrhh,
     lambda wb: _borrar_columna(wb["NominaMensual"], 3, "COSTO TOTAL EMPRESA/MES"), "COSTO TOTAL EMPRESA/MES"),
    ("rrhh vacaciones sin días", "rrhh", fx.wb_rrhh,
     lambda wb: _borrar_columna(wb["Vacaciones"], 3, "Días pendientes"), "Días pendientes"),
    ("rrhh sin recalcular", "rrhh", fx.wb_rrhh,
     lambda wb: _vaciar(wb["NominaMensual"], [f"F{r}" for r in range(4, 8)]), "Ctrl+S"),
    ("rrhh costo con texto", "rrhh", fx.wb_rrhh,
     lambda wb: wb["NominaMensual"].cell(4, 6, "pendiente"), "debe ser un número"),

    ("embudo sin Fecha decision", "embudo", fx.wb_embudo,
     lambda wb: _borrar_columna(wb["Embudo_Diario"], 1, "Fecha decision"), "Fecha decision"),
    ("embudo sin Decision", "embudo", fx.wb_embudo,
     lambda wb: _borrar_columna(wb["Embudo_Diario"], 1, "Decision"), "Decision"),
    ("embudo fecha como texto", "embudo", fx.wb_embudo,
     lambda wb: _poner(wb["Embudo_Diario"], 1, "Fecha agenda visita", 3, "mañana"), "fecha de Excel"),
    ("embudo canal fuera de lista", "embudo", fx.wb_embudo,
     lambda wb: _poner(wb["Embudo_Diario"], 1, "Canal", 3, "Volante"), "no está en la lista"),

    ("metas mes como texto", "metas", fx.wb_metas, lambda wb: wb["Metas"].cell(6, 1, "Octubre 2026"), "fecha de Excel"),
    ("metas mes repetido", "metas", fx.wb_metas,
     lambda wb: wb["Metas"].cell(6, 1, datetime.datetime(2026, 9, 1)), "ya está en la fila"),
    ("metas vacías", "metas", fx.wb_metas, lambda wb: wb["Metas"].delete_rows(5, 10), "ninguna fila"),
    ("metas porcentaje 60 en vez de 60%", "metas", fx.wb_metas, lambda wb: wb["Metas"].cell(5, 3, 60), "porcentaje"),

    ("cobranza Pagada con valor raro", "cobranza", fx.wb_cobranza,
     lambda wb: wb["Cuotas de la semana"].cell(2, 5, "tal vez"), "'Pagada'"),
    ("cobranza valor con texto", "cobranza", fx.wb_cobranza,
     lambda wb: wb["Cuotas de la semana"].cell(2, 4, "500 mil"), "debe ser un número"),
]


@pytest.mark.parametrize("clave, fabrica, dañar, esperado", [c[1:] for c in CASOS], ids=[c[0] for c in CASOS])
def test_archivo_dañado_se_rechaza(clave, fabrica, dañar, esperado):
    wb = fabrica()
    dañar(wb)
    errores = val.VALIDADORES[clave](_como_se_sube(wb))
    assert errores, "el validador dejó pasar un archivo dañado"
    assert any(esperado in e for e in errores), errores


def test_errores_repetidos_se_resumen():
    """100 filas malas no deben llenar la pantalla con 100 mensajes."""
    wb = fx.wb_recaudo()
    ws = wb["Detalle Cuotas"]
    filas_con_cuota = range(3, ws.max_row + 1)
    for fila in filas_con_cuota:
        _poner(ws, 2, "Pagado SISMO", fila, "error")
    errores = val.validar_recaudo(_como_se_sube(wb))
    assert len(errores) == val.MAX_ERRORES_POR_COLUMNA + 1
    assert f"{len(filas_con_cuota) - val.MAX_ERRORES_POR_COLUMNA} fila(s) más" in errores[-1]


def test_pagada_acepta_si_no_casilla_y_vacio():
    wb = fx.wb_cobranza()
    for fila, v in enumerate(["Sí", "si", "X", "No", True, None], start=2):
        wb["Cuotas de la semana"].cell(fila, 5, v)
    assert val.validar_cobranza_semanal(_como_se_sube(wb)) == []


# ---------------------------------------------------------------- 3. las reglas nuevas protegen algo real

@pytest.mark.parametrize("nombre, fabrica, dañar, lector", [
    ("Proyeccion_Recaudo.xlsx", fx.wb_recaudo, _recaudo_sin("Fecha pago SISMO"), "metricas"),
    ("Cruce_SISMO_Wava.xlsx", fx.wb_conciliacion,
     lambda wb: wb.remove(wb["Pagos sin registrar SISMO"]), "leer_conciliacion"),
    ("Flujo_Pagos_Deudas.xlsx", fx.wb_tesoreria,
     lambda wb: _borrar_columna(wb["Base real ingresos"], 1, "Es reverso de egreso"), "leer_tesoreria"),
    ("Control_RRHH_Nomina_RODDOS_2026.xlsx", fx.wb_rrhh,
     lambda wb: _borrar_columna(wb["Vacaciones"], 3, "Días pendientes"), "leer_rrhh"),
])
def test_sin_la_regla_nueva_el_tablero_se_caia(datos_prueba, reemplazar, nombre, fabrica, dañar, lector):
    import metricas as mx

    wb = fabrica()
    dañar(wb)
    reemplazar(nombre, wb)
    with pytest.raises(Exception):
        mx.construir_metricas() if lector == "metricas" else getattr(ds, lector)()
