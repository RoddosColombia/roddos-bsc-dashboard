import calendar
import streamlit as st

import acceso
import metricas as mx
import data_sources as ds
from utils import cop

st.set_page_config(page_title="Vista de reunión — RODDOS BSC", layout="wide", page_icon="🗓️")


def mdsafe(s):
    return str(s).replace("$", "\\$")


COLOR_OK = "#1F6F5C"
COLOR_ALERTA = "#B7791F"
COLOR_CRIT = "#9C2B0F"
COLOR_NEUTRO = "#7A7A7A"

RUBROS_PORCENTAJE = {"pct_aprobacion"}
RUBROS_SIN_META = {"cuotas_mes", "vencidas_num", "vencidas_dinero"}


def estado(valor, meta, es_negativo_malo=False):
    if valor is None or not meta:
        return "Sin meta", COLOR_NEUTRO
    ratio = valor / meta
    if es_negativo_malo:
        if ratio <= 0.5:
            return "Bajo control", COLOR_OK
        if ratio <= 1.0:
            return "Vigilar", COLOR_ALERTA
        return "Atención", COLOR_CRIT
    if ratio >= 0.95:
        return "En meta", COLOR_OK
    if ratio >= 0.75:
        return "En camino", COLOR_ALERTA
    return "Rezagado", COLOR_CRIT


def fmt_valor(clave, valor, es_dinero):
    if valor is None:
        return "Sin dato"
    if es_dinero:
        return cop(valor)
    if clave in RUBROS_PORCENTAJE:
        return f"{valor * 100:.0f}%"
    if clave == "dias_inventario":
        return f"{valor:,.1f}".replace(",", ".")
    return f"{valor:,.0f}".replace(",", ".")


st.title("🗓️ Vista de reunión")
st.caption(
    "Pensada para proyectar en pantalla y recorrer en 15 minutos. Un renglón por indicador, "
    "semáforo contra la meta del mes — no discute datos, discute desviaciones."
)

data = mx.construir_metricas()
M = data["metricas"]
hoy_recaudo = data["hoy_recaudo"]

metas = ds.leer_metas(hoy_recaudo)
recaudo = ds.leer_recaudo()
meta_pactada_recaudo = recaudo["dashboard"].get("meta_pactada")

objetivos_mes = {}
if metas:
    objetivos_mes["ventas"] = metas["ventas"]
    objetivos_mes["activaciones"] = metas["ventas"]
    objetivos_mes["ci_dinero"] = metas["ci_dinero"]
    objetivos_mes["pct_aprobacion"] = metas["pct_aprobacion"]
if meta_pactada_recaudo:
    objetivos_mes["pagos_dinero"] = meta_pactada_recaudo

st.info(f"🎯 Mes de trabajo: **{calendar.month_name[hoy_recaudo.month].capitalize()} {hoy_recaudo.year}**" +
        (f" · Meta ventas: **{metas['ventas']:.0f}** · Meta aprobación: **{metas['pct_aprobacion']*100:.0f}%** · "
         f"Meta agendas: **{metas['pct_agendas']*100:.0f}%** · Tope mora: **{metas['pct_mora_tope']*100:.0f}%**"
         if metas else " · Sin Metas_RODDOS.xlsx cargado"))

for nombre_etapa, claves in mx.ETAPAS:
    with st.container(border=True):
        st.subheader(nombre_etapa)
        for clave in claves:
            r = M.get(clave)
            if r is None:
                continue
            val = r.get("mes")
            es_dinero = "dinero" in clave or clave in ("ci_dinero", "mora_total", "pagos_dinero", "vencidas_dinero")
            objetivo = objetivos_mes.get(clave)
            negativo = clave == "mora_total"
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(mdsafe(mx.RUBRO_LABEL[clave]))
            c2.markdown(f"**{mdsafe(fmt_valor(clave, val, es_dinero))}**")
            if clave in RUBROS_SIN_META or not objetivo:
                c3.markdown(f"<span style='color:{COLOR_NEUTRO}'>● Sin meta</span>", unsafe_allow_html=True)
            else:
                txt, color = estado(val, objetivo, es_negativo_malo=negativo)
                c3.markdown(f"<span style='color:{color}; font-weight:700'>● {txt}</span>", unsafe_allow_html=True)
        if r := M.get(claves[0]):
            st.caption(f"Corte: {r.get('corte') or '—'}")

with st.container(border=True):
    st.subheader("💰 Tesorería")
    if acceso.formulario_director("La caja es solo para directores.") and metas:
        tes = ds.leer_tesoreria()
        dash = tes["dashboard"]
        pago_auteco_mes = dash.get("pago_auteco_mes") or 0
        resultado_objetivo = (meta_pactada_recaudo or 0) + metas["ci_dinero"] - metas["gasto_fijo"] - pago_auteco_mes
        color = COLOR_OK if resultado_objetivo >= 0 else COLOR_CRIT
        c1, c2 = st.columns(2)
        c1.markdown("Caja disponible total")
        c1.markdown(f"**{mdsafe(cop(dash['caja_disponible_total']))}**")
        c2.markdown("Resultado objetivo del mes (recaudo + CI − gasto fijo − Auteco)")
        c2.markdown(f"<span style='color:{color}; font-weight:700'>{mdsafe(cop(resultado_objetivo))}</span>", unsafe_allow_html=True)
    elif st.session_state.get("es_director"):
        st.caption("Sin Metas_RODDOS.xlsx cargado — no se puede calcular el resultado objetivo del mes.")

st.divider()
st.caption("RRHH no aparece aquí — es un módulo privado, solo para directores (ver página RRHH).")
