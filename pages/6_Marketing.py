"""Marketing: funnel por canal y campaña (lead → solicitud → aprobado → compra).

Solo lee los totales que calcula funnel/ejecutar.py cada día (bsc_dashboard.funnel_resumen).
No hay datos personales en esta página.
"""
import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_sources as ds
import graficos
from funnel import almacen, calculo
from utils import CIAN, MUT, VERDE, encabezado, estilo_roddos, kpi

st.set_page_config(page_title="Marketing — RODDOS BSC", layout="wide", page_icon="📣")
estilo_roddos()
encabezado("Marketing · De dónde llegan los clientes que compran")

try:
    resumen = almacen.leer(ds.db_respaldo())
except Exception as e:  # sin conexión a la base del tablero
    st.warning(f"No se pudieron leer los datos del funnel: {e}")
    st.stop()

if not resumen:
    st.info("📭 **Todavía no hay datos del funnel.** Se calculan solos todos los días a las 6 a. m. "
            "(GitHub Actions → «Funnel de marketing»). Si es la primera vez, se puede correr a mano "
            "desde esa misma pantalla con «Run workflow».")
    st.stop()

generado = resumen["generado_en"] - dt.timedelta(hours=5)
st.caption(f"Actualizado el {generado:%d/%m/%Y a las %H:%M} (hora Colombia) · datos desde el "
           f"{resumen['desde'] - dt.timedelta(hours=5):%d/%m/%Y}. Fuentes: Inventario 2026 (Facturación), "
           "solicitudes de roddos.com y conversaciones de WhatsApp, Instagram y Messenger de CRM-RODDOS.")

coh = pd.DataFrame(resumen["cohortes"])
meses = sorted(set(coh["mes"])) if not coh.empty else []
NOMBRE_MES = {"01": "ene", "02": "feb", "03": "mar", "04": "abr", "05": "may", "06": "jun",
              "07": "jul", "08": "ago", "09": "sep", "10": "oct", "11": "nov", "12": "dic"}


def mes_txt(m):
    return f"{NOMBRE_MES[m[5:]]} {m[:4]}"


f1, f2 = st.columns([3, 2])
with f1:
    elegidos = st.multiselect("Meses", meses, default=meses, format_func=mes_txt, key="mk_meses")
with f2:
    modelo_txt = st.radio("Canal que se le asigna a cada solicitud", ["Primer contacto", "Último contacto"],
                          horizontal=True, key="mk_modelo",
                          help="Primer contacto: lo que lo trajo por primera vez en los 30 días antes de "
                               "solicitar. Último contacto: lo último que tocó antes de solicitar.")
modelo = "primer" if modelo_txt == "Primer contacto" else "ultimo"
elegidos = elegidos or meses


def filtrar(filas):
    df = pd.DataFrame(filas)
    return df[df["mes"].isin(elegidos)] if not df.empty else df


def alto(df):
    """Alto para mostrar la tabla completa, sin barra de desplazamiento."""
    return 38 + 35 * len(df)


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "—"


coh_f = filtrar(resumen["cohortes"])
coh_f = coh_f[coh_f["modelo"] == modelo] if not coh_f.empty else coh_f
leads = filtrar(resumen["leads"])
calidad = filtrar(resumen["calidad"])
ventas = filtrar(resumen["ventas"])
campanas = filtrar(resumen["campanas"])

tot_sol = int(coh_f["solicitudes"].sum()) if not coh_f.empty else 0
tot_apr = int(coh_f["aprobados"].sum()) if not coh_f.empty else 0
tot_com = int(coh_f["compras"].sum()) if not coh_f.empty else 0
tot_leads = int(leads["leads"].sum()) if not leads.empty else 0
sin_origen = int(calidad["sin_origen"].sum()) if not calidad.empty else 0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi("Leads nuevos", f"{tot_leads:,}".replace(",", "."), sub="WhatsApp, Instagram y Messenger")
with c2:
    kpi("Solicitudes", f"{tot_sol:,}".replace(",", "."), sub="formularios en roddos.com")
with c3:
    kpi("Aprobados", f"{tot_apr:,}".replace(",", "."), sub=f"{pct(tot_apr, tot_sol)} de las solicitudes")
with c4:
    kpi("Compraron", f"{tot_com:,}".replace(",", "."), sub=f"{pct(tot_com, tot_sol)} de las solicitudes",
        valor_color=VERDE)
