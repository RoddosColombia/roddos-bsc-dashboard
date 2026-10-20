"""Reconstrucción de meses anteriores (reconstruir.py) con los Excel de prueba.

Datos de prueba: septiembre con 30 cuotas pagadas de $500.000; Inventario con resumen de
marzo a octubre (11 vendidas, 10 activadas y $15.000.000 de cuotas iniciales por mes);
Metas con fila de septiembre (meta de ventas 100) y octubre (30).
"""
import datetime as dt
import os

import pytest
from streamlit.testing.v1 import AppTest

import data_sources as ds
import fixtures_excel as fx
import historico
import reconstruir as rc

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _fotos():
    return {f["periodo"]: f for f in rc.reconstruir(ds.leer_recaudo(), ds.leer_inventario(), ds.leer_embudo(),
                                                     ds.leer_metas, fx.HOY, fx.HOY)}


def test_septiembre_se_reconstruye_con_las_formulas_del_tablero(datos_prueba):
    sep = _fotos()["2026-09"]["datos"]
    assert sep["pagos_dinero"] == 30 * fx.CUOTA and sep["pagos_num"] == 30
    assert sep["ventas"] == 11 and sep["activaciones"] == 10 and sep["ci_dinero"] == 15_000_000
    assert sep["_metas"]["ventas"] == 100                  # la meta de septiembre, no la de octubre
    assert sep["_reconstruida"] is True


def test_lo_que_no_se_puede_saber_hacia_atras_queda_vacio(datos_prueba):
    sep = _fotos()["2026-09"]["datos"]
    for clave in ("vencidas_dinero", "mora_total", "inventario_disponible"):
        assert clave not in sep


def test_no_reconstruye_el_mes_de_trabajo_ni_meses_sin_datos(datos_prueba):
    fotos = _fotos()
    assert "2026-10" not in fotos                         # ese lo toma la foto en vivo
    assert min(fotos) == "2026-03"                        # el Inventario empieza en marzo
    assert fotos["2026-04"]["datos"]["_metas"] == {}       # no hay fila de metas de abril


def test_una_foto_real_nunca_se_reemplaza(datos_prueba, tmp_path):
    alm = historico.AlmacenLocal(str(tmp_path / "h.sqlite"))
    real = dict(periodo="2026-09", corte="2026-09-30", guardado_en="x", datos={"pagos_dinero": 1.0})
    alm.guardar(real)
    historico.registrar_reconstruidas(alm, list(_fotos().values()))
    assert alm.obtener("2026-09")["datos"] == {"pagos_dinero": 1.0}       # foto real del formato anterior: intacta
    assert historico.es_reconstruida(alm.obtener("2026-08"))


def test_volver_a_reconstruir_no_reescribe_si_no_cambia(datos_prueba, tmp_path):
    alm = historico.AlmacenLocal(str(tmp_path / "h.sqlite"))
    fotos = list(_fotos().values())
    assert historico.registrar_reconstruidas(alm, fotos) == len(fotos)
    assert historico.registrar_reconstruidas(alm, fotos) == 0


@pytest.mark.parametrize("etiqueta, esperado", [
    ("Marzo", (2026, 3)), ("septiembre", (2026, 9)), ("Sept", (2026, 9)), ("Set", (2026, 9)),
    ("mar-26", (2026, 3)), ("Marzo 2025", (2025, 3)), ("Diciembre", (2025, 12)),   # leído en octubre de 2026
    (dt.datetime(2026, 5, 1), (2026, 5)), ("TOTAL", None), (None, None),
])
def test_etiquetas_de_mes_del_inventario(etiqueta, esperado):
    assert rc.mes_de_etiqueta(etiqueta, dt.date(2026, 10, 9)) == esperado


def test_pagina_historico_marca_los_meses_reconstruidos(datos_prueba):
    at = AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    at.run()
    at = AppTest.from_file(os.path.join(RAIZ, "pages/5_Historico.py"), default_timeout=60).run()
    assert not at.exception
    assert any("Mes reconstruido" in c.value for c in at.caption)
    tabla = at.dataframe[0].value
    assert "Septiembre 2026 *" in tabla.index and "Octubre 2026 (en curso)" not in tabla.index[:-1]
    assert tabla.loc["Septiembre 2026 *", "Cartera vencida ($)"] == "—"
