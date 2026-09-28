import calendar
import streamlit as st

import acceso
import metricas as mx
import data_sources as ds
from utils import cop, estilo_roddos, html, hsafe, kpi, hero, CARD

st.set_page_config(page_title="Vista de reunión — RODDOS BSC", layout="wide", page_icon="🗓️")
estilo_roddos()

COLOR_OK = "#00C853"
COLOR_ALERTA = "#FFB300"
COLOR_CRIT = "#FF5252"
COLOR_NEUTRO = "#9AA0A6"

RUBROS_PORCENTAJE = {"pct_aprobacion", "pct_conversion_agenda"}
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
        return "sin dato"
    if es_dinero:
        return cop(valor)
    if clave in RUBROS_PORCENTAJE:
        return f"{valor * 100:.0f}%"
    if clave == "dias_inventario":
        return f"{valor:,.1f}".replace(",", ".")
    return f"{valor:,.0f}".replace(",", ".")


st.title("🗓️ Vista de reunión")
st.caption(
    "Para proyectar en pantalla y recorrer en 15 minutos. Un renglón por indicador, "
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

if metas:
    sub = (f"Meta ventas {metas['ventas']:.0f} · aprobación {metas['pct_aprobacion']*100:.0f}% · "
           f"agendas {metas['pct_agendas']*100:.0f}% · tope mora {metas['pct_mora_tope']*100:.0f}%")
else:
    sub = "Sin Metas_RODDOS.xlsx cargado"
hero(f"Mes de trabajo · {calendar.month_name[hoy_recaudo.month].capitalize()} {hoy_recaudo.year}",
     "Este mes", sub=sub)

st.write("")

for nombre_etapa, claves in mx.ETAPAS:
    filas = f"<div style='font-family:Montserrat,sans-serif;font-weight:700;font-size:16px;margin-bottom:6px'>{nombre_etapa}</div>"
    corte = None
    for clave in claves:
        r = M.get(clave)
        if r is None:
            continue
        corte = corte or r.get("corte")
        val = r.get("mes")
        es_dinero = "dinero" in clave or clave in ("ci_dinero", "mora_total", "pagos_dinero", "vencidas_dinero")
        objetivo = objetivos_mes.get(clave)
        if clave in RUBROS_SIN_META or not objetivo:
            txt, color = "referencia", COLOR_NEUTRO
        else:
            txt, color = estado(val, objetivo, es_negativo_malo=(clave == "mora_total"))
        filas += (f"<div style='display:flex;justify-content:space-between;align-items:center;padding:9px 2px;border-top:1px solid #262626'>"
                  f"<span style='font-size:14px;color:#D0D3D6'>{hsafe(mx.RUBRO_LABEL[clave])}</span>"
                  f"<span style='display:flex;align-items:center;gap:10px'>"
                  f"<span style='font-size:14px;font-weight:700;color:#F2F2F2'>{hsafe(fmt_valor(clave, val, es_dinero))}</span>"
                  f"<span style='font-size:11px;color:{color};min-width:74px;text-align:right'>● {txt}</span></span></div>")
    if corte:
        filas += f"<div style='font-size:11px;color:#6E7276;margin-top:8px'>Corte: {corte}</div>"
    html(f"<div style='{CARD}margin-bottom:12px'>{filas}</div>")

st.subheader("💰 Tesorería")
if acceso.formulario_director("La caja es solo para directores.") and metas:
    tes = ds.leer_tesoreria()
    dash = tes["dashboard"]
    pago_auteco_mes = dash.get("pago_auteco_mes") or 0
    resultado_objetivo = (meta_pactada_recaudo or 0) + metas["ci_dinero"] - metas["gasto_fijo"] - pago_auteco_mes
    tc1, tc2 = st.columns(2)
    with tc1:
        kpi("Caja disponible total", cop(dash["caja_disponible_total"]))
    with tc2:
        kpi("Resultado objetivo del mes", cop(resultado_objetivo),
            chip_txt="en verde" if resultado_objetivo >= 0 else "en rojo",
            chip_color=COLOR_OK if resultado_objetivo >= 0 else COLOR_CRIT,
            sub="recaudo + CI − gasto fijo − Auteco")
elif st.session_state.get("es_director"):
    st.caption("Sin Metas_RODDOS.xlsx cargado — no se puede calcular el resultado objetivo del mes.")

st.divider()
st.caption("RRHH no aparece aquí — es un módulo privado, solo para directores (ver página RRHH).")
