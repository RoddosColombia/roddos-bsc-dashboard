"""Casos encontrados al verificar los Excel REALES de SharePoint (19 oct 2026).

Antes, el tablero (incluida la versión publicada) rechazaba el Embudo y las Metas reales.
Cada test reproduce, con datos inventados, una situación que apareció en los archivos reales.
"""
import datetime
import io

import openpyxl
import pytest

import data_sources as ds
import formatos
import fixtures_excel as fx
import validators as val


def _como_se_sube(wb):
    b = io.BytesIO()
    wb.save(b)
    b.seek(0)
    return openpyxl.load_workbook(b, data_only=True)


def _col(nombre):
    return fx.EMBUDO_COLUMNAS.index(nombre) + 1


# ---------------------------------------------------------------- Embudo

def test_visita_agendada_sin_estado_no_rechaza_el_archivo():
    """77 filas reales tenían fecha de agenda y 'Estado agenda' vacío (visitas aún pendientes)."""
    wb = fx.wb_embudo()
    ws = wb["Embudo_Diario"]
    for fila in range(3, ws.max_row + 1):
        if ws.cell(fila, _col("Fecha agenda visita")).value is not None:
            ws.cell(fila, _col("Estado agenda")).value = None
    assert val.validar_embudo(_como_se_sube(wb)) == []


@pytest.mark.parametrize("texto, esperado", [
    ("27-07-2026", datetime.datetime(2026, 7, 27)),   # tal cual apareció en la fila 94
    ("21/09/2026", datetime.datetime(2026, 9, 21)),   # tal cual apareció en la fila 98
    ("05/09/2026", datetime.datetime(2026, 9, 5)),    # día primero: 5 de septiembre, NO 9 de mayo
    ("5.9.2026", datetime.datetime(2026, 9, 5)),
    ("2026-09-05", datetime.datetime(2026, 9, 5)),
    ("31/02/2026", None),                             # no existe
    ("mañana", None),
])
def test_fechas_escritas_a_mano(texto, esperado):
    assert formatos.parse_fecha_texto(texto) == esperado


def test_embudo_con_fechas_en_texto_pasa_y_se_lee_con_el_dia_primero(datos_prueba, reemplazar):
    wb = fx.wb_embudo()
    ws = wb["Embudo_Diario"]
    ws.cell(3, _col("Fecha formulario")).value = "27-07-2026"
    ws.cell(3, _col("Fecha decision")).value = "05/09/2026"
    assert val.validar_embudo(_como_se_sube(wb)) == []
    reemplazar("Embudo_Comercial_RODDOS.xlsx", wb)
    df = ds.leer_embudo()
    assert df.loc[0, "Fecha formulario"] == datetime.datetime(2026, 7, 27)
    assert df.loc[0, "Fecha decision"] == datetime.datetime(2026, 9, 5)


def test_filas_que_solo_traen_la_fecha_se_ignoran(datos_prueba, reemplazar):
    """Filas 127+ reales: fecha pero sin nombre. Si no tienen ningún otro dato, son filas vacías."""
    wb = fx.wb_embudo()
    ws = wb["Embudo_Diario"]
    for k in range(5):
        ws.append([datetime.datetime(2026, 10, 1 + k)] + [None] * (len(fx.EMBUDO_COLUMNAS) - 1))
    assert val.validar_embudo(_como_se_sube(wb)) == []
    reemplazar("Embudo_Comercial_RODDOS.xlsx", wb)
    assert len(ds.leer_embudo()) == 12          # no se cuentan como leads


def test_fila_con_datos_pero_sin_nombre_sigue_siendo_error():
    wb = fx.wb_embudo()
    fila = [None] * len(fx.EMBUDO_COLUMNAS)
    fila[0], fila[_col("Canal") - 1] = datetime.datetime(2026, 10, 2), "Referido"
    wb["Embudo_Diario"].append(fila)
    errores = val.validar_embudo(_como_se_sube(wb))
    assert any("falta el nombre" in e for e in errores)


# ---------------------------------------------------------------- Metas

def _metas_con_encabezado_en_fila(n):
    """Metas con los encabezados en la fila n (la plantilla los tiene en la 4)."""
    original = fx.wb_metas()["Metas"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Metas"
    for desplazamiento, fila in enumerate(original.iter_rows(min_row=4, values_only=True)):
        for j, v in enumerate(fila, start=1):
            ws.cell(n + desplazamiento, j, v)
    return wb


@pytest.mark.parametrize("fila", [1, 2, 6])
def test_metas_con_encabezados_en_otra_fila(datos_prueba, reemplazar, fila):
    wb = _metas_con_encabezado_en_fila(fila)
    assert val.validar_metas(_como_se_sube(wb)) == []
    reemplazar("Metas_RODDOS.xlsx", wb)
    assert ds.leer_metas(fx.HOY)["ventas"] == 30


def test_metas_sin_columnas_dice_que_encabezados_encontro():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Metas"
    ws.append(["Periodo", "Ventas"])
    errores = val.validar_metas(_como_se_sube(wb))
    assert "Encabezados encontrados" in errores[0] and "Periodo" in errores[0]


# ---------------------------------------------------------------- Inventario maestro (Operaciones)

def test_inventario_con_ref_en_celda_secundaria_se_acepta(datos_prueba, reemplazar):
    """Caso real (20 oct): el maestro 'Inventario 2026.xlsx' de Operaciones trae #REF! en H7
    (plan separe no activados), una celda que ningún indicador usa."""
    wb = fx.wb_inventario()
    wb["Dashboard"]["H7"] = "#REF!"
    wb["Dashboard"]["D18"] = "#N/A"
    assert val.validar_inventario(_como_se_sube(wb)) == []
    reemplazar("Inventario_2026.xlsx", wb)
    inv = ds.leer_inventario()
    assert inv["hoy"]["plan_separe_no_activados"] is None and inv["hoy"]["disp_sport"] is None
    import metricas as mx
    M = mx.construir_metricas()["metricas"]
    assert "Sport —" in M["inventario_disponible"]["extra"]          # "—", no "None" ni un 0 falso
    assert M["ventas"]["mes"] == 12


@pytest.mark.parametrize("celda", ["B7", "D7", "F7", "H18"])
def test_inventario_con_error_en_celda_critica_se_rechaza(celda):
    wb = fx.wb_inventario()
    wb["Dashboard"][celda] = "#REF!"
    errores = val.validar_inventario(_como_se_sube(wb))
    assert any(celda in e for e in errores)
