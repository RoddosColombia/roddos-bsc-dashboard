import datetime
import calendar
import streamlit as st
import plotly.graph_objects as go

from utils import cop
import metricas as mx
import objetivos as obj
import data_sources as ds

st.set_page_config(page_title="RODDOS — Operación diaria", layout="wide", page_icon="🏍️")

def mdsafe(s):
    """Streamlit interpreta un par de $...$ como formula matematica (KaTeX).
    Escapa el signo de pesos para que '$1.000' no dispare ese modo."""
    return str(s).replace("$", "\\$")


COLOR_OK = "#1F6F5C"
COLOR_ALERTA = "#B7791F"
COLOR_CRIT = "#9C2B0F"
COLOR_NEUTRO = "#7A7A7A"

st.title("🏍️ RODDOS — Operación diaria")
st.caption("Ayer · esta semana · este mes — por rubro de negocio. No incluye RRHH (tiene su propia página).")

data = mx.construir_metricas()
M = data["metricas"]
hoy_recaudo = data["hoy_recaudo"]
hoy_inv = data["hoy_inv"]
hoy_inv_txt = data["hoy_inv_txt"]

c1, c2, c3 = st.columns(3)
c1.info(f"📋 Recaudo — corte de datos: **{hoy_recaudo}**")
c2.info(f"📦 Inventario/Ventas — corte de datos: **{hoy_inv_txt or hoy_inv}**")
mes_actual_key = hoy_recaudo.strftime("%Y-%m")
c3.info(f"🎯 Mes de trabajo: **{calendar.month_name[hoy_recaudo.month].capitalize()} {hoy_recaudo.year}**")

st.caption(
    "Los dos cortes son distintos porque vienen de dos archivos que tu equipo actualiza en momentos distintos. "
    "No se fuerza una sola fecha — cada número muestra el corte real de su propia fuente."
)

# ============ ALERTA DE CONCILIACIÓN (informativa, no permanente/alarmante) ============
conc = data["conc"]
if conc["problemas"]:
    with st.expander(f"🔎 Conciliación SISMO ↔ Wava — {len(conc['problemas'])} casos abiertos, {cop(conc['monto_en_riesgo'])} por confirmar", expanded=False):
        for p in conc["problemas"]:
            st.markdown(f"**{p['num']}. {p['problema']}** — {p['casos']} · {cop(p['monto']) if isinstance(p['monto'], (int, float)) else p['monto']}")
            st.caption(p["solucion"])

st.divider()


RUBROS_SIN_META = {"cuotas_mes", "vencidas_num", "vencidas_dinero"}  # referencia, no objetivo a cumplir
RUBROS_PORCENTAJE = {"pct_aprobacion"}  # se muestran como % en vez de número entero


def estado_chip(valor, meta_esperada_a_hoy, es_negativo_malo=False):
    """Devuelve (texto, color) comparando contra la meta YA PRORRATEADA al día de hoy.
    Nunca marca crítico solo por 'aún no hay dato' ni por estar a mitad de mes."""
    if valor is None or not meta_esperada_a_hoy:
        return "Sin meta definida", COLOR_NEUTRO
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

RUBROS_AYER_SEM = RUBROS_DIARIOS + (RUBROS_EMBUDO_TRIADA if hay_datos_embudo else [])

# ============ 1. ¿CÓMO NOS FUE AYER? ============
st.header("1 · ¿Cómo nos fue ayer?")
n_col = 4
for i in range(0, len(RUBROS_AYER_SEM), n_col):
    cols = st.columns(n_col)
    for clave, col in zip(RUBROS_AYER_SEM[i:i + n_col], cols):
        tile_rubro(clave, col, "ayer")

st.divider()

# ============ 2. ¿CÓMO VAMOS ESTA SEMANA? ============
st.header("2 · ¿Cómo vamos esta semana?")
for i in range(0, len(RUBROS_AYER_SEM), n_col):
    cols = st.columns(n_col)
    for clave, col in zip(RUBROS_AYER_SEM[i:i + n_col], cols):
        tile_rubro(clave, col, "semana")

if not data["rec"]["semanal"].empty:
    st.subheader("Meta semanal vs. recaudo real (Proyeccion_Recaudo.xlsx)")
    sem = data["rec"]["semanal"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sem["semana"], y=sem["meta"], name="Meta de la semana", marker_color="#d9d9d9"))
    fig.add_trace(go.Bar(x=sem["semana"], y=sem["ingreso_real"], name="Ingreso real", marker_color=COLOR_OK))
    fig.update_layout(barmode="overlay", height=360, legend=dict(orientation="h", y=1.15))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============ 3. ¿CÓMO VAMOS ESTE MES? ============
