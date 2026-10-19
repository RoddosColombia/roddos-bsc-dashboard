import calendar
import datetime
import streamlit as st

from utils import estilo_roddos, encabezado, html, hsafe, CARD, CIAN, VERDE, ROJO, MUT, TXT, TXT2, BORDE, TRACK
import os

import data_sources as ds
from utils import leer_seguro

st.set_page_config(page_title="Agenda — RODDOS BSC", layout="wide", page_icon="🗓️")
estilo_roddos()
encabezado("Agenda de visitas")

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

emb = leer_seguro(ds.leer_embudo, os.path.basename(ds.F_EMBUDO))
if emb is None:
    st.stop()
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

vista = st.segmented_control("Vista", ["Semana", "Mes"], default="Semana", label_visibility="collapsed",
                             key="ag_vista")


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
    c1, c_hoy, c2, c3 = st.columns([1, 0.6, 2.4, 1])
    if c_hoy.button("Hoy", key="sem_hoy", use_container_width=True, disabled=off == 0,
                    help="Volver a la semana actual"):
        st.session_state["ag_sem"] = 0; st.rerun()
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
    c1, c_hoy, c2, c3 = st.columns([1, 0.6, 2.4, 1])
    if c_hoy.button("Hoy", key="mes_hoy", use_container_width=True, disabled=off == 0,
                    help="Volver al mes actual"):
        st.session_state["ag_mes"] = 0; st.session_state["ag_dia_sel"] = datetime.date.today(); st.rerun()
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
    dias_con = sorted(k for k in por_dia if k.year == y and k.month == m)

    # Día seleccionado: se conserva mientras siga en el mes que se está viendo.
    # Si no, se elige hoy (si está en este mes) o el primer día con visitas.
    sel = st.session_state.get("ag_dia_sel")
    if not (isinstance(sel, datetime.date) and (sel.year, sel.month) == (y, m)):
        sel = hoy if (hoy.year, hoy.month) == (y, m) else (dias_con[0] if dias_con else None)
        st.session_state["ag_dia_sel"] = sel

    # Cada día se dibuja en HTML (para poder mostrar un punto de color por cliente según su
    # estado) y encima lleva un botón invisible del mismo tamaño que recibe el clic:
    # el HTML por sí solo no puede avisarle a Streamlit que lo pulsaron.
    html("<style>"
         ".st-key-ag_cal [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:6px !important}"
         ".st-key-ag_cal [data-testid='stColumn']{min-width:0 !important;width:auto !important;"
         "flex:1 1 0 !important;position:relative}"
         ".st-key-ag_cal [class*='st-key-agdia_']{position:absolute !important;inset:0;margin:0 !important;z-index:2}"
         ".st-key-ag_cal [class*='st-key-agdia_'] button{width:100%;height:100%;min-height:0;opacity:0;cursor:pointer}"
         f".st-key-ag_cal [data-testid='stColumn']:hover .ag-celda{{border-color:{CIAN} !important}}"
         "</style>")

    def celda(d):
        clientes = por_dia.get(d, [])
        es_sel, es_hoy = d == sel, d == hoy
        borde = f"2px solid {CIAN}" if (es_hoy or es_sel) else f"1px solid {BORDE}"
        fondo = "#E6F7FB" if es_sel else "#FFFFFF"
        badge = (f"<span style='background:#E6F7FB;color:#008BA3;font-size:11px;font-weight:700;"
                 f"padding:0 6px;border-radius:10px'>{len(clientes)}</span>") if clientes else ""
        puntos = "".join(f"<span title='{hsafe(n)} · {hsafe(t)}' style='width:8px;height:8px;border-radius:50%;"
                         f"background:{c};display:inline-block'></span>" for n, t, c in clientes[:10])
        if len(clientes) > 10:
            puntos += f"<span style='font-size:10px;color:{TXT2}'>+{len(clientes) - 10}</span>"
        return (f"<div class='ag-celda' style='background:{fondo};border:{borde};border-radius:10px;padding:8px;"
                f"min-height:62px;box-sizing:border-box'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<span style='font-size:12px;color:{TXT};font-weight:{700 if es_sel else 400}'>{d.day}</span>{badge}</div>"
                f"<div style='display:flex;flex-wrap:wrap;gap:3px;margin-top:6px'>{puntos}</div></div>")

    with st.container(key="ag_cal"):
        for col, nombre_dia in zip(st.columns(7), DIAS):
            col.markdown(f"<div style='text-align:center;font-size:11px;font-weight:700;color:{TXT2};"
                         f"font-family:Montserrat,sans-serif'>{nombre_dia}</div>", unsafe_allow_html=True)
        for semana in calendar.Calendar(firstweekday=0).monthdayscalendar(y, m):
            for dnum, col in zip(semana, st.columns(7)):
                if dnum == 0:
                    continue
                d = datetime.date(y, m, dnum)
                with col:
                    html(celda(d))
                    if st.button(f"Ver {d.day}", key=f"agdia_{d:%Y%m%d}", use_container_width=True):
                        st.session_state["ag_dia_sel"] = d
                        st.rerun()

    # ---- consolidado: lista desplegable de los días con visitas (sincronizada con el clic) ----
    def _elegir_de_lista():
        st.session_state["ag_dia_sel"] = st.session_state["ag_dia_lista"]

    if dias_con:
        st.write("")
        st.session_state["ag_dia_lista"] = sel if sel in dias_con else None
        st.selectbox("Ver clientes de un día", dias_con, key="ag_dia_lista", on_change=_elegir_de_lista,
                     placeholder="Elige un día con visitas",
                     format_func=lambda d: f"{DIAS[d.weekday()]} {d.day} de {MESES[m]} — {len(por_dia[d])} clientes")

    # ---- detalle del día elegido ----
    if sel is None:
        st.caption("Este mes no tiene visitas agendadas. Usa ◀ ▶ para ver otros meses.")
    else:
        clientes = por_dia.get(sel, [])
        titulo = f"{DIAS[sel.weekday()]} {sel.day} de {MESES[sel.month]}" + (" · hoy" if sel == hoy else "")
        if clientes:
            filas = "".join(
                f"<div style='display:flex;justify-content:space-between;align-items:center;gap:12px;"
                f"padding:6px 0;border-bottom:1px solid {BORDE}'>{chip(n, c)}"
                f"<span style='font-size:12px;font-weight:600;color:{c}'>{hsafe(t)}</span></div>"
                for n, t, c in clientes)
            resumen = f"{len(clientes)} cliente(s)"
        else:
            filas = f"<div style='color:{MUT};font-size:13px'>Sin visitas agendadas este día.</div>"
            resumen = "0 clientes"
        html(f"<div style='{CARD}'>"
             f"<div style='display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px'>"
             f"<span style='font-family:Montserrat,sans-serif;font-weight:700;font-size:15px'>{titulo}</span>"
             f"<span style='color:{TXT2};font-size:12px'>{resumen}</span></div>{filas}</div>")
    leyenda()