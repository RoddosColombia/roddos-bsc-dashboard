import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import formatos
import graficos
import historico
from utils import cop, estilo_roddos, encabezado, kpi, VERDE, ROJO, NEUTRO, CIAN

st.set_page_config(page_title="Histórico — RODDOS BSC", layout="wide", page_icon="📈")
estilo_roddos()
encabezado("Histórico · cómo cerró cada mes")

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def nombre_mes(periodo):
    anio, mes = periodo.split("-")
    return f"{MESES[int(mes)].capitalize()} {anio}"


def fmt(tipo, v):
    if v is None:
        return "—"
    if tipo == "dinero":
        return cop(v)
    if tipo == "porcentaje":
        return f"{v * 100:.0f}%"
    return f"{v:,.0f}".replace(",", ".")


try:
    alm = historico.almacen()
    fotos = alm.listar()
except Exception as e:
    st.error(f"No se pudo leer el histórico: {e}")
    st.stop()

st.caption(f"Guardado en: **{alm.nombre}**. Se toma una foto cada vez que se abre la página principal "
           "con datos nuevos; la última foto de cada mes es su cierre.")

if not fotos:
    st.info("📭 Todavía no hay historia guardada. Abre la página principal con los datos cargados y "
            "aquí empezará a aparecer cada mes.")
    st.stop()

mes_actual = formatos.hoy_colombia().strftime("%Y-%m")
etiquetas = [nombre_mes(f["periodo"]) + (" (en curso)" if f["periodo"] == mes_actual else "")
             + (" *" if historico.es_reconstruida(f) else "") for f in fotos]
if any(historico.es_reconstruida(f) for f in fotos):
    st.caption("\\* Mes reconstruido a partir de la historia de los Excel: incluye recaudo, ventas, activaciones, "
               "cuotas iniciales, leads y % de aprobación. La cartera vencida, la mora y las motos disponibles no "
               "se pueden saber hacia atrás y aparecen con «—». Desde que el tablero toma fotos en vivo, cada mes "
               "queda completo.")

# ---- Último mes vs. el anterior ----
ultima = fotos[-1]
anterior = fotos[-2] if len(fotos) > 1 else None
st.subheader(f"{etiquetas[-1]} vs. {etiquetas[-2] if anterior else '—'}")
st.caption(f"Corte de la foto más reciente: {ultima['corte']}")

cols = st.columns(4)
for i, (clave, etiqueta, tipo, mas_es_mejor) in enumerate(historico.INDICADORES[:8]):
    v = ultima["datos"].get(clave)
    v_ant = anterior["datos"].get(clave) if anterior else None
    chip, color = None, NEUTRO
    if v is not None and v_ant:
        cambio = (v - v_ant) / abs(v_ant)
        chip = f"{'▲' if cambio >= 0 else '▼'} {abs(cambio) * 100:.0f}% vs. mes anterior"
        if mas_es_mejor is not None and abs(cambio) >= 0.005:
            color = VERDE if (cambio > 0) == mas_es_mejor else ROJO
    with cols[i % 4]:
        kpi(etiqueta, fmt(tipo, v), chip_txt=chip, chip_color=color)

# ---- Evolución de un indicador ----
st.write("")
st.subheader("Evolución mes a mes")
opciones = {etq: (clave, tipo) for clave, etq, tipo, _ in historico.INDICADORES}
elegido = st.selectbox("Indicador", list(opciones.keys()))
clave, tipo = opciones[elegido]

valores = [f["datos"].get(clave) for f in fotos]
metas = [(f["datos"].get("_metas") or {}).get(clave) for f in fotos]

# en el eje, meses cortos ("Sep 26", "Oct 26*") para que no se corten; la tabla mantiene el nombre completo
eje = [MESES[int(f["periodo"][5:])][:3].capitalize() + " " + f["periodo"][2:4]
       + ("*" if historico.es_reconstruida(f) else "") for f in fotos]
fig = go.Figure()
fig.add_trace(go.Bar(x=eje, y=valores, name=elegido, marker_color=CIAN))
if any(m is not None for m in metas):
    fig.add_trace(go.Scatter(x=eje, y=metas, name="Meta", mode="lines+markers",
                             line=dict(color="#EEF2F4", dash="dash")))
fig.update_layout(height=380, legend=dict(orientation="h", y=1.12),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#EEF2F4",
                  yaxis_tickformat=".0%" if tipo == "porcentaje" else None)
graficos.pulir(fig, tipo)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---- Tabla completa ----
with st.expander("📋 Ver tabla de todos los meses"):
    tabla = pd.DataFrame(
        {etq: [fmt(tipo_i, f["datos"].get(c)) for f in fotos] for c, etq, tipo_i, _ in historico.INDICADORES},
        index=etiquetas,
    )
    tabla.insert(0, "Corte", [f["corte"] for f in fotos])
    st.dataframe(tabla, use_container_width=True)
