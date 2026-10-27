"""Vista de reunión gráfica: gráficos (graficos.py) y la página con los Excel de prueba."""
import os

import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

import graficos as g

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.parametrize("valor, esperado, color", [
    (16, 15, g.VERDE), (12, 15, g.AMBAR), (9, 15, g.ROJO), (5, None, g.GRIS),
])
def test_color_contra_lo_esperado_a_hoy(valor, esperado, color):
    assert g.color_estado(valor, esperado) == color


def test_a_mitad_de_mes_al_ritmo_es_verde_y_no_rezagado():
    """El error que había: día 15 de 30, 15 ventas de una meta de 30 salía 'Rezagado'."""
    assert g.texto_estado(15, 30 * 15 / 30) == "En meta"


def test_medidor():
    f = g.medidor("Recaudo", 38_500_000, 60_000_000, 28_000_000, "dinero")
    ind = f.data[0]
    assert isinstance(ind, go.Indicator) and ind.value == pytest.approx(38.5)
    assert ind.number.suffix == " M" and ind.gauge.threshold.value == pytest.approx(28)
    assert ind.gauge.bar.color == g.VERDE
    assert f.layout.separators == ",."            # 38,5 M (formato colombiano)


def test_medidor_sin_meta_a_hoy_no_dibuja_raya():
    assert g.medidor("Ventas", 5, 30, None).data[0].gauge.threshold.value is None


def test_embudo_textos_y_porcentajes():
    f = g.embudo([("Leads", 120), ("Formularios", 64), ("Aprobados", None), ("Compraron", 11)])
    t = f.data[0]
    assert list(t.y) == ["Leads", "Formularios", "Compraron"]     # sin las etapas sin dato
    assert t.text[1] == "<b>64</b>  ·  53%" and t.text[2] == "<b>11</b>  ·  17%"
    assert list(t.textposition) == ["inside", "inside", "outside"]


def test_cascada_resultado():
    f = g.cascada_resultado(60e6, 45e6, 40e6, 25e6)
    assert list(f.data[0].y) == [60, 45, -40, -25, 40]
    assert f.data[0].text[-1] == "40,0 M"
    assert g.cascada_resultado(30e6, 10e6, 40e6, 25e6).data[0].totals.marker.color == g.ROJO


def test_tendencia_marca_reconstruidos():
    f = g.tendencia("Ventas", ["Sep", "Oct"], [11, 10], [100, 30], [True, False])
    assert list(f.data[0].marker.color) == ["rgba(56,217,240,0.35)", g.CIAN]
    assert list(f.data[1].y) == [100, 30]


def _vista(clave=None):
    at = AppTest.from_file(os.path.join(RAIZ, "pages/3_Vista_Reunion.py"), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    at.run()
    if clave:
        at.text_input(key="clave_directores").input(clave)
        at.button[0].click()
        at.run()
    return at


def test_vista_reunion_grafica(datos_prueba):
    AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=60).run()   # crea el histórico
    at = _vista()
    assert not at.exception
    subtitulos = [s.value for s in at.subheader]
    for s in ("🎯 ¿Cómo vamos frente a la meta?", "🧲 Embudo comercial del mes", "💳 Cartera",
              "📦 Inventario", "📈 Tendencia de los últimos meses"):
        assert s in subtitulos
    graficos_pagina = at.get("plotly_chart")
    assert len(graficos_pagina) == 5 + 1 + 3          # medidores + embudo + tendencias
    detalle = " ".join(m.value for e in at.expander for m in e.markdown)
    assert "1 · Demanda" in detalle                    # el detalle completo sigue disponible


def test_vista_reunion_cascada_solo_con_clave(datos_prueba):
    sin = _vista()
    con = _vista("x")
    assert len(con.get("plotly_chart")) == len(sin.get("plotly_chart")) + 1


@pytest.mark.parametrize("valores", [(200e6, 175e6, 120e6, 250e6),   # resultado casi en cero
                                     (200e6, 175e6, 120e6, 400e6),   # resultado negativo grande
                                     (30e6, 10e6, 40e6, 25e6)])      # todo pequeño y negativo
