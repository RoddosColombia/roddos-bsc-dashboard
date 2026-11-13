"""Cálculo del funnel (módulo puro: sin Mongo, sin Streamlit, sin red → se prueba con datos inventados).

Modelo (docs/investigacion/09-modelo-atribucion-funnel.md en CRM-RODDOS):
  - Persona = documento; si no hay, celular.
  - Una venta se une a la solicitud de esa persona creada hasta 1 día después de la venta
    (prefiere la aprobada y, entre varias, la más reciente).
  - Canal de una solicitud = el PRIMER toque medido en los 30 días antes de crearla (también se
    calcula el último). Si el mismo día hay varios, gana la evidencia más fuerte:
      A anuncio de Meta → WhatsApp (referral)    B Google Ads (gclid)
      C anuncio de Meta → landing (fbclid/utm)   D enlace con UTM (incluye los de WhatsApp)
      E landing sin campaña / código LP en WhatsApp
  - Sin toques: WhatsApp sin marca (escribió antes de la solicitud) → contacto iniciado por
    RODDOS (le escribimos primero) → visita al sitio sin campaña → sin origen.
  - Venta sin solicitud: el mismo criterio con la fecha de la venta y ventana de 60 días.
  - Fechas: nunca se estiman. Los meses van en hora de Colombia.
"""
import collections
import datetime as dt
from urllib.parse import urlparse

from funnel import canal_venta

UTC_A_CO = dt.timedelta(hours=-5)
VENTANA_SOLICITUD = dt.timedelta(days=30)
VENTANA_VENTA = dt.timedelta(days=60)
APROBADOS = {"APROBADA", "FORMALIZACION", "ENTREGADA"}
RANGOS = "ABCDE"

META_ANUNCIO_WA = "Meta → WhatsApp (anuncio)"
GOOGLE_ADS = "Google Ads"
META_LANDING = "Meta → landing"
LANDING_WA = "Landing → WhatsApp (LP)"
LANDING_SIN_CAMPANA = "Landing sin campaña"
OTRA_UTM = "Otra campaña (UTM)"
WA_SIN_MARCA = "WhatsApp sin marca"
CONTACTO_RODDOS = "Contacto iniciado por RODDOS"
SITIO = "Sitio sin campaña"
SIN_ORIGEN = "Sin origen"

WA_MEDIOS = {
    "alexandra": "WhatsApp · bot Alexandra",
    "flujo": "WhatsApp · flujo Mercately",
    "asesor": "WhatsApp · asesor",
    "plantilla": "WhatsApp · plantilla",
}
WA_ENLACE_OTRO = "WhatsApp · enlace sin tipo"
FUENTES_META = {"fb", "facebook", "ig", "instagram", "meta", "an", "audience_network", "messenger"}
FUENTES_GOOGLE = {"google", "adwords", "youtube"}
MEDIOS_PAGOS = {"cpc", "ppc", "paid", "paidsearch", "paid_search", "display", "video"}


def mes_co(t):
    """Mes (AAAA-MM) en hora de Colombia de un datetime en UTC (o de una fecha local)."""
    if isinstance(t, dt.datetime):
        return (t + UTC_A_CO).strftime("%Y-%m")
    return t.strftime("%Y-%m")


def inicio_dia_utc(fecha_local):
    """00:00 hora Colombia de una fecha local, expresado en UTC (sin zona, como lo entrega Mongo)."""
    return dt.datetime(fecha_local.year, fecha_local.month, fecha_local.day) + dt.timedelta(hours=5)


def _es_landing(ruta):
    return bool(ruta) and str(ruta).startswith("/moto-a-cuotas")


def _dominio(url):
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return "otro"
    host = host.removeprefix("www.").removeprefix("m.").removeprefix("l.").removeprefix("lm.")
    return host or "otro"


