import streamlit as st

import acceso
import metricas as mx
import data_sources as ds
import os

import frescura
import graficos
import historico
import objetivos as obj

from utils import (cop, estilo_roddos, encabezado, html, hsafe, kpi, hero, CARD, pedir_archivos,
                   cargar_o_detener, leer_seguro, mostrar_avisos, mostrar_frescura, sincronizar_sharepoint)

st.set_page_config(page_title="Vista de reunión — RODDOS BSC", layout="wide", page_icon="🗓️")
estilo_roddos()
encabezado("Vista de reunión")
sincronizar_sharepoint()

_faltan = ds.faltantes(ds.F_RECAUDO, ds.F_INVENTARIO)
if _faltan:
    pedir_archivos(_faltan)

COLOR_OK = "#00A344"
COLOR_ALERTA = "#E08600"
COLOR_CRIT = "#E5484D"
COLOR_NEUTRO = "#5B616E"

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


st.caption(
    "Para proyectar en pantalla y recorrer en 15 minutos. Un renglón por indicador, "
    "semáforo contra la meta del mes — no discute datos, discute desviaciones."
)

data = cargar_o_detener(mx.construir_metricas,
                        [os.path.basename(ds.F_RECAUDO), os.path.basename(ds.F_INVENTARIO)])
M = data["metricas"]
hoy_recaudo = data["hoy_recaudo"]
mostrar_frescura({k: v for k, v in {"Recaudo": hoy_recaudo, "Inventario": data["inv"]["hoy"].get("actualizado_fecha"),
                                     "Embudo": data.get("hoy_emb")}.items() if k != "Embudo" or v})
mostrar_avisos(data.get("avisos"))

recaudo = data["rec"]  # ya se leyó al construir las métricas
meta_pactada_recaudo = recaudo["dashboard"].get("meta_pactada")
# misma regla que la página principal: cada indicador con la meta del mes de su archivo
_metas = leer_seguro(obj.objetivos_del_mes, os.path.basename(ds.F_METAS), ds.leer_metas,
                     {"recaudo": hoy_recaudo, "inventario": data["hoy_inv"],
                      "embudo": obj.fecha_de_texto(M["leads"].get("corte"))},
                     meta_pactada_recaudo)
objetivos_mes, metas_por_fuente = _metas or (
    {"pagos_dinero": meta_pactada_recaudo} if meta_pactada_recaudo else {}, {})
metas = metas_por_fuente.get("inventario") or metas_por_fuente.get("recaudo")

if metas:
    sub = (f"Meta ventas {metas['ventas']:.0f} · aprobación {metas['pct_aprobacion']*100:.0f}% · "
           f"agendas {metas['pct_agendas']*100:.0f}% · tope mora {metas['pct_mora_tope']*100:.0f}%")
else:
    sub = "Sin Metas_RODDOS.xlsx cargado"
hero("Mes de trabajo · " + frescura.texto_mes_de_trabajo(
         {"Recaudo": hoy_recaudo, "Inventario": data["hoy_inv"], "Embudo": data.get("hoy_emb")}),
     "Este mes", sub=sub)

hoy_inv = data["hoy_inv"]


def meta_a_hoy(clave, objetivo):
    """Lo que se esperaría llevar HOY para ir al ritmo de la meta del mes (los rubros que se
    acumulan se prorratean con los días de SU archivo; los demás se comparan con la meta tal cual)."""
    if not objetivo:
        return None
    if clave not in obj.RUBROS_FLUJO_MENSUAL:
        return objetivo
    dia = obj.fecha_corte_rubro(clave, hoy_recaudo, hoy_inv).day
    return objetivo * dia / obj.dias_del_mes_rubro(clave, hoy_recaudo, hoy_inv)


