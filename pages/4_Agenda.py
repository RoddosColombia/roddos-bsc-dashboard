import calendar
import datetime
import streamlit as st

from utils import estilo_roddos, encabezado, html, hsafe, CARD, CIAN, VERDE, ROJO, MUT, TXT, TXT2, BORDE, TRACK
import data_sources as ds

st.set_page_config(page_title="Agenda — RODDOS BSC", layout="wide", page_icon="🗓️")
estilo_roddos()
encabezado("Agenda de visitas")

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

emb = ds.leer_embudo()
if emb.empty or "Fecha agenda visita" not in emb.columns:
    st.info("🗓️ Aún no hay visitas agendadas. Registra clientes con su **Fecha agenda visita** en el "
            "Embudo Comercial y súbelo en **📤 Actualizar datos**; la agenda se llena sola.")
    st.stop()


def estado_cliente(row):
    if str(row.get("Resultado visita")) == "Compró":
        return "Compró", VERDE
    est = row.get("Estado agenda")
    if est == "Cumplida":
        return "Vino", CIAN
    if est == "No cumplida":
        return "No vino", ROJO
    return "Pendiente", MUT


# ---- clientes por día ----
por_dia = {}
for _, row in emb.iterrows():
    f = row.get("Fecha agenda visita")
    if f is None or (hasattr(f, "date") is False):
        continue
    try:
        d = f.date()
    except Exception:
        continue
    nombre = row.get("Nombre") or "—"
    txt, color = estado_cliente(row)
    por_dia.setdefault(d, []).append((str(nombre), txt, color))

total_general = sum(len(v) for v in por_dia.values())

vista = st.segmented_control("Vista", ["Semana", "Mes"], default="Semana", label_visibility="collapsed")


def chip(nombre, color):
    return (f"<div style='display:flex;align-items:center;gap:6px;font-size:12.5px;color:{TXT};padding:1px 0'>"
            f"<span style='width:8px;height:8px;border-radius:50%;background:{color};flex:none'></span>"
            f"{hsafe(nombre)}</div>")


def leyenda():
    items = [("Pendiente", MUT), ("Vino", CIAN), ("No vino", ROJO), ("Compró", VERDE)]
    chips = "".join(f"<span style='display:flex;align-items:center;gap:5px'>"
                    f"<span style='width:9px;height:9px;border-radius:50%;background:{c}'></span>{t}</span>"
                    for t, c in items)
    html(f"<div style='display:flex;flex-wrap:wrap;gap:16px;margin-top:12px;font-size:12px;color:{TXT2}'>{chips}</div>")


if vista == "Semana":
    off = st.session_state.get("ag_sem", 0)
    c1, c2, c3 = st.columns([1, 3, 1])
    if c1.button("◀ Anterior", key="sem_prev", use_container_width=True):
        off -= 1; st.session_state["ag_sem"] = off; st.rerun()
    if c3.button("Siguiente ▶", key="sem_next", use_container_width=True):
        off += 1; st.session_state["ag_sem"] = off; st.rerun()
    ref = datetime.date.today() + datetime.timedelta(weeks=off)
    lunes = ref - datetime.timedelta(days=ref.weekday())
    dias = [lunes + datetime.timedelta(days=i) for i in range(7)]
    total_sem = sum(len(por_dia.get(d, [])) for d in dias)
    c2.markdown(
        f"<div style='text-align:center;font-family:Montserrat,sans-serif;font-weight:700;font-size:15px'>"
        f"{dias[0].strftime('%d/%m')} – {dias[6].strftime('%d/%m')}</div>"
        f"<div style='text-align:center;color:{TXT2};font-size:12px'>{total_sem} clientes esta semana</div>",
        unsafe_allow_html=True)

    hoy = datetime.date.today()
    cols = st.columns(7)
    for d, col in zip(dias, cols):
        clientes = por_dia.get(d, [])
        es_hoy = d == hoy
        borde = f"2px solid {CIAN}" if es_hoy else f"1px solid {BORDE}"
        cuerpo = "".join(chip(n, c) for n, _, c in clientes) or f"<div style='color:{MUT};font-size:12px'>—</div>"
        with col:
            html(f"<div style='background:#FFFFFF;border:{borde};border-radius:12px;padding:10px;min-height:120px'>"
                 f"<div style='display:flex;justify-content:space-between;align-items:baseline;"
                 f"border-bottom:1px solid {BORDE};padding-bottom:6px;margin-bottom:8px'>"
                 f"<span style='font-weight:700;font-size:13px;font-family:Montserrat,sans-serif'>{DIAS[d.weekday()]} {d.day}</span>"
                 f"<span style='background:#E6F7FB;color:#008BA3;font-size:12px;font-weight:700;padding:1px 8px;border-radius:20px'>{len(clientes)}</span>"
                 f"</div><div style='display:flex;flex-direction:column;gap:2px'>{cuerpo}</div></div>")
    leyenda()

