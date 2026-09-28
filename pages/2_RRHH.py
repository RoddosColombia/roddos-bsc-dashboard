import streamlit as st
import plotly.graph_objects as go
from utils import cop, estilo_roddos, kpi
import acceso
import data_sources as ds

st.set_page_config(page_title="RRHH — RODDOS BSC", layout="wide", page_icon="👥")
estilo_roddos()
acceso.exigir_director()

st.title("👥 RRHH — Nómina y equipo")
st.caption("Calculado desde la última carga de Control_RRHH_Nomina_RODDOS_2026.xlsx. La nómina se liquida una vez al mes, no a diario, por eso no sigue el esquema ayer/semana/mes.")

rrhh = ds.leer_rrhh()

if rrhh["nomina"].empty or "Empleado" not in rrhh["nomina"].columns:
    st.warning(
        "**El archivo de RRHH tiene fórmulas sin recalcular.** Pasa cuando se edita por fuera de Excel "
        "(por ejemplo, al agregar un empleado): las fórmulas quedan bien, pero el valor en caché se pierde. "
        "Abre `Control_RRHH_Nomina_RODDOS_2026.xlsx` en Excel una vez y guárdalo (Ctrl+S) — recalcula todo — "
        "y esta página se actualiza sola."
    )
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    kpi("Headcount", f"{rrhh['headcount']}")
with c2:
    kpi("Costo total empresa · nómina formal", f"{cop(rrhh['costo_total_empresa_mes'])}/mes")
with c3:
    kpi("Neto legal a pagar · total", cop(rrhh["neto_legal_total"]))

if rrhh["brecha_legal_total"]:
    st.warning(
        f"**Brecha neto legal vs. práctica actual: {cop(rrhh['brecha_legal_total'])}/mes.** "
        "Es FSP + retefuente que la regla del 40% (Ley 1393/2010) obliga a descontar en los cargos "
        "de mayor ingreso, pero que hoy no se está reteniendo. Fuente: hoja NominaMensual."
    )

st.write("")
st.subheader("Costo total empresa por persona")
nom = rrhh["nomina"]
fig = go.Figure()
fig.add_trace(go.Bar(x=nom["Empleado"], y=nom["COSTO TOTAL EMPRESA/MES"], marker_color="#00E5FF", name="Costo total empresa"))
fig.add_trace(go.Bar(x=nom["Empleado"], y=nom["Total devengado"], marker_color="#3A6E7A", name="Total devengado"))
fig.update_layout(barmode="group", yaxis_title="$/mes", height=420, legend=dict(orientation="h", y=1.1),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#F2F2F2")
st.plotly_chart(fig, use_container_width=True)
st.caption("Costo total empresa incluye aportes patronales y provisión de prestaciones; total devengado es lo que recibe el empleado.")

with st.expander("Ver tabla completa de nómina"):
    st.dataframe(
        nom.style.format({
            "Salario": cop, "Auxilio transporte": cop, "Bonificación no salarial": cop,
            "Total devengado": cop, "NETO LEGAL a pagar": cop, "Neto práctica actual (solo salud+pensión)": cop,
            "Brecha vs. legal": cop, "COSTO TOTAL EMPRESA/MES": cop,
        }),
        use_container_width=True,
    )

st.divider()

st.subheader("Vacaciones")
vac = rrhh["vacaciones"]
cv1, cv2 = st.columns(2)
with cv1:
    kpi("Días pendientes acumulados · todo el equipo", f"{rrhh['dias_pendientes_total']:.0f}")
with cv2:
    kpi("Provisión pendiente estimada", cop(rrhh["provision_vacaciones_total"]))

alertas = vac[vac["Alerta"] != "OK"] if "Alerta" in vac.columns else vac.iloc[0:0]
if not alertas.empty:
    st.error(f"⚠️ {len(alertas)} empleado(s) con alerta de vacaciones: " + ", ".join(alertas["Empleado"].tolist()))
else:
    st.caption("Sin alertas de vacaciones vencidas o por vencer.")

with st.expander("Ver detalle de vacaciones por empleado"):
    st.dataframe(
        vac.style.format({"Valor día (salario/30)": cop, "Provisión pendiente estimada": cop}),
        use_container_width=True,
    )

st.divider()
st.info("Falta incorporar: rotación de personal y ausentismo — no están en el archivo fuente. Responsable: RRHH.")
