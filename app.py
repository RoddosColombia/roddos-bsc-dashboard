import datetime
import calendar
import os
import streamlit as st
import plotly.graph_objects as go

from utils import cop, estilo_roddos
import metricas as mx
import objetivos as obj
import data_sources as ds

st.set_page_config(page_title="RODDOS — Operación diaria", layout="wide", page_icon="🏍️")
estilo_roddos()


def mdsafe(s):
    """Escapa '$' para que Streamlit no lo lea como fórmula KaTeX (contexto markdown)."""
    return str(s).replace("$", "\\$")


def hsafe(s):
    """Para '$' dentro de HTML: entidad, que se ve como $ y no dispara KaTeX."""
    return str(s).replace("$", "&#36;")


def html(s):
    st.markdown(s, unsafe_allow_html=True)


COLOR_OK = "#00C853"
COLOR_ALERTA = "#FFB300"
COLOR_CRIT = "#FF5252"
COLOR_NEUTRO = "#9AA0A6"

CARD = "background:#1A1A1A;border:1px solid #2C2C2C;border-radius:14px;padding:16px 18px;"

st.title("🏍️ RODDOS — Operación diaria")

data = mx.construir_metricas()
M = data["metricas"]
hoy_recaudo = data["hoy_recaudo"]
hoy_inv = data["hoy_inv"]
hoy_inv_txt = data["hoy_inv_txt"]

c1, c2, c3 = st.columns(3)
c1.caption(f"📋 Recaudo — corte {hoy_recaudo}")
c2.caption(f"📦 Inventario/Ventas — corte {hoy_inv_txt or hoy_inv}")
c3.caption(f"🎯 Mes de trabajo: {calendar.month_name[hoy_recaudo.month].capitalize()} {hoy_recaudo.year}")

conc = data["conc"]
if conc["problemas"]:
    with st.expander(f"🔎 Conciliación SISMO ↔ Wava — {len(conc['problemas'])} casos abiertos, {cop(conc['monto_en_riesgo'])} por confirmar", expanded=False):
        for p in conc["problemas"]:
            st.markdown(f"**{p['num']}. {p['problema']}** — {p['casos']} · {cop(p['monto']) if isinstance(p['monto'], (int, float)) else p['monto']}")
            st.caption(p["solucion"])


RUBROS_SIN_META = {"cuotas_mes", "vencidas_num", "vencidas_dinero"}
RUBROS_PORCENTAJE = {"pct_aprobacion"}


def estado_chip(valor, meta_esperada_a_hoy, es_negativo_malo=False):
    if valor is None or not meta_esperada_a_hoy:
        return "Sin meta", COLOR_NEUTRO
    ratio = valor / meta_esperada_a_hoy
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


def tile_rubro(clave, columna, periodo, objetivo=None, dia_del_mes=None, dias_mes=None):
    r = M[clave]
    label = mx.RUBRO_LABEL[clave]
    val = r.get(periodo)
    with columna:
        with st.container(border=True):
            st.caption(label)
            if val is None:
                st.markdown("**Sin dato diario en esta fuente**" if periodo != "mes" else "**Sin dato**")
            else:
                es_dinero = "dinero" in clave or clave in ("ci_dinero", "mora_total", "pagos_dinero", "vencidas_dinero")
                es_porcentaje = clave in RUBROS_PORCENTAJE

                def _fmt(v):
                    if es_dinero:
                        return cop(v)
                    if es_porcentaje:
                        return f"{v * 100:.0f}%"
                    return f"{v:,.1f}".replace(",", ".") if clave == "dias_inventario" else f"{v:,.0f}".replace(",", ".")

                st.markdown(f"### {_fmt(val)}")
                if periodo == "mes" and objetivo and clave not in RUBROS_SIN_META:
                    negativo = clave == "mora_total"
                    dia_de_esta_fuente = dia_del_mes.get(clave) if isinstance(dia_del_mes, dict) else dia_del_mes
                    if clave in obj.RUBROS_FLUJO_MENSUAL and dia_de_esta_fuente and dias_mes:
                        meta_a_hoy = objetivo * dia_de_esta_fuente / dias_mes
                    else:
                        meta_a_hoy = objetivo
                    txt, color = estado_chip(val, meta_a_hoy, es_negativo_malo=negativo)
                    st.markdown(f"<span style='color:{color}; font-weight:700; font-size:13px'>● {txt}</span>", unsafe_allow_html=True)
                    fmt_obj = _fmt(objetivo)
                    if not negativo:
                        pct = min(1.0, val / objetivo)
                        st.progress(pct, text=f"{val/objetivo*100:.0f}% del objetivo del mes ({fmt_obj})")
                        if clave in obj.RUBROS_FLUJO_MENSUAL:
                            st.caption(f"Meta esperada a hoy (día {dia_de_esta_fuente} de {dias_mes}): {_fmt(meta_a_hoy)}")
            if r.get("extra"):
                st.caption(r["extra"])
            st.caption(f"Fuente: {r['fuente']}")