st.header("3 · ¿Cómo vamos este mes?")

metas = ds.leer_metas(hoy_recaudo)
meta_pactada_recaudo = data["rec"]["dashboard"].get("meta_pactada")
objetivos_mes = {}
if metas:
    objetivos_mes["ventas"] = metas["ventas"]
    objetivos_mes["activaciones"] = metas["ventas"]  # una activación por venta, misma meta
    objetivos_mes["ci_dinero"] = metas["ci_dinero"]
    objetivos_mes["pct_aprobacion"] = metas["pct_aprobacion"]
if meta_pactada_recaudo:
    objetivos_mes["pagos_dinero"] = meta_pactada_recaudo
dias_mes = calendar.monthrange(hoy_recaudo.year, hoy_recaudo.month)[1]
RUBROS_FUENTE_INVENTARIO = {"ventas", "facturacion", "ci_completas", "ci_parciales", "ci_dinero", "activaciones", "dias_inventario"}
dia_por_rubro = {c: (hoy_inv.day if c in RUBROS_FUENTE_INVENTARIO else hoy_recaudo.day) for c in mx.RUBROS_ORDEN}

todos_mes = RUBROS_DIARIOS + RUBROS_SOLO_MES
if hay_datos_embudo:
    todos_mes = RUBROS_DIARIOS + RUBROS_EMBUDO_TRIADA + ["pct_aprobacion", "agendas_hoy"] + RUBROS_SOLO_MES
n_col = 4
for i in range(0, len(todos_mes), n_col):
    cols = st.columns(n_col)
    for clave, col in zip(todos_mes[i:i + n_col], cols):
        tile_rubro(clave, col, "mes", objetivo=objetivos_mes.get(clave),
                   dia_del_mes=dia_por_rubro, dias_mes=dias_mes)

st.subheader("Proyección de cierre de mes")
st.caption("Con el ritmo promedio observado hasta hoy, si nada cambia, ¿en qué cierra el mes?")
proy_cols = st.columns(3)
dia_del_mes = hoy_recaudo.day
rubros_proyectables = [c for c in ("ci_dinero", "pagos_dinero", "ventas") if objetivos_mes.get(c) and M[c].get("mes") is not None]
for clave, col in zip(rubros_proyectables, proy_cols):
    val = M[clave]["mes"]
    objetivo = objetivos_mes.get(clave)
    proy, ritmo, ritmo_req = obj.proyeccion_cierre(val, dia_del_mes, dias_mes, objetivo)
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
                st.caption(f"Ritmo actual: {mdsafe(fmt(ritmo))}/día · ritmo requerido para cerrar en meta: {mdsafe(fmt(ritmo_req))}/día")

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

st.divider()

# ============ EMBUDO COMERCIAL (leads, formularios, decisiones, agendas) ============
st.header("Embudo comercial (Marketing / leads)")

if hay_datos_embudo:
    st.success(
        "**Embudo comercial activo.** Los rubros 1 a 7 (leads, formularios, aprobados/rechazados "
        "y agendas de visita) ya se calculan desde el último archivo cargado y aparecen arriba "
        "en las secciones ayer/semana/mes. Para subir una versión más reciente, ve a "
        "**📤 Actualizar datos** en el menú de la izquierda."
    )
else:
    st.warning(
        "**Leads, formularios, aprobados/rechazados y las 4 métricas de agenda de visita "
        "(rubros 1 a 7) no tienen datos cargados todavía.** "
        "Descarga la plantilla, empieza a registrar, y súbela en **📤 Actualizar datos** "
        "(menú de la izquierda) cuando quieras refrescar el tablero."
    )
    rubros_sin_dato_orden = [c for c in mx.RUBROS_ORDEN if c in mx.RUBROS_SIN_DATO]
    n_col_sd = 4
    for i in range(0, len(rubros_sin_dato_orden), n_col_sd):
        cols_sin_dato = st.columns(n_col_sd)
        for clave, col in zip(rubros_sin_dato_orden[i:i + n_col_sd], cols_sin_dato):
            with col:
                with st.container(border=True):
                    st.caption(mx.RUBRO_LABEL[clave])
                    st.markdown("**Sin dato**")
                    st.caption(M[clave]["fuente"])

import os as _os
_plantilla_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "plantillas", "Plantilla_Embudo_Comercial.xlsx")
try:
    with open(_plantilla_path, "rb") as f:
        st.download_button("⬇️ Descargar plantilla en blanco", f, file_name="Plantilla_Embudo_Comercial.xlsx")
except FileNotFoundError:
    st.caption("Plantilla no encontrada en esta instancia — pide que la regeneren.")