def _grafico(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ============ 1. ¿Cómo vamos frente a la meta? ============
st.write("")
st.subheader("🎯 ¿Cómo vamos frente a la meta?")
MEDIDORES = [("pagos_dinero", "Recaudo", "dinero"), ("ventas", "Ventas", "numero"),
             ("ci_dinero", "Cuotas iniciales", "dinero"), ("activaciones", "Activaciones", "numero"),
             ("pct_aprobacion", "% aprobación", "porcentaje")]
medidores = [(c, t, tipo) for c, t, tipo in MEDIDORES if objetivos_mes.get(c) and M[c].get("mes") is not None]
if medidores:
    # filas de 3: con 5 en una sola fila cada medidor queda muy angosto y los números no caben
    for i in range(0, len(medidores), 3):
        fila = medidores[i:i + 3]
        for col, (clave, titulo, tipo) in zip(st.columns(3), fila):
            with col:
                _grafico(graficos.medidor(titulo, M[clave]["mes"], objetivos_mes[clave],
                                          meta_a_hoy(clave, objetivos_mes[clave]), tipo))
    st.caption("La barra es lo logrado en el mes; la **raya oscura**, lo esperado a hoy para cumplir la meta; "
               "el fondo gris llega hasta la meta del mes. Verde: al ritmo o por encima · ámbar: un poco por "
               "debajo · rojo: lejos del ritmo. Dinero en millones.")
else:
    st.caption("Sin metas cargadas para comparar — sube Metas_RODDOS.xlsx en 📤 Actualizar datos.")

# ============ 2. Embudo comercial · 3. Cartera e inventario ============
st.write("")
c_emb, c_car = st.columns([3, 2])
with c_emb:
    st.subheader("🧲 Embudo comercial del mes")
    leads = M["leads"].get("mes")
    if leads:
        decididos, pct = M["aprobados_rechazados"].get("mes"), M["pct_aprobacion"].get("mes")
        aprobados = round(decididos * pct) if decididos and pct is not None else None
        _grafico(graficos.embudo([
            ("Leads", leads), ("Formularios", M["formularios"].get("mes")), ("Aprobados", aprobados),
            ("Visitas agendadas", M["agendas_totales"].get("mes")), ("Compraron", M["agendas_compraron"].get("mes")),
        ]))
        st.caption("Cada barra muestra cuántos clientes llegaron a esa etapa y qué % pasó desde la anterior.")
    else:
        st.caption("Sin datos del Embudo comercial este mes.")
with c_car:
    st.subheader("💳 Cartera")
    vencidas_n = M["vencidas_num"].get("mes")
    kpi("Recaudo del mes", cop(M["pagos_dinero"].get("mes")),
        sub=f"{fmt_valor('pagos_num', M['pagos_num'].get('mes'), False)} pagos de cuotas")
    kpi("Cuotas vencidas", cop(M["vencidas_dinero"].get("mes")), valor_color=COLOR_CRIT if vencidas_n else "#1A1D23",
        sub=f"{fmt_valor('vencidas_num', vencidas_n, False)} cuotas sin pagar a la fecha")
    kpi("Mora total", cop(M["mora_total"].get("mes")), sub="créditos activos en mora")
    st.subheader("📦 Inventario")
    i1, i2 = st.columns(2)
    with i1:
        kpi("Motos disponibles", fmt_valor("inventario_disponible", M["inventario_disponible"].get("mes"), False))
    with i2:
        kpi("Días de inventario", fmt_valor("dias_inventario", M["dias_inventario"].get("mes"), False),
            sub="al ritmo de venta del mes")

# ============ 4. Tendencia de los últimos meses ============
st.write("")
st.subheader("📈 Tendencia de los últimos meses")
try:
    fotos = historico.almacen().listar()[-6:]
except Exception as e:
    fotos = []
    st.caption(f"No se pudo leer el histórico: {e}")
if len(fotos) >= 2:
    # etiquetas cortas ("May", "Jun*") para que quepan horizontales en columnas angostas
    periodos = [frescura.MESES[int(f["periodo"][5:])][:3].capitalize()
                + ("*" if historico.es_reconstruida(f) else "") for f in fotos]
    reconstruidos = [historico.es_reconstruida(f) for f in fotos]
    t1, t2, t3 = st.columns(3)
    for col, (clave, titulo, tipo) in zip((t1, t2, t3), (("pagos_dinero", "Recaudo", "dinero"),
                                                        ("ventas", "Ventas", "numero"),
                                                        ("leads", "Leads", "numero"))):
        with col:
            _grafico(graficos.tendencia(titulo, periodos, [f["datos"].get(clave) for f in fotos],
                                        [(f["datos"].get("_metas") or {}).get(clave) for f in fotos],
                                        reconstruidos, tipo))
    st.caption("Línea punteada: meta de cada mes. \\* Barras claras: meses reconstruidos desde los Excel. "
               "El detalle mes a mes está en 📈 Histórico.")
else:
    st.caption("La tendencia aparece cuando el histórico tenga al menos dos meses (ver 📈 Histórico).")

# ============ 5. Tesorería (solo directores) ============
st.write("")
st.subheader("💰 Tesorería")
es_director = acceso.formulario_director("La caja es solo para directores.")
if es_director and ds.faltantes(ds.F_TESORERIA):
    st.caption("Sin Flujo_Pagos_Deudas.xlsx cargado — súbelo en 📤 Actualizar datos para ver la caja.")
elif es_director and metas and (tes := leer_seguro(ds.leer_tesoreria, os.path.basename(ds.F_TESORERIA))):
    dash = tes["dashboard"]
    pago_auteco_mes = dash.get("pago_auteco_mes") or 0
    resultado_objetivo = (meta_pactada_recaudo or 0) + metas["ci_dinero"] - metas["gasto_fijo"] - pago_auteco_mes
    tc1, tc2 = st.columns([1, 2])
    with tc1:
        kpi("Caja disponible total", cop(dash["caja_disponible_total"]))
        kpi("Resultado objetivo del mes", cop(resultado_objetivo),
            chip_txt="en verde" if resultado_objetivo >= 0 else "en rojo",
            chip_color=COLOR_OK if resultado_objetivo >= 0 else COLOR_CRIT,
            sub="recaudo + CI − gasto fijo − Auteco")
    with tc2:
        _grafico(graficos.cascada_resultado(meta_pactada_recaudo, metas["ci_dinero"], metas["gasto_fijo"],
                                            pago_auteco_mes))
elif es_director and not metas:
    st.caption("Sin Metas_RODDOS.xlsx cargado — no se puede calcular el resultado objetivo del mes.")

# ============ 6. Detalle completo ============
st.write("")
with st.expander("📋 Ver todos los indicadores en detalle"):
    for nombre_etapa, claves in mx.ETAPAS:
        filas = (f"<div style='font-family:Montserrat,sans-serif;font-weight:700;font-size:16px;"
                 f"margin-bottom:6px'>{nombre_etapa}</div>")
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
            else:  # contra lo esperado A HOY, no contra la meta del mes completo
                txt, color = estado(val, meta_a_hoy(clave, objetivo), es_negativo_malo=(clave == "mora_total"))
            filas += (f"<div style='display:flex;justify-content:space-between;align-items:center;padding:9px 2px;"
                      f"border-top:1px solid #EEF0F3'>"
                      f"<span style='font-size:14px;color:#3A3F4A'>{hsafe(mx.RUBRO_LABEL[clave])}</span>"
                      f"<span style='display:flex;align-items:center;gap:10px'>"
                      f"<span style='font-size:14px;font-weight:700;color:#1A1D23'>"
                      f"{hsafe(fmt_valor(clave, val, es_dinero))}</span>"
                      f"<span style='font-size:11px;color:{color};min-width:74px;text-align:right'>● {txt}</span>"
                      f"</span></div>")
        if corte:
            filas += f"<div style='font-size:11px;color:#8A909C;margin-top:8px'>Corte: {corte}</div>"
        html(f"<div style='{CARD}margin-bottom:12px'>{filas}</div>")

st.divider()
st.caption("RRHH no aparece aquí — es un módulo privado, solo para directores (ver página RRHH).")