RUBROS_DIARIOS = ["cuotas_mes", "pagos_num", "pagos_dinero", "vencidas_num", "vencidas_dinero"]
RUBROS_SOLO_MES = ["ventas", "facturacion", "ci_completas", "ci_parciales", "ci_dinero",
                   "activaciones", "mora_total", "inventario_bodega", "inventario_disponible", "dias_inventario"]
RUBROS_EMBUDO_TRIADA = ["leads", "formularios", "aprobados_rechazados",
                        "agendas_totales", "agendas_cumplidas_ayer", "agendas_incumplidas"]
hay_datos_embudo = M["leads"]["mes"] is not None

# ============ Parámetros de meta ============
metas = ds.leer_metas(hoy_recaudo)
meta_pactada_recaudo = data["rec"]["dashboard"].get("meta_pactada")
objetivos_mes = {}
if metas:
    objetivos_mes["ventas"] = metas["ventas"]
    objetivos_mes["activaciones"] = metas["ventas"]
    objetivos_mes["ci_dinero"] = metas["ci_dinero"]
    objetivos_mes["pct_aprobacion"] = metas["pct_aprobacion"]
if meta_pactada_recaudo:
    objetivos_mes["pagos_dinero"] = meta_pactada_recaudo
dias_mes = calendar.monthrange(hoy_recaudo.year, hoy_recaudo.month)[1]
RUBROS_FUENTE_INVENTARIO = {"ventas", "facturacion", "ci_completas", "ci_parciales", "ci_dinero", "activaciones", "dias_inventario"}
dia_por_rubro = {c: (hoy_inv.day if c in RUBROS_FUENTE_INVENTARIO else hoy_recaudo.day) for c in mx.RUBROS_ORDEN}

# ============ Selector de período (ayer / semana / mes) ============
st.write("")
PERIODOS = {"Ayer": "ayer", "Esta semana": "semana", "Este mes": "mes"}
sel = st.segmented_control("Período", list(PERIODOS.keys()), default="Este mes", label_visibility="collapsed")
periodo = PERIODOS.get(sel, "mes")
periodo_txt = {"ayer": "ayer", "semana": "esta semana", "mes": "este mes"}[periodo]


def meta_periodo(clave, objetivo):
    if not objetivo:
        return None
    if clave not in obj.RUBROS_FLUJO_MENSUAL:
        return objetivo
    if periodo == "mes":
        return objetivo * dia_por_rubro.get(clave, dias_mes) / dias_mes
    if periodo == "semana":
        return objetivo * 7 / dias_mes
    return objetivo / dias_mes


def fmt_val(clave, v):
    if v is None:
        return "—"
    if "dinero" in clave or clave in ("ci_dinero", "mora_total", "pagos_dinero", "vencidas_dinero"):
        return cop(v)
    if clave in RUBROS_PORCENTAJE:
        return f"{v * 100:.0f}%"
    if clave == "dias_inventario":
        return f"{v:,.1f}".replace(",", ".")
    return f"{v:,.0f}".replace(",", ".")


