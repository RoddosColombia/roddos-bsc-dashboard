import streamlit as st
import plotly.graph_objects as go
from utils import cop
import acceso
import data_sources as ds

st.set_page_config(page_title="RRHH — RODDOS BSC", layout="wide", page_icon="👥")
acceso.exigir_director()


def mdsafe(s):
    return str(s).replace("$", "\\$")


COLOR_OK = "#1F6F5C"
COLOR_ALERTA = "#B7791F"
COLOR_CRIT = "#9C2B0F"

st.title("👥 RRHH — Nómina y equipo")
st.caption("Calculado desde la última carga de Control_RRHH_Nomina_RODDOS_2026.xlsx (sube una versión nueva en 📤 Actualizar datos). No sigue el esquema ayer/semana/mes de las demás páginas — la nómina se liquida una vez al mes, no a diario.")

rrhh = ds.leer_rrhh()

if rrhh["nomina"].empty or "Empleado" not in rrhh["nomina"].columns:
    st.warning(
        "**El archivo de RRHH tiene fórmulas sin recalcular.** Esto pasa cuando se edita "
        "por fuera de Excel (por ejemplo, para agregar un empleado nuevo): las fórmulas "
        "quedan correctas, pero el valor en caché que Excel guarda para lectura rápida se "
        "pierde. Abre `Control_RRHH_Nomina_RODDOS_2026.xlsx` en Excel una vez y guárdalo "
        "(Ctrl+S) — recalcula todo automáticamente — y esta página se actualiza sola."
    )
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.caption("Headcount")
        st.markdown(f"### {rrhh['headcount']}")
with c2:
    with st.container(border=True):
        st.caption("Costo total empresa (nómina formal)")
        st.markdown(f"### {mdsafe(cop(rrhh['costo_total_empresa_mes']))}/mes")
with c3:
    with st.container(border=True):
        st.caption("Neto legal a pagar (total)")
        st.markdown(f"### {mdsafe(cop(rrhh['neto_legal_total']))}")

if rrhh["brecha_legal_total"]:
    st.warning(
        f"**Brecha neto legal vs. práctica actual: {cop(rrhh['brecha_legal_total'])}/mes.** "
        "Es FSP + retefuente que la regla del 40% (Ley 1393/2010) obliga a descontar en los cargos "
        "de mayor ingreso, pero que hoy no se está reteniendo en la práctica. Fuente: hoja NominaMensual."
    )

st.divider()

st.subheader("Costo total empresa por persona")
nom = rrhh["nomina"]
fig = go.Figure()
fig.add_trace(go.Bar(x=nom["Empleado"], y=nom["COSTO TOTAL EMPRESA/MES"], marker_color="#6B46C1", name="Costo total empresa"))
fig.add_trace(go.Bar(x=nom["Empleado"], y=nom["Total devengado"], marker_color="#B794F4", name="Total devengado"))
fig.update_layout(barmode="group", yaxis_title="$/mes", height=420, legend=dict(orientation="h", y=1.1))
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
    with st.container(border=True):
        st.caption("Días pendientes acumulados (todo el equipo)")
        st.markdown(f"### {rrhh['dias_pendientes_total']:.0f}")
with cv2:
    with st.container(border=True):
        st.caption("Provisión pendiente estimada")
        st.markdown(f"### {mdsafe(cop(rrhh['provision_vacaciones_total']))}")

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