def toque_de_origen(atr, ts):
    """Un origen guardado por RODDOS-web (attribution o su firstTouch) → (ts, rango, canal, campaña),
    o None si no es una campaña medible (una visita al sitio sin campaña se trata aparte)."""
    if not atr:
        return None
    ts = atr.get("capturedAt") or ts
    fuente = (atr.get("utmSource") or "").strip().lower()
    medio = (atr.get("utmMedium") or "").strip().lower()
    campana = atr.get("utmCampaign") or ""
    if atr.get("gclid") or (fuente in FUENTES_GOOGLE and medio in MEDIOS_PAGOS):
        return ts, "B", GOOGLE_ADS, campana or "(sin utm_campaign)"
    if atr.get("fbclid") or fuente in FUENTES_META:
        return ts, "C", META_LANDING, atr.get("utmContent") or campana or "(sin utm_campaign)"
    if fuente == "whatsapp":
        return ts, "D", WA_MEDIOS.get(medio, WA_ENLACE_OTRO), campana or medio or "(sin medio)"
    if fuente:
        return ts, "D", OTRA_UTM, "/".join(x for x in (fuente, medio, campana) if x)
    if _es_landing(atr.get("landing")):
        return ts, "E", LANDING_SIN_CAMPANA, atr.get("landing")
    return None


def toques_solicitud(sol):
    atr = sol.get("atr") or {}
    toques = []
    for origen in (atr, atr.get("firstTouch")):
        t = toque_de_origen(origen, sol["creada"])
        if t and t not in toques:
            toques.append(t)
    return toques


def visita_sitio(sol):
    """Entrada al sitio sin campaña (solicitudes desde el 9-nov-2026): campaña = de dónde venía."""
    atr = sol.get("atr") or {}
    for origen in (atr.get("firstTouch"), atr):
        if origen and origen.get("landing") and not _es_landing(origen.get("landing")):
            ref = origen.get("referrer")
            return _dominio(ref) if ref else "directo"
    return None


def atribuir(cel, sol, hasta, wa, ventana):
    """→ (canal primer toque, canal último toque, campaña del primer toque)."""
    w = wa.get(cel) if cel else None
    w = w or {}
    candidatos = list(w.get("toques", [])) + (toques_solicitud(sol) if sol else [])
    # 5 min de margen solo para toques con campaña (el origen se guarda segundos después de crear).
    margen = dt.timedelta(minutes=5)
    en_ventana = [t for t in candidatos if hasta - ventana <= t[0] <= hasta + margen]
    if en_ventana:
        primero = min(en_ventana, key=lambda t: (t[0].date(), RANGOS.index(t[1]), t[0]))
        ultimo = max(en_ventana, key=lambda t: (t[0].date(), -RANGOS.index(t[1]), t[0]))
        return primero[2], ultimo[2], primero[3]
    # La conversación cuenta solo si empezó ANTES de la solicitud: el aviso automático
    # "Recibimos tu solicitud" llega segundos después y no es un contacto de RODDOS.
    if w.get("primer_entrante") and w["primer_entrante"] < hasta:
        return WA_SIN_MARCA, WA_SIN_MARCA, ""
    if w.get("primer_dir") == "out" and w.get("primer_mensaje") and w["primer_mensaje"] < hasta:
        return CONTACTO_RODDOS, CONTACTO_RODDOS, ""
    sitio = visita_sitio(sol) if sol else None
    if sitio:
        return SITIO, SITIO, sitio
    return SIN_ORIGEN, SIN_ORIGEN, ""


def unir_ventas(ventas, solicitudes):
    """→ {índice de venta: solicitud, …} y cómo se unió cada una ('documento' / 'celular')."""
    por_doc, por_cel = collections.defaultdict(list), collections.defaultdict(list)
    for s in solicitudes:
        if s.get("doc"):
            por_doc[s["doc"]].append(s)
        if s.get("cel"):
            por_cel[s["cel"]].append(s)
    unidas, via = {}, {}
    for i, v in enumerate(ventas):
        limite = inicio_dia_utc(v["fecha"]) + dt.timedelta(days=1)
        for clave, indice in (("doc", por_doc), ("cel", por_cel)):
            cands = [s for s in indice.get(v.get(clave), []) if s["creada"] <= limite] if v.get(clave) else []
            if cands:
                preferidas = [s for s in cands if s["estado"] in APROBADOS] or cands
                unidas[i] = max(preferidas, key=lambda s: s["creada"])
                via[i] = "documento" if clave == "doc" else "celular"
                break
    return unidas, via


