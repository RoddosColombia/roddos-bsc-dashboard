"""Los lectores (data_sources.py) y las métricas (metricas.py) contra los Excel de prueba.

Los valores esperados salen de cómo se construyen los datos en fixtures_excel.py,
así que se pueden comprobar a mano.
"""
import datetime

import pytest

import data_sources as ds
import fixtures_excel as fx
import metricas as mx
import objetivos as obj

HOY = fx.HOY
CUOTA = fx.CUOTA


# ---------------------------------------------------------------- Recaudo + métricas

def test_metricas_de_recaudo(datos_prueba):
    data = mx.construir_metricas()
    M = data["metricas"]
    assert data["hoy_recaudo"] == HOY
    assert data["avisos"] == []
    assert M["pagos_dinero"]["mes"] == HOY.day * CUOTA       # una pagada por día
    assert M["pagos_dinero"]["ayer"] == CUOTA
    assert M["vencidas_num"]["mes"] == HOY.day               # una pendiente por día ya vencida
    assert M["vencidas_dinero"]["mes"] == HOY.day * CUOTA
    assert M["mora_total"]["mes"] == 4_200_000


def test_recaudo_lee_por_nombre_de_columna_no_por_posicion(datos_prueba, reemplazar):
    """Si SISMO cambia el orden de las columnas, el tablero no debe enloquecer."""
    wb = fx.wb_recaudo()
    wb["Detalle Cuotas"].move_range("E2:E200", cols=8)   # 'Cód. crédito' de la columna E a la M
    wb["Detalle Cuotas"].delete_cols(5)
    reemplazar("Proyeccion_Recaudo.xlsx", wb)
    M = mx.construir_metricas()["metricas"]
    assert M["pagos_dinero"]["mes"] == HOY.day * CUOTA


def test_semanas_y_dias_sin_tope(datos_prueba):
    rec = ds.leer_recaudo()
    assert list(rec["semanal"]["semana"]) == [f"Sem {n}" for n in range(36, 42)]
    assert len(rec["diario"]) == HOY.day


# ---------------------------------------------------------------- Inventario

def test_inventario(datos_prueba):
    inv = ds.leer_inventario()
    assert inv["hoy"]["actualizado_fecha"] == HOY
    assert inv["motos_disponibles_raw"] == 12
    assert inv["motos_en_site"] == 14
    assert list(inv["mensual"]["mes"])[-1] == "Octubre"      # la fila TOTAL no cuenta como mes
    assert inv["mensual"]["activadas"].sum() == 80


def test_inventario_acepta_fecha_de_excel_en_k2(datos_prueba, reemplazar):
    wb = fx.wb_inventario()
    wb["Dashboard"]["K2"] = datetime.datetime(2026, 10, 7)
    reemplazar("Inventario_2026.xlsx", wb)
    assert ds.leer_inventario()["hoy"]["actualizado_fecha"] == datetime.date(2026, 10, 7)


# ---------------------------------------------------------------- Opcionales que fallan no tumban nada

def test_conciliacion_dañada_deja_aviso_y_el_resto_funciona(datos_prueba, reemplazar):
    wb = fx.wb_conciliacion()
    wb.remove(wb["Pagos sin registrar SISMO"])
    reemplazar("Cruce_SISMO_Wava.xlsx", wb)
    data = mx.construir_metricas()
    assert len(data["avisos"]) == 1 and "Cruce_SISMO_Wava.xlsx" in data["avisos"][0]
    assert data["metricas"]["pagos_dinero"]["mes"] == HOY.day * CUOTA


def test_embudo_dañado_deja_aviso_y_rubros_sin_dato(datos_prueba, reemplazar):
    wb = fx.wb_embudo()
    ws = wb["Embudo_Diario"]
    ws.delete_cols(fx.EMBUDO_COLUMNAS.index("Decision") + 1)
    reemplazar("Embudo_Comercial_RODDOS.xlsx", wb)
    data = mx.construir_metricas()
    assert any("Embudo_Comercial_RODDOS.xlsx" in a for a in data["avisos"])
    assert data["metricas"]["leads"]["mes"] is None
    assert data["metricas"]["ventas"]["mes"] == 12


def test_embudo_con_datos(datos_prueba):
    M = mx.construir_metricas()["metricas"]
    assert M["leads"]["mes"] == 12
    assert M["aprobados_rechazados"]["mes"] == 12
    assert M["pct_aprobacion"]["mes"] == pytest.approx(8 / 12, abs=1e-4)


# ---------------------------------------------------------------- Metas

