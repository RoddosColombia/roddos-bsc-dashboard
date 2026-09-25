import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils import cop
import acceso
import data_sources as ds

st.set_page_config(page_title="Tesorería — RODDOS BSC", layout="wide", page_icon="💰")
acceso.exigir_director()


def mdsafe(s):
    return str(s).replace("$", "\\$")


COLOR_OK = "#1F6F5C"
COLOR_ALERTA = "#B7791F"
COLOR_CRIT = "#9C2B0F"

st.title("💰 Tesorería y flujo de caja")
st.caption("Ayer · esta semana · este mes — calculado desde la última carga de Flujo_Pagos_Deudas.xlsx (hoja Tablero mes + Base real egresos/ingresos). Sube una versión nueva en 📤 Actualizar datos.")

tes = ds.leer_tesoreria()
dash = tes["dashboard"]
egresos = tes["egresos"]
ingresos = tes["ingresos"]

hoy = dash["corte_fecha"] or egresos["Fecha"].max().date()
ayer = hoy - datetime.timedelta(days=1)
semana_ini = hoy - datetime.timedelta(days=hoy.weekday())
mes_ini = hoy.replace(day=1)

al_dia = "AL DÍA" in (dash["corte_txt"] or "").upper()
c1, c2 = st.columns(2)
c1.info(f"📅 Corte: **{hoy}** ({'al día' if al_dia else 'ver detalle'}) · Mes de control: **{dash['mes_control'].strftime('%B %Y').capitalize() if dash['mes_control'] else '—'}**")
c2.info(f"🏦 Caja disponible total (todas las cuentas): **{cop(dash['caja_disponible_total'])}**")

if dash["egresos_por_clasificar"]:
    st.caption(f"⚠️ {cop(dash['egresos_por_clasificar'])} en movimientos aún por clasificar — no cambia la caja, pero puede reasignar categorías al depurarse.")

st.divider()


def egresos_en(desde, hasta):
    m = egresos[(egresos["Fecha"].dt.date >= desde) & (egresos["Fecha"].dt.date <= hasta)]
    return float(m["Valor"].fillna(0).sum())


def ingresos_en(desde, hasta):
    m = ingresos[(ingresos["Fecha"].dt.date >= desde) & (ingresos["Fecha"].dt.date <= hasta)]
    return float(m["Valor"].fillna(0).sum())


def tile_flujo(col, label, valor, negativo_es_malo=True):
    with col:
        with st.container(border=True):
            st.caption(label)
            color = None
            if negativo_es_malo:
                color = COLOR_OK if valor >= 0 else COLOR_CRIT
            st.markdown(f"<span style='font-size:26px; font-weight:700; color:{color or 'inherit'}'>{mdsafe(cop(valor))}</span>", unsafe_allow_html=True)


st.header("1 · ¿Cómo nos fue ayer?")
cols = st.columns(3)
ing_ayer, egr_ayer = ingresos_en(ayer, ayer), egresos_en(ayer, ayer)
tile_flujo(cols[0], "Ingresos", ing_ayer, negativo_es_malo=False)
tile_flujo(cols[1], "Egresos", egr_ayer, negativo_es_malo=False)
tile_flujo(cols[2], "Resultado neto", ing_ayer - egr_ayer)

st.divider()

st.header("2 · ¿Cómo vamos esta semana?")
cols = st.columns(3)
ing_sem, egr_sem = ingresos_en(semana_ini, hoy), egresos_en(semana_ini, hoy)
tile_flujo(cols[0], "Ingresos (lun-hoy)", ing_sem, negativo_es_malo=False)
tile_flujo(cols[1], "Egresos (lun-hoy)", egr_sem, negativo_es_malo=False)
tile_flujo(cols[2], "Resultado neto", ing_sem - egr_sem)

egr_sem_cat = egresos[(egresos["Fecha"].dt.date >= semana_ini) & (egresos["Fecha"].dt.date <= hoy)]
if not egr_sem_cat.empty:
    top_cat = egr_sem_cat.groupby("Categoría normalizada")["Valor"].sum().sort_values(ascending=False).head(6)
    fig = go.Figure(go.Bar(x=top_cat.values, y=top_cat.index, orientation="h", marker_color=COLOR_ALERTA))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), title="Egresos de la semana por categoría (top 6)")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