def _filas(contador, campos):
    return [dict(zip(campos, k), **v) for k, v in sorted(contador.items())]


def calcular(ventas, solicitudes, wa, leads, inicio, generado_en=None):
    """Totales del funnel desde `inicio` (datetime UTC). Ver el docstring del módulo.

    ventas: [{fecha: date, doc, cel, canal_texto}]
    solicitudes: [{id, creada: datetime UTC, estado, doc, cel, atr: attribution}]
    wa: {celular: {toques: [(ts, rango, canal, campaña)], primer_entrante, primer_mensaje, primer_dir}}
    leads: [{primer: datetime UTC, cel, fuente, campana}]  (un lead = una persona nueva de WhatsApp)
    """
    unidas, via = unir_ventas(ventas, solicitudes)
    compradoras = {s["id"] for s in unidas.values()}
    sols = [s for s in solicitudes if s["creada"] >= inicio]

    cohortes = collections.defaultdict(collections.Counter)
    campanas = collections.defaultdict(collections.Counter)
    calidad = collections.defaultdict(collections.Counter)
    canal_de = {}
    for s in sols:
        primero, ultimo, campana = atribuir(s.get("cel"), s, s["creada"], wa, VENTANA_SOLICITUD)
        canal_de[s["id"]] = primero
        m = mes_co(s["creada"])
        aprobada, compro = s["estado"] in APROBADOS, s["id"] in compradoras
        for modelo, canal in (("primer", primero), ("ultimo", ultimo)):
            c = cohortes[(m, modelo, canal)]
            c["solicitudes"] += 1
            c["aprobados"] += aprobada
            c["compras"] += compro
        if campana:
            c = campanas[(m, primero, str(campana)[:120])]
            c["solicitudes"] += 1
            c["aprobados"] += aprobada
            c["compras"] += compro
        q = calidad[(m,)]
        q["solicitudes"] += 1
        q["sin_origen"] += primero == SIN_ORIGEN
        q["solo_sitio"] += primero == SITIO
        q["con_celular"] += bool(s.get("cel"))

    ventas_tabla = collections.defaultdict(collections.Counter)
    dudosos = 0
    for i, v in enumerate(ventas):
        if inicio_dia_utc(v["fecha"]) < inicio:
            continue
        declarado, dudoso = canal_venta.normalizar(v.get("canal_texto"))
        dudosos += dudoso
        s = unidas.get(i)
        if s is not None:
            medido = canal_de.get(s["id"]) or atribuir(s.get("cel"), s, s["creada"], wa, VENTANA_SOLICITUD)[0]
        else:
            medido = atribuir(v.get("cel"), None, inicio_dia_utc(v["fecha"]) + dt.timedelta(days=1),
                              wa, VENTANA_VENTA)[0]
        m = mes_co(v["fecha"])
        ventas_tabla[(m, medido, declarado, s is not None)]["ventas"] += 1
        q = calidad[(m,)]
        q["ventas"] += 1
        q["ventas_con_solicitud"] += s is not None
        q["ventas_por_documento"] += via.get(i) == "documento"
        q["ventas_con_documento"] += bool(v.get("doc"))

    celulares_con_solicitud = {s["cel"] for s in solicitudes if s.get("cel")}
    leads_tabla = collections.defaultdict(collections.Counter)
    for lead in leads:
        if lead["primer"] < inicio:
            continue
        c = leads_tabla[(mes_co(lead["primer"]), lead["fuente"], str(lead.get("campana") or "")[:120])]
        c["leads"] += 1
        c["con_telefono"] += bool(lead.get("cel"))
        c["con_solicitud"] += bool(lead.get("cel")) and lead["cel"] in celulares_con_solicitud

    return dict(
        version=1,
        generado_en=generado_en or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
        desde=inicio,
        cohortes=_filas(cohortes, ("mes", "modelo", "canal")),
        campanas=_filas(campanas, ("mes", "canal", "campana")),
        ventas=_filas(ventas_tabla, ("mes", "canal_medido", "canal_declarado", "con_solicitud")),
        leads=_filas(leads_tabla, ("mes", "fuente", "campana")),
        calidad=_filas(calidad, ("mes",)),
        avisos=dict(canal_venta_dudosos=dudosos),
    )