# ---- Veredicto ----
recaudo_val = M["pagos_dinero"][periodo]
meta_rec_p = meta_periodo("pagos_dinero", meta_pactada_recaudo)
if meta_rec_p and recaudo_val is not None:
    _, vcolor = estado_chip(recaudo_val, meta_rec_p)
    icono = {COLOR_OK: "✅", COLOR_ALERTA: "⚠️", COLOR_CRIT: "🔴"}.get(vcolor, "•")
    titulo = {COLOR_OK: f"Vas en meta {periodo_txt}",
              COLOR_ALERTA: f"Vas ajustado {periodo_txt}",
              COLOR_CRIT: f"Vas atrasado {periodo_txt}"}.get(vcolor, f"Cómo vamos {periodo_txt}")
    sub = f"Recaudo {fmt_val('pagos_dinero', recaudo_val)} · esperado {fmt_val('pagos_dinero', meta_rec_p)}"
else:
    vcolor, icono = COLOR_NEUTRO, "•"
    titulo = f"Cómo vamos {periodo_txt}"
    sub = "Sin meta de recaudo cargada para comparar."
html(f"<div style='{CARD}display:flex;gap:12px;align-items:center;border-left:4px solid {vcolor};margin-bottom:14px'>"
     f"<span style='font-size:22px'>{icono}</span>"
     f"<div><div style='font-family:Montserrat,sans-serif;font-weight:700;font-size:17px'>{titulo}</div>"
     f"<div style='color:#9AA0A6;font-size:13px;margin-top:2px'>{hsafe(sub)}</div></div></div>")

# ---- Recaudo (número héroe) ----
etiqueta_hero = {"ayer": "Recaudo de ayer", "semana": "Recaudo de la semana", "mes": "Recaudo del mes"}[periodo]
htxt, hcolor = estado_chip(recaudo_val, meta_rec_p) if (recaudo_val is not None and meta_rec_p) else ("Sin dato", COLOR_NEUTRO)
barra = ""
if periodo == "mes" and meta_pactada_recaudo and recaudo_val is not None:
    hero_pct = min(100, recaudo_val / meta_pactada_recaudo * 100)
    pace_pct = min(100, dia_por_rubro.get("pagos_dinero", dias_mes) / dias_mes * 100)
    delta = recaudo_val - (meta_rec_p or 0)
    barra = (f"<div style='height:9px;background:#0E0E0E;border-radius:20px;margin:14px 0 8px;position:relative'>"
             f"<div style='width:{hero_pct:.0f}%;height:100%;background:{hcolor};border-radius:20px'></div>"
             f"<div style='position:absolute;top:-3px;left:{pace_pct:.0f}%;width:2px;height:15px;background:#CFCFCF'></div></div>"
             f"<div style='font-size:13px;color:#9AA0A6'>Esperado a hoy: <b style='color:#F2F2F2'>{fmt_val('pagos_dinero', meta_rec_p)}</b> · "
             f"<span style='color:{hcolor};font-weight:700'>{fmt_val('pagos_dinero', delta)} vs ritmo</span></div>")
meta_txt = f"de {fmt_val('pagos_dinero', meta_pactada_recaudo)} meta" if (periodo == "mes" and meta_pactada_recaudo) else etiqueta_hero.lower()
html(f"<div style='{CARD}'>"
     f"<div style='display:flex;justify-content:space-between;align-items:flex-start'>"
     f"<div><div style='color:#9AA0A6;font-size:13px'>{etiqueta_hero} · cobranza</div>"
     f"<div style='margin-top:4px'><span style='font-family:Montserrat,sans-serif;font-weight:800;font-size:38px;color:#fff'>{hsafe(fmt_val('pagos_dinero', recaudo_val))}</span> "
     f"<span style='color:#8A8F94;font-size:15px'>{hsafe(meta_txt)}</span></div></div>"
     f"<span style='background:{hcolor}22;color:{hcolor};font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px;white-space:nowrap'>{htxt}</span>"
     f"</div>{barra}</div>")