def test_cascada_ninguna_etiqueta_queda_por_fuera(valores):
    """Caso reportado: con los valores reales no se veían 'Pago Auteco' ni 'Resultado'."""
    f = g.cascada_resultado(*valores)
    w = f.data[0]
    assert w.cliponaxis is False
    bajo, alto = f.layout.yaxis.range
    acumulado, puntos = 0, [0]
    for v in w.y[:-1]:
        acumulado += v
        puntos.append(acumulado)
    puntos.append(w.y[-1])
    assert bajo < min(puntos) and alto > max(puntos)               # con aire arriba y abajo
    assert len(w.text) == 5 and all(t.endswith(" M") for t in w.text)


def test_cascada_barra_chica_lleva_la_etiqueta_afuera():
    w = g.cascada_resultado(200e6, 175e6, 120e6, 250e6).data[0]
    assert w.textposition[-1] == "outside"     # resultado de 5 M: no cabe adentro
    assert w.textposition[3] == "inside"       # pago Auteco de 250 M: adentro, en blanco


# ---------------------------------------------------------------- valores sobre las columnas (pedido de los jefes)

def test_pulir_pone_el_valor_en_cada_columna_y_quita_el_zoom():
    fig = go.Figure([go.Bar(x=["Sep", "Oct"], y=[58e6, 4.5e6], name="Recaudo"),
                     go.Bar(x=["Sep", "Oct"], y=[60e6, 60e6], name="Meta de la semana")])
    g.pulir(fig, "dinero")
    assert list(fig.data[0].text) == ["58,0 M", "4,5 M"]
    assert fig.data[1].text is None                      # la meta es referencia: sin número
    assert fig.data[0].textangle == 0 and fig.data[0].cliponaxis is False
    assert fig.layout.dragmode is False and fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange
    assert fig.layout.yaxis.range[1] == pytest.approx(60e6 * 1.2)   # espacio para el número de la más alta


def test_pulir_barras_horizontales_y_porcentajes():
    fig = g.pulir(go.Figure(go.Bar(x=[3e6, 1e6], y=["Nómina", "Arriendo"], orientation="h")), "dinero")
    assert list(fig.data[0].text) == ["3,0 M", "1,0 M"] and fig.layout.xaxis.range[1] == pytest.approx(3.75e6)
    assert g.valor_corto(0.6, "porcentaje") == "60%" and g.valor_corto(1234, "numero") == "1.234"


def test_tendencia_muestra_los_valores():
    f = g.tendencia("Recaudo", ["Sep", "Oct"], [58e6, 4.5e6], tipo="dinero")
    assert list(f.data[0].text) == ["58,0", "4,5"] and f.layout.dragmode is False


def test_nombres_largos_en_varias_lineas():
    """Caso real (RRHH, 27 oct): los nombres completos se montaban unos sobre otros."""
    assert g.partir_etiqueta("Mary Alexandra Suárez") == "Mary Alexandra<br>Suárez"
    assert g.partir_etiqueta("Lizbeth Rincón") == "Lizbeth<br>Rincón"
    assert g.partir_etiqueta("Andrés") == "Andrés"
    fig = g.pulir(go.Figure(go.Bar(x=["Yenny Paola Aya Fuentes", "Iván Echeverri"], y=[4.8e6, 16.9e6])), "dinero")
    assert list(fig.layout.xaxis.ticktext) == ["Yenny Paola<br>Aya Fuentes", "Iván<br>Echeverri"]
    corto = g.pulir(go.Figure(go.Bar(x=["Sep", "Oct"], y=[1, 2])))
    assert corto.layout.xaxis.ticktext is None          # etiquetas cortas: sin cambios


def test_pulir_con_columnas_de_pandas():
    """Las páginas pasan columnas de pandas (no listas). Caso real: RRHH se caía con 'x or []'."""
    import pandas as pd
    nom = pd.DataFrame({"Empleado": ["Mary Alexandra Suárez", "Andrés Sanjuan"], "Costo": [6.9e6, 16.9e6]})
    fig = g.pulir(go.Figure(go.Bar(x=nom["Empleado"], y=nom["Costo"])), "dinero")
    assert list(fig.layout.xaxis.ticktext) == ["Mary Alexandra<br>Suárez", "Andrés<br>Sanjuan"]
    assert list(fig.data[0].text) == ["6,9 M", "16,9 M"]