else:  # Mes
    off = st.session_state.get("ag_mes", 0)
    c1, c2, c3 = st.columns([1, 3, 1])
    if c1.button("◀ Anterior", key="mes_prev", use_container_width=True):
        off -= 1; st.session_state["ag_mes"] = off; st.rerun()
    if c3.button("Siguiente ▶", key="mes_next", use_container_width=True):
        off += 1; st.session_state["ag_mes"] = off; st.rerun()
    base = datetime.date.today().replace(day=1)
    y, m = base.year, base.month
    m += off
    while m > 12: m -= 12; y += 1
    while m < 1: m += 12; y -= 1
    total_mes = sum(len(v) for k, v in por_dia.items() if k.year == y and k.month == m)
    c2.markdown(
        f"<div style='text-align:center;font-family:Montserrat,sans-serif;font-weight:700;font-size:15px'>"
        f"{MESES[m].capitalize()} {y}</div>"
        f"<div style='text-align:center;color:{TXT2};font-size:12px'>{total_mes} clientes este mes</div>",
        unsafe_allow_html=True)

    hoy = datetime.date.today()
    encabez = "".join(f"<div style='text-align:center;font-size:11px;font-weight:700;color:{TXT2};"
                      f"font-family:Montserrat,sans-serif'>{d}</div>" for d in DIAS)
    celdas = ""
    for semana in calendar.Calendar(firstweekday=0).monthdayscalendar(y, m):
        for dnum in semana:
            if dnum == 0:
                celdas += "<div></div>"
                continue
            d = datetime.date(y, m, dnum)
            n = len(por_dia.get(d, []))
            es_hoy = d == hoy
            borde = f"2px solid {CIAN}" if es_hoy else f"1px solid {BORDE}"
            badge = (f"<span style='background:#E6F7FB;color:#008BA3;font-size:11px;font-weight:700;"
                     f"padding:0 6px;border-radius:10px'>{n}</span>") if n else ""
            celdas += (f"<div style='background:#FFFFFF;border:{borde};border-radius:10px;padding:8px;min-height:62px'>"
                       f"<div style='display:flex;justify-content:space-between;align-items:center'>"
                       f"<span style='font-size:12px;color:{TXT}'>{dnum}</span>{badge}</div></div>")
    html(f"<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:4px'>{encabez}</div>"
         f"<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:6px'>{celdas}</div>")

    dias_con = sorted(k for k in por_dia if k.year == y and k.month == m)
    if dias_con:
        st.write("")
        sel = st.selectbox("Ver clientes de un día", dias_con,
                           format_func=lambda d: f"{DIAS[d.weekday()]} {d.day} de {MESES[m]} — {len(por_dia[d])} clientes")
        filas = "".join(chip(n, c) for n, _, c in por_dia.get(sel, []))
        html(f"<div style='{CARD}'>{filas}</div>")
    leyenda()