with c5:
    kpi("Solicitudes sin origen", pct(sin_origen, tot_sol),
        sub="no se sabe de dónde llegaron (meta: bajar)", valor_color=MUT)

st.caption("Las compras se cuentan en el mes de la **solicitud**: los meses recientes todavía pueden subir, "
           "porque hay gente aprobada que compra días o semanas después.")

# ---------------------------------------------------------------- conversión por canal
st.subheader("¿Qué canal convierte en venta?")
if coh_f.empty:
    st.caption("Sin solicitudes en los meses elegidos.")
else:
    por_canal = (coh_f.groupby("canal")[["solicitudes", "aprobados", "compras"]].sum()
                 .sort_values("solicitudes", ascending=False).reset_index())
    por_canal["% aprobados"] = [pct(a, s) for a, s in zip(por_canal["aprobados"], por_canal["solicitudes"])]
    por_canal["% compra (de solicitudes)"] = [pct(c, s) for c, s in zip(por_canal["compras"], por_canal["solicitudes"])]
    por_canal["% compra (de aprobados)"] = [pct(c, a) for c, a in zip(por_canal["compras"], por_canal["aprobados"])]

    g1, g2 = st.columns([3, 2])
    with g1:
        orden = por_canal.sort_values("compras")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=orden["canal"], x=orden["solicitudes"], orientation="h", name="Solicitudes",
                             marker_color="rgba(56,217,240,0.35)"))
        fig.add_trace(go.Bar(y=orden["canal"], x=orden["compras"], orientation="h", name="Compras",
                             marker_color=VERDE))
        fig.update_layout(barmode="overlay", height=max(320, 34 * len(orden)), legend=dict(orientation="h", y=1.08),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#EEF2F4",
                          margin=dict(l=10, r=20, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with g2:
        canales = ["Todos los canales"] + por_canal["canal"].tolist()
        canal = st.selectbox("Embudo de", canales, key="mk_canal")
        fila = por_canal[por_canal["canal"] == canal] if canal != canales[0] else por_canal
        st.plotly_chart(graficos.embudo([("Solicitudes", int(fila["solicitudes"].sum())),
                                         ("Aprobados", int(fila["aprobados"].sum())),
                                         ("Compraron", int(fila["compras"].sum()))]),
                        use_container_width=True, config={"displayModeBar": False})
    st.dataframe(por_canal.rename(columns={"canal": "Canal", "solicitudes": "Solicitudes",
                                           "aprobados": "Aprobados", "compras": "Compras"}),
                 hide_index=True, use_container_width=True, height=alto(por_canal))
    with st.expander("¿Qué significa cada canal?"):
        st.markdown(
            f"- **{calculo.META_ANUNCIO_WA}**: escribió por WhatsApp desde un anuncio de Facebook o Instagram.\n"
            f"- **{calculo.META_LANDING}**: llegó a roddos.com desde un anuncio de Facebook o Instagram.\n"
            f"- **{calculo.GOOGLE_ADS}**: llegó desde un anuncio de Google.\n"
            f"- **{calculo.LANDING_WA}**: tocó el botón de WhatsApp de la página de campaña (código LP).\n"
            "- **WhatsApp · bot Alexandra / flujo / asesor / plantilla**: abrió el enlace del formulario "
            "que le mandamos por WhatsApp (se mide desde nov-2026).\n"
            f"- **{calculo.WA_SIN_MARCA}**: nos escribió por WhatsApp antes de solicitar, sin anuncio ni código "
            "(orgánico, referido, alguien le pasó el número…).\n"
            f"- **{calculo.CONTACTO_RODDOS}**: un asesor le escribió primero, antes de que solicitara.\n"
            f"- **{calculo.SITIO}**: entró directo a roddos.com o desde Google sin anuncio (se mide desde nov-2026).\n"
            f"- **{calculo.SIN_ORIGEN}**: no hay rastro de cómo llegó (casi todo es anterior a nov-2026).")

# ---------------------------------------------------------------- leads
st.subheader("Leads: ¿cuántos llegan a solicitar?")
if leads.empty:
    st.caption("Sin leads en los meses elegidos.")
else:
    por_fuente = (leads.groupby("fuente")[["leads", "con_telefono", "con_solicitud"]].sum()
                  .sort_values("leads", ascending=False).reset_index())
    por_fuente["% que solicita"] = [pct(c, n) for c, n in zip(por_fuente["con_solicitud"], por_fuente["leads"])]
    st.dataframe(por_fuente.rename(columns={"fuente": "Fuente", "leads": "Leads", "con_telefono": "Con teléfono",
                                            "con_solicitud": "Con solicitud"}),
                 hide_index=True, use_container_width=True, height=alto(por_fuente))
    st.caption("Lead = persona que nos escribió por primera vez. Instagram, Messenger y quienes usan nombre de "
               "usuario en WhatsApp no comparten su teléfono, así que todavía no se pueden unir con su solicitud.")

# ---------------------------------------------------------------- campañas
st.subheader("Campañas y anuncios")
with st.container():
    st.markdown("**Solicitudes por campaña** (primer contacto) · las 25 con más compras")
    if campanas.empty:
        st.caption("Sin campañas en los meses elegidos.")
    else:
        tabla = (campanas.groupby(["canal", "campana"])[["solicitudes", "aprobados", "compras"]].sum()
                 .sort_values(["compras", "solicitudes"], ascending=False).reset_index().head(25))
        st.dataframe(tabla.rename(columns={"canal": "Canal", "campana": "Campaña / anuncio",
                                           "solicitudes": "Solicitudes", "aprobados": "Aprobados",
                                           "compras": "Compras"}),
                     hide_index=True, use_container_width=True, height=alto(tabla))
with st.container():
    st.markdown("**Leads por anuncio y código de landing** · los 25 con más leads")
    con_campana = leads[leads["campana"] != ""] if not leads.empty else leads
    if con_campana.empty:
        st.caption("Sin leads de anuncios o landing en los meses elegidos.")
    else:
        tabla = (con_campana.groupby(["fuente", "campana"])[["leads", "con_solicitud"]].sum()
                 .sort_values("leads", ascending=False).reset_index().head(25))
        st.dataframe(tabla.rename(columns={"fuente": "Fuente", "campana": "Anuncio / código",
                                           "leads": "Leads", "con_solicitud": "Con solicitud"}),
                     hide_index=True, use_container_width=True, height=alto(tabla))

# ---------------------------------------------------------------- declarado vs medido
st.subheader("Ventas: lo que dice el cliente vs. lo que medimos")
if ventas.empty:
    st.caption("Sin ventas en los meses elegidos.")
else:
    matriz = ventas.pivot_table(index="canal_declarado", columns="canal_medido", values="ventas",
                                aggfunc="sum", fill_value=0)
    matriz["Total"] = matriz.sum(axis=1)
    matriz = matriz.sort_values("Total", ascending=False)
    matriz.index.name = "Dijo el cliente ↓ · Medido →"
    matriz.columns.name = None
    st.dataframe(matriz, use_container_width=True, height=alto(matriz))
    unidas = int(ventas[ventas["con_solicitud"]]["ventas"].sum())
    total_v = int(ventas["ventas"].sum())
    st.caption(f"Filas: «Canal venta» que anota el asesor en Facturación. Columnas: canal medido. "
               f"{unidas} de {total_v} ventas ({pct(unidas, total_v)}) se unieron con su solicitud por documento "
               "o celular; las demás se miden por su celular en WhatsApp.")
    dudosos = resumen.get("avisos", {}).get("canal_venta_dudosos", 0)
    if dudosos:
        st.caption(f"{dudosos} venta(s) con un «Canal venta» que no está en la lista se clasificaron como mejor "
                   "se pudo (p. ej. «INSTAGRAM» a secas puede ser pauta u orgánico).")

# ---------------------------------------------------------------- calidad
st.subheader("Calidad del dato")
if not calidad.empty:
    cal = calidad.sort_values("mes")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[mes_txt(m) for m in cal["mes"]],
                         y=[100 * s / t if t else 0 for s, t in zip(cal["sin_origen"], cal["solicitudes"])],
                         name="% solicitudes sin origen", marker_color=MUT))
    fig.add_trace(go.Bar(x=[mes_txt(m) for m in cal["mes"]],
                         y=[100 * u / v if v else 0 for u, v in zip(cal["ventas_con_solicitud"], cal["ventas"])],
                         name="% ventas unidas con su solicitud", marker_color=CIAN))
    fig.update_layout(barmode="group", height=320, yaxis_title="%", legend=dict(orientation="h", y=1.1),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#EEF2F4")
    graficos.pulir(fig, "numero")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("«Sin origen» debe bajar desde nov-2026: roddos.com ya guarda el origen en todas sus páginas y los "
               "enlaces que mandamos por WhatsApp llevan su marca (utm).")