st.header("3 · ¿Cómo vamos este mes?")
cols = st.columns(4)
with cols[0]:
    with st.container(border=True):
        st.caption("Presupuesto del mes")
        st.markdown(f"### {mdsafe(cop(dash['presupuesto_mes']))}")
        st.progress(min(1.0, dash["ejecutado_mes"] / dash["presupuesto_mes"]) if dash["presupuesto_mes"] else 0,
                    text=f"Ejecutado: {cop(dash['ejecutado_mes'])} ({dash['ejecutado_mes']/dash['presupuesto_mes']*100:.0f}%)" if dash["presupuesto_mes"] else "Ejecutado: —")
with cols[1]:
    with st.container(border=True):
        st.caption("Ingreso real del mes")
        st.markdown(f"### {mdsafe(cop(dash['ingreso_real_mes']))}")
        color = COLOR_OK if dash["pct_cumplimiento_meta"] >= 0.95 else (COLOR_ALERTA if dash["pct_cumplimiento_meta"] >= 0.75 else COLOR_CRIT)
        st.markdown(f"<span style='color:{color}; font-weight:700'>{dash['pct_cumplimiento_meta']*100:.0f}% de la meta del mes</span>", unsafe_allow_html=True)
with cols[2]:
    with st.container(border=True):
        st.caption("Resultado del mes (ingreso − egreso)")
        color = COLOR_OK if dash["resultado_mes"] >= 0 else COLOR_CRIT
        st.markdown(f"<span style='font-size:22px; font-weight:700; color:{color}'>{mdsafe(cop(dash['resultado_mes']))}</span>", unsafe_allow_html=True)
with cols[3]:
    with st.container(border=True):
        st.caption("Mayor egreso en un día (mes)")
        st.markdown(f"### {mdsafe(cop(dash['mayor_egreso_dia']))}")

st.caption(f"Fuente: Flujo_Pagos_Deudas.xlsx · Tablero mes — corte {dash['corte_txt'].strip()}")

st.divider()

# ============ RESULTADO OBJETIVO DEL MES (Fase 1, decisión #4 — 2026-09-23) ============
st.header("Resultado objetivo del mes")
st.caption(
    "Reemplaza los dos modelos de proyección que competían aquí (Proyección 18M del archivo real "
    "y el modelo del informe financiero). Fórmula definida por la dirección: cuánto debería quedar "
    "en caja este mes si se cumplen las metas de recaudo y ventas, después de los gastos fijos y Auteco."
)

metas = ds.leer_metas()
recaudo = ds.leer_recaudo()
meta_pactada_recaudo = recaudo["dashboard"].get("meta_pactada") or 0
pago_auteco_mes = dash.get("pago_auteco_mes") or 0

if not metas:
    st.warning("No se ha cargado `Metas_RODDOS.xlsx` todavía — sube uno en **📤 Actualizar datos** para ver este cálculo.")
else:
    meta_ci = metas["ci_dinero"]
    gasto_fijo = metas["gasto_fijo"]
    resultado_objetivo = meta_pactada_recaudo + meta_ci - gasto_fijo - pago_auteco_mes

    st.markdown("**Ingreso objetivo por recaudo de cuotas semanales** (meta pactada, `Proyeccion_Recaudo.xlsx` · Resumen Semanal)")
    st.markdown(f"### {mdsafe(cop(meta_pactada_recaudo))}")
    st.markdown("**+ Ingreso objetivo por cuotas iniciales** (`Metas_RODDOS.xlsx`)")
    st.markdown(f"### {mdsafe(cop(meta_ci))}")
    st.markdown("**− Gasto fijo mensual** (`Metas_RODDOS.xlsx`)")
    st.markdown(f"### {mdsafe(cop(gasto_fijo))}")
    st.markdown("**− Pago a Auteco del mes** (calculado en vivo: saldo pendiente de facturas con vencimiento este mes, `Flujo_Pagos_Deudas.xlsx` · Facturas Auteco)")
    st.markdown(f"### {mdsafe(cop(pago_auteco_mes))}")

    st.divider()
    color_res = COLOR_OK if resultado_objetivo >= 0 else COLOR_CRIT
    st.markdown("**= Resultado objetivo del mes**")
    st.markdown(f"<span style='font-size:32px; font-weight:700; color:{color_res}'>{mdsafe(cop(resultado_objetivo))}</span>", unsafe_allow_html=True)

    st.caption(
        f"Este resultado asume que se cumple la meta de ventas del mes ({metas['ventas']:.0f} unidades) — "
        "es de ahí que sale el ingreso objetivo de cuotas iniciales. Si el inventario disponible no alcanza "
        "para sostener esas ventas, este resultado no se va a cumplir aunque la cartera pague al día. "
        "Ver 'Motos disponibles' y 'Días de inventario' en la página principal."
    )
