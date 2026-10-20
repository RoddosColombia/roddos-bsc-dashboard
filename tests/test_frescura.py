"""Aviso de datos desactualizados (frescura.py) y cómo se ve en las páginas."""
import datetime as dt
import os

import pytest
from streamlit.testing.v1 import AppTest

import fixtures_excel as fx
import frescura as fr

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LUN, MAR, JUE, VIE, SAB = (dt.date(2026, 10, d) for d in (19, 20, 15, 16, 17))


@pytest.mark.parametrize("corte, hoy, habiles, nivel", [
    (dt.date(2026, 10, 18), LUN, 0, fr.AL_DIA),         # domingo -> lunes
    (VIE, LUN, 0, fr.AL_DIA),                           # viernes -> lunes: fin de semana no cuenta
    (JUE, LUN, 1, fr.AL_DIA),                           # lunes antes de subir lo del viernes
    (JUE, MAR, 2, fr.ATRASO),
    (dt.date(2026, 10, 12), LUN, 4, fr.ATRASO),
    (dt.date(2026, 10, 9), LUN, 5, fr.GRAVE),           # una semana
    (dt.date(2026, 9, 28), LUN, 14, fr.GRAVE),          # el caso real: datos de finales de septiembre
    (LUN, LUN, 0, fr.AL_DIA),
])
def test_niveles(corte, hoy, habiles, nivel):
    r = fr.revisar({"Recaudo": corte}, hoy)[0]
    assert r["habiles"] == habiles and r["nivel"] == nivel


def test_texto_en_espanol():
    r = fr.revisar({"Recaudo": dt.date(2026, 9, 28)}, LUN)[0]
    assert r["texto"] == "Recaudo: datos del 28 de septiembre (hace 21 días)"
    assert fr.revisar({"X": dt.date(2026, 10, 18)}, LUN)[0]["texto"].endswith("(de ayer)")
    assert "de 2025" in fr.revisar({"X": dt.date(2025, 12, 30)}, LUN)[0]["texto"]


def test_nivel_general_es_el_peor():
    res = fr.revisar({"Recaudo": VIE, "Inventario": dt.date(2026, 9, 28)}, LUN)
    assert fr.nivel_general(res) == fr.GRAVE
    assert fr.nivel_general(fr.revisar({"A": VIE, "B": None}, LUN)) == fr.SIN_FECHA


def _abrir(pagina):
    at = AppTest.from_file(os.path.join(RAIZ, pagina), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    at.run()
    if any(t.key == "clave_directores" for t in at.text_input):
        at.text_input(key="clave_directores").input("x")
        at.button[0].click()
        at.run()
    return at


@pytest.mark.parametrize("pagina", ["app.py", "pages/3_Vista_Reunion.py", "pages/1_Tesoreria.py"])
def test_pagina_avisa_datos_viejos(datos_prueba, monkeypatch, pagina):
    monkeypatch.setattr(fr, "_hoy", lambda: fx.HOY + dt.timedelta(days=17))   # dos semanas y media después
    at = _abrir(pagina)
    assert not at.exception
    assert any("Los datos no están al día" in e.value and "hace 17 días" in e.value for e in at.error)


def test_pagina_principal_al_dia(datos_prueba, monkeypatch):
    monkeypatch.setattr(fr, "_hoy", lambda: fx.HOY + dt.timedelta(days=3))    # viernes -> lunes
    at = _abrir("app.py")
    assert not any("no están al día" in e.value for e in at.error)
    assert any("✅ Datos al día" in c.value for c in at.caption)


def test_mes_de_trabajo_es_el_mas_reciente_y_avisa_el_atrasado():
    f = fr.texto_mes_de_trabajo
    assert f({"Recaudo": dt.date(2026, 9, 14), "Inventario": dt.date(2026, 10, 20),
              "Embudo": dt.date(2026, 10, 19)}) == "Octubre 2026 · Recaudo aún en septiembre"
    assert f({"Recaudo": dt.date(2026, 10, 18), "Inventario": dt.date(2026, 10, 20)}) == "Octubre 2026"
    assert f({"Recaudo": dt.date(2025, 12, 30), "Inventario": dt.date(2026, 1, 5),
              "Embudo": None}) == "Enero 2026 · Recaudo aún en diciembre 2025"
    assert f({"Recaudo": None}) == "—"


def test_vista_reunion_muestra_el_mes_mas_reciente(datos_prueba, reemplazar):
    reemplazar("Proyeccion_Recaudo.xlsx", fx.wb_recaudo(hoy=dt.date(2026, 9, 20)))
    at = _abrir("pages/3_Vista_Reunion.py")
    assert not at.exception
    assert "Mes de trabajo · Octubre 2026 · Recaudo aún en septiembre" in " ".join(m.value for m in at.markdown)