def test_metas_del_mes(datos_prueba):
    assert ds.leer_metas(HOY)["ventas"] == 30
    assert ds.leer_metas(datetime.date(2026, 9, 15))["ventas"] == 100
    assert ds.leer_metas(datetime.datetime(2026, 10, 9, 8, 0))["ventas"] == 30  # acepta datetime


def test_metas_ignora_fila_con_mes_en_texto(datos_prueba, reemplazar):
    wb = fx.wb_metas()
    wb["Metas"].cell(6, 1, "Octubre 2026")
    reemplazar("Metas_RODDOS.xlsx", wb)
    assert ds.leer_metas(HOY)["ventas"] == 100   # antes: AttributeError y página caída


# ---------------------------------------------------------------- Cobranza (Sí / No del instructivo)

def test_cobranza_cuenta_si_como_pagada(datos_prueba):
    cob = ds.leer_cobranza_semanal()
    assert cob["potencial_total"] == 8 * CUOTA          # 6 de la semana + 2 vencidas
    assert cob["cobrado_dinero"] == 4 * CUOTA           # 3 "Sí" de la semana + 1 vencida
    assert cob["cuotas_cobradas"] == 4
    assert cob["pct_avance"] == pytest.approx(0.5)


# ---------------------------------------------------------------- Tesorería y RRHH

def test_tesoreria(datos_prueba):
    tes = ds.leer_tesoreria()
    d = tes["dashboard"]
    assert d["corte_fecha"] == HOY
    assert d["mes_control"] == datetime.datetime(2026, 10, 1)
    assert d["pago_auteco_mes"] == 25_000_000
    assert (tes["egresos"]["Es traslado"] == "No").all()   # los traslados no son gasto


def test_tesoreria_mes_control_en_texto_no_tumba(datos_prueba, reemplazar):
    wb = fx.wb_tesoreria()
    wb["Tablero mes"]["C4"] = "Octubre"
    reemplazar("Flujo_Pagos_Deudas.xlsx", wb)
    assert ds.leer_tesoreria()["dashboard"]["mes_control"] is None


def test_rrhh(datos_prueba):
    r = ds.leer_rrhh()
    assert r["headcount"] == 4
    assert r["costo_total_empresa_mes"] == 4 * 2_700_000   # la fila TOTAL no se suma dos veces


# ---------------------------------------------------------------- ruta opcional (prueba de lectura antes de reemplazar)

@pytest.mark.parametrize("lector, nombre", [
    ("leer_recaudo", "Proyeccion_Recaudo.xlsx"), ("leer_inventario", "Inventario_2026.xlsx"),
    ("leer_conciliacion", "Cruce_SISMO_Wava.xlsx"), ("leer_tesoreria", "Flujo_Pagos_Deudas.xlsx"),
    ("leer_rrhh", "Control_RRHH_Nomina_RODDOS_2026.xlsx"), ("leer_embudo", "Embudo_Comercial_RODDOS.xlsx"),
    ("leer_metas", "Metas_RODDOS.xlsx"), ("leer_cobranza_semanal", "Cobranza_Semanal.xlsx"),
])
def test_cada_lector_acepta_una_ruta(tmp_path, lector, nombre):
    """La página Actualizar datos prueba el archivo nuevo en una copia temporal."""
    ruta = tmp_path / f"copia_{nombre}"
    fx.ARCHIVOS[nombre]().save(ruta)
    assert getattr(ds, lector)(ruta=str(ruta)) is not None


# ---------------------------------------------------------------- Proyección de cierre (bug corregido)

def test_proyeccion_usa_el_corte_de_inventario_para_ventas():
    hoy_recaudo, hoy_inv = datetime.date(2026, 10, 20), datetime.date(2026, 10, 10)
    proy, ritmo, _ = obj.proyeccion_rubro("ventas", 10, 30, hoy_recaudo, hoy_inv)
    assert ritmo == 1.0          # 10 ventas en 10 días de Inventario (antes: 10 / 20 = 0,5)
    assert proy == 31.0          # octubre tiene 31 días


def test_proyeccion_usa_el_corte_de_recaudo_para_pagos():
    proy, ritmo, _ = obj.proyeccion_rubro("pagos_dinero", 1_000, 3_000, datetime.date(2026, 10, 20),
                                          datetime.date(2026, 10, 10))
    assert ritmo == 50.0


def test_proyeccion_usa_el_largo_del_mes_de_la_fuente():
    """Inventario cortado el 30 de septiembre y Recaudo ya en octubre."""
    proy, _, _ = obj.proyeccion_rubro("ventas", 30, 40, datetime.date(2026, 10, 2), datetime.date(2026, 9, 30))
    assert proy == 30.0          # septiembre tiene 30 días: el mes ya cerró en 30