st.write("")


def kpi_card(col, etiqueta, valor, chip_txt, chip_color, sub=""):
    with col:
        html(f"<div style='{CARD}'>"
             f"<div style='color:#9AA0A6;font-size:13px'>{etiqueta}</div>"
             f"<div style='font-family:Montserrat,sans-serif;font-weight:800;font-size:26px;color:#fff;margin:4px 0'>{hsafe(valor)}</div>"
             f"<span style='color:{chip_color};font-size:12px;font-weight:700'>● {chip_txt}</span>"
             + (f"<div style='color:#8A8F94;font-size:12px;margin-top:3px'>{hsafe(sub)}</div>" if sub else "")
             + "</div>")


k1, k2 = st.columns(2)
ventas_val = M["ventas"][periodo]
if ventas_val is None:
    kpi_card(k1, "Ventas · activaciones", "Solo mensual", "mira «Este mes»", COLOR_NEUTRO)
else:
    meta_v = objetivos_mes.get("ventas")
    t, c = estado_chip(ventas_val, meta_periodo("ventas", meta_v)) if meta_v else ("Sin meta", COLOR_NEUTRO)
    kpi_card(k1, "Ventas · activaciones", f"{ventas_val:.0f} / {meta_v:.0f}" if meta_v else f"{ventas_val:.0f}", t, c)

cv = M["vencidas_dinero"][periodo]
cn = M["vencidas_num"][periodo]
kpi_card(k2, "Cartera vencida · riesgo", fmt_val("vencidas_dinero", cv),
         "en seguimiento", COLOR_ALERTA if cv else COLOR_NEUTRO,
         sub=f"{cn:.0f} cuotas en mora" if cn else "")

st.write("")

# ---- El embudo: dónde está la fuga ----
REP = {"1 · Demanda": "leads", "2 · Crédito": "pct_aprobacion", "3 · Agenda": "agendas_totales",
       "4 · Venta": "ventas", "5 · Facturación y entrega": "facturacion",
       "6 · Cartera y mora": "vencidas_dinero", "7 · Inventario": "dias_inventario"}
filas = (f"<div style='font-size:12px;color:#8A8F94;text-transform:uppercase;letter-spacing:0.05em;padding:2px 4px 10px'>"
         f"El embudo {periodo_txt} · dónde está la fuga</div>")
for nombre_etapa, claves in mx.ETAPAS:
    rep = REP.get(nombre_etapa, claves[-1])
    v = M.get(rep, {}).get(periodo)
    mp = meta_periodo(rep, objetivos_mes.get(rep))
    if v is not None and mp:
        _, dotc = estado_chip(v, mp, es_negativo_malo=(rep == "mora_total"))
    else:
        dotc = COLOR_NEUTRO
    valtxt = fmt_val(rep, v) if v is not None else "sin dato"
    filas += (f"<div style='display:flex;justify-content:space-between;align-items:center;padding:11px 4px;border-top:1px solid #262626'>"
              f"<span style='font-size:14px'>{nombre_etapa}</span>"
              f"<span style='display:flex;align-items:center;gap:10px'>"
              f"<span style='font-size:14px;font-weight:700;color:#F2F2F2'>{hsafe(valtxt)}</span>"
              f"<span style='width:9px;height:9px;border-radius:50%;background:{dotc}'></span></span></div>")
html(f"<div style='{CARD}'>{filas}</div>")

# ============ Detalle completo (todos los rubros del período) ============
with st.expander(f"📊 Ver todo el detalle · {periodo_txt}"):
    todos = list(RUBROS_DIARIOS)
    if hay_datos_embudo:
        todos += RUBROS_EMBUDO_TRIADA + ["pct_aprobacion", "agendas_hoy"]
    todos += RUBROS_SOLO_MES
    n_col = 4
    for i in range(0, len(todos), n_col):
        cols = st.columns(n_col)
        for clave, col in zip(todos[i:i + n_col], cols):
            if periodo == "mes":
                tile_rubro(clave, col, "mes", objetivo=objetivos_mes.get(clave),
                           dia_del_mes=dia_por_rubro, dias_mes=dias_mes)
            else:
                tile_rubro(clave, col, periodo)

