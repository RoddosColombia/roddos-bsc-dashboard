import datetime
import streamlit as st
import plotly.graph_objects as go

from utils import cop, estilo_roddos, html, hsafe, kpi, hero
import acceso
import data_sources as ds

st.set_page_config(page_title="Tesorería — RODDOS BSC", layout="wide", page_icon="💰")
estilo_roddos()
acceso.exigir_director()

COLOR_OK = "#00C853"
COLOR_ALERTA = "#FFB300"
COLOR_CRIT = "#FF5252"

st.title("💰 Tesorería y flujo de caja")

tes = ds.leer_tesoreria()
dash = tes["dashboard"]
egresos = tes["egresos"]
ingresos = tes["ingresos"]

hoy = dash["corte_fecha"] or egresos["Fecha"].max().date()
ayer = hoy - datetime.timedelta(days=1)
semana_ini = hoy - datetime.timedelta(days=hoy.weekday())

al_dia = "AL DÍA" in (dash["corte_txt"] or "").upper()
c1, c2 = st.columns(2)
c1.caption(f"📅 Corte {hoy} ({'al día' if al_dia else 'ver detalle'})")
c2.caption(f"🗓️ Mes de control: {dash['mes_control'].strftime('%B %Y').capitalize() if dash['mes_control'] else '—'}")

res_mes = dash["resultado_mes"]
hero("Caja disponible total · todas las cuentas", cop(dash["caja_disponible_total"]),
     chip_txt=f"resultado del mes {cop(res_mes)}",
     chip_color=COLOR_OK if res_mes >= 0 else COLOR_CRIT)
if dash["egresos_por_clasificar"]:
    st.caption(f"⚠️ {cop(dash['egresos_por_clasificar'])} en movimientos aún por clasificar — no cambia la caja, pero puede reasignar categorías al depurarse.")

st.write("")


def egresos_en(desde, hasta):
    m = egresos[(egresos["Fecha"].dt.date >= desde) & (egresos["Fecha"].dt.date <= hasta)]
    return float(m["Valor"].fillna(0).sum())


def ingresos_en(desde, hasta):
    m = ingresos[(ingresos["Fecha"].dt.date >= desde) & (ingresos["Fecha"].dt.date <= hasta)]
    return float(m["Valor"].fillna(0).sum())


def flujo(cols, ing, egr, etiqueta_extra=""):
    neto = ing - egr
    with cols[0]:
        kpi(f"Ingresos {etiqueta_extra}".strip(), cop(ing))
    with cols[1]:
        kpi(f"Egresos {etiqueta_extra}".strip(), cop(egr))
    with cols[2]:
        kpi("Resultado neto", cop(neto), valor_color=COLOR_OK if neto >= 0 else COLOR_CRIT)


st.subheader("1 · ¿Cómo nos fue ayer?")
flujo(st.columns(3), ingresos_en(ayer, ayer), egresos_en(ayer, ayer))

st.subheader("2 · ¿Cómo vamos esta semana?")
flujo(st.columns(3), ingresos_en(semana_ini, hoy), egresos_en(semana_ini, hoy), "(lun-hoy)")

egr_sem_cat = egresos[(egresos["Fecha"].dt.date >= semana_ini) & (egresos["Fecha"].dt.date <= hoy)]
if not egr_sem_cat.empty:
    with st.expander("Egresos de la semana por categoría"):
        top_cat = egr_sem_cat.groupby("Categoría normalizada")["Valor"].sum().sort_values(ascending=False).head(6)
        fig = go.Figure(go.Bar(x=top_cat.values, y=top_cat.index, orientation="h", marker_color=COLOR_ALERTA))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#F2F2F2")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("3 · ¿Cómo vamos este mes?")
mcols = st.columns(4)
with mcols[0]:
    pct_pres = dash["ejecutado_mes"] / dash["presupuesto_mes"] if dash["presupuesto_mes"] else 0
    kpi("Presupuesto del mes", cop(dash["presupuesto_mes"]),
        sub=f"Ejecutado {cop(dash['ejecutado_mes'])} ({pct_pres*100:.0f}%)" if dash["presupuesto_mes"] else "Ejecutado —")
with mcols[1]:
    pctm = dash["pct_cumplimiento_meta"]
    cmeta = COLOR_OK if pctm >= 0.95 else (COLOR_ALERTA if pctm >= 0.75 else COLOR_CRIT)
    kpi("Ingreso real del mes", cop(dash["ingreso_real_mes"]),
        chip_txt=f"{pctm*100:.0f}% de la meta", chip_color=cmeta)
with mcols[2]:
    kpi("Resultado del mes", cop(dash["resultado_mes"]),
        valor_color=COLOR_OK if dash["resultado_mes"] >= 0 else COLOR_CRIT)
with mcols[3]:
    kpi("Mayor egreso en un día", cop(dash["mayor_egreso_dia"]))

st.caption(f"Fuente: Flujo_Pagos_Deudas.xlsx · Tablero mes — corte {dash['corte_txt'].strip()}")

st.divider()

# ============ RESULTADO OBJETIVO DEL MES ============
st.subheader("🎯 Resultado objetivo del mes")
st.caption(
    "Cuánto debería quedar en caja este mes si se cumplen las metas de recaudo y ventas, "
    "después de los gastos fijos y el pago a Auteco. Fórmula definida por la dirección."
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

    def linea(signo, etiqueta, valor):
        return (f"<div style='display:flex;justify-content:space-between;align-items:center;padding:10px 4px;border-top:1px solid #262626'>"
                f"<span style='font-size:14px;color:#B8BCC0'>{signo} {etiqueta}</span>"
                f"<span style='font-size:16px;font-weight:700;color:#F2F2F2;font-family:Montserrat,sans-serif'>{hsafe(cop(valor))}</span></div>")

    filas = (linea("+", "Recaudo objetivo de cuotas semanales (meta pactada)", meta_pactada_recaudo)
             + linea("+", "Ingreso objetivo por cuotas iniciales (Metas)", meta_ci)
             + linea("−", "Gasto fijo mensual (Metas)", -gasto_fijo)
             + linea("−", "Pago a Auteco del mes (facturas que vencen este mes)", -pago_auteco_mes))
    html(f"<div style='background:#1A1A1A;border:1px solid #2C2C2C;border-radius:14px;padding:8px 16px'>{filas}</div>")

    st.write("")
    hero("= Resultado objetivo del mes", cop(resultado_objetivo),
         chip_txt="en verde" if resultado_objetivo >= 0 else "en rojo",
         chip_color=COLOR_OK if resultado_objetivo >= 0 else COLOR_CRIT)

    st.caption(
        f"Asume que se cumple la meta de ventas ({metas['ventas']:.0f} unidades) — de ahí sale el ingreso "
        "de cuotas iniciales. Si el inventario disponible no alcanza para esas ventas, este resultado no se "
        "cumple aunque la cartera pague al día. Ver 'Días de inventario' en la página principal."
    )