with st.expander("📈 Proyección de cierre de mes"):
    st.caption("Con el ritmo promedio observado hasta hoy, si nada cambia, ¿en qué cierra el mes?")
    proy_cols = st.columns(3)
    rubros_proyectables = [c for c in ("ci_dinero", "pagos_dinero", "ventas") if objetivos_mes.get(c) and M[c].get("mes") is not None]
    for clave, col in zip(rubros_proyectables, proy_cols):
        val = M[clave]["mes"]
        objetivo = objetivos_mes.get(clave)
        proy, ritmo, ritmo_req = obj.proyeccion_cierre(val, hoy_recaudo.day, dias_mes, objetivo)
        es_dinero = clave in ("ci_dinero", "pagos_dinero")
        fmt = cop if es_dinero else (lambda v: f"{v:,.0f}".replace(",", "."))
        with col:
            with st.container(border=True):
                st.caption(mx.RUBRO_LABEL[clave])
                if proy is not None:
                    brecha = proy - objetivo
                    color = COLOR_OK if brecha >= 0 else (COLOR_ALERTA if brecha >= -objetivo * 0.15 else COLOR_CRIT)
                    st.markdown(f"**Proyección de cierre:** {mdsafe(fmt(proy))}")
                    st.markdown(f"<span style='color:{color}'>Brecha vs. objetivo ({mdsafe(fmt(objetivo))}): {mdsafe(fmt(brecha))}</span>", unsafe_allow_html=True)
                    st.caption(f"Ritmo actual: {mdsafe(fmt(ritmo))}/día · requerido para cerrar en meta: {mdsafe(fmt(ritmo_req))}/día")

if not data["rec"]["semanal"].empty:
    with st.expander("📅 Meta semanal vs. recaudo real"):
        sem = data["rec"]["semanal"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=sem["semana"], y=sem["meta"], name="Meta de la semana", marker_color="#3A3A3A"))
        fig.add_trace(go.Bar(x=sem["semana"], y=sem["ingreso_real"], name="Ingreso real", marker_color=COLOR_OK))
        fig.update_layout(barmode="overlay", height=360, legend=dict(orientation="h", y=1.15),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#F2F2F2")
        st.plotly_chart(fig, use_container_width=True)

with st.expander("🎯 Metas del mes"):
    if not metas:
        st.warning("No se ha cargado `Metas_RODDOS.xlsx` todavía — sube uno en **📤 Actualizar datos**.")
    else:
        st.caption(f"Metas vigentes desde {metas['mes'].strftime('%B %Y').capitalize()} — para cambiarlas, agrega una fila nueva en Metas_RODDOS.xlsx y súbelo en 📤 Actualizar datos.")
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Meta ventas", f"{metas['ventas']:,.0f}".replace(",", "."))
        mc2.metric("Meta % aprobación", f"{metas['pct_aprobacion']*100:.0f}%")
        mc3.metric("Meta % agendas", f"{metas['pct_agendas']*100:.0f}%")
        mc4.metric("Tope de mora", f"{metas['pct_mora_tope']*100:.0f}%")

if not hay_datos_embudo:
    with st.expander("🧲 Embudo comercial — sin datos todavía"):
        st.warning(
            "Leads, formularios, aprobados/rechazados y agendas (rubros 1 a 7) no tienen datos cargados. "
            "Descarga la plantilla, registra, y súbela en **📤 Actualizar datos**."
        )
        _plantilla_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plantillas", "Plantilla_Embudo_Comercial.xlsx")
        try:
            with open(_plantilla_path, "rb") as f:
                st.download_button("⬇️ Descargar plantilla en blanco", f, file_name="Plantilla_Embudo_Comercial.xlsx")
        except FileNotFoundError:
            st.caption("Plantilla no encontrada en esta instancia — pide que la regeneren.")
