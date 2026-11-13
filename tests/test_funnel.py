"""Funnel de marketing: conversión de "Canal venta", lectura de Facturación, reglas de atribución,
almacenamiento y la página. Todo con datos inventados (ningún test toca bases ni SharePoint)."""
import datetime as dt
import io
import json
import os

import mongomock
import openpyxl
import pytest
from streamlit.testing.v1 import AppTest

from funnel import almacen, calculo, canal_venta, inventario
from funnel.calculo import calcular

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INICIO = dt.datetime(2026, 8, 1, 5)
T = dt.datetime(2026, 9, 10, 15)  # una solicitud cualquiera (UTC)


# ---------------------------------------------------------------- Canal venta

@pytest.mark.parametrize("texto, esperado", [
    ("REFERIDO/ERIKA", canal_venta.REFERIDO),
    ("Referida/Naireth Reyes", canal_venta.REFERIDO),
    ("REFERIDO SIN ID", canal_venta.VOZ_A_VOZ),
    ("VOZ A VOZ", canal_venta.VOZ_A_VOZ),
    ("VOZ", canal_venta.VOZ_A_VOZ),
    ("PAUTA", canal_venta.PAUTA_SIN_IDENTIFICAR),
    ("PAUTA/FACEBOOK", canal_venta.PAUTA_META),
    ("pauta / google", canal_venta.PAUTA_GOOGLE),
    ("VOLANTEO", canal_venta.CALLE),
    ("RODDOTIZADO", canal_venta.CLIENTE_RODDOS),
    ("SOLICITANTE ANTIGUO CREDITO", canal_venta.CLIENTE_RODDOS),
    ("ORGANICO", canal_venta.REDES_ORGANICAS),
    ("MERCATELY", canal_venta.NO_RECUERDA),
    ("EMPLEADO", canal_venta.REFERIDO),
    ("", canal_venta.VACIO),
    (None, canal_venta.VACIO),
    # los valores de la lista desplegable nueva se reconocen tal cual
    ("PAUTA META", canal_venta.PAUTA_META),
    ("REDES ORGÁNICAS", canal_venta.REDES_ORGANICAS),
    ("CLIENTE RODDOS", canal_venta.CLIENTE_RODDOS),
    ("NO RECUERDA", canal_venta.NO_RECUERDA),
])
def test_canal_venta_se_normaliza(texto, esperado):
    assert canal_venta.normalizar(texto)[0] == esperado


def test_canal_venta_marca_los_dudosos():
    assert canal_venta.normalizar("INSTAGRAM") == (canal_venta.REDES_ORGANICAS, True)
    assert canal_venta.normalizar("algo raro")[1] is True
    assert canal_venta.normalizar("PAUTA")[1] is False


def test_la_lista_desplegable_tiene_10_opciones():
    assert len(canal_venta.OPCIONES) == 10
    assert all(canal_venta.normalizar(op) == (op, False) for op in canal_venta.OPCIONES)


# ---------------------------------------------------------------- Facturación

def _xlsx(filas, encabezado=("Fecha venta", "Cliente", "# Documento", "Celular", "Canal venta")):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Facturación"
    ws.append(list(encabezado))
    for f in filas:
        ws.append(list(f))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_facturacion_se_lee_sin_nombres():
    contenido = _xlsx([
        (dt.datetime(2026, 9, 3), "Ana Pérez", 1023456789, "+57 300 123 4567", "REFERIDO/JUAN"),
        ("28/09/2026", "Luis", "79.123.456", 573101234567, "PAUTA"),   # fecha escrita a mano (día/mes)
        (None, "Sin fecha", 111, 3001112233, "PAUTA"),                  # sin fecha: no es venta
        (dt.datetime(2026, 10, 1), "X", None, "12345", ""),
    ])
    v = inventario.leer_ventas(contenido)
    assert [x["fecha"] for x in v] == [dt.date(2026, 9, 3), dt.date(2026, 9, 28), dt.date(2026, 10, 1)]
    assert v[0]["doc"] == "1023456789" and v[0]["cel"] == "3001234567"
    assert v[1]["doc"] == "79123456" and v[1]["cel"] == "3101234567"
    assert v[2]["doc"] is None and v[2]["cel"] is None
    assert "Ana" not in json.dumps(v, default=str)


def test_facturacion_sin_columnas_avisa():
    with pytest.raises(inventario.ErrorInventario, match="Canal venta"):
        inventario.leer_ventas(_xlsx([], encabezado=("Fecha venta", "# Documento", "Celular")))


# ---------------------------------------------------------------- atribución

def sol(id_="s1", creada=T, estado="APROBADA", doc="111111", cel="3001112233", atr=None):
    return dict(id=id_, creada=creada, estado=estado, doc=doc, cel=cel, atr=atr or {})


def canal(s, wa=None):
    return calculo.atribuir(s.get("cel"), s, s["creada"], wa or {}, calculo.VENTANA_SOLICITUD)


def test_anuncio_de_meta_por_whatsapp():
    wa = {"3001112233": {"toques": [(T - dt.timedelta(days=3), "A", calculo.META_ANUNCIO_WA, "Raider · 1202")],
                         "primer_entrante": T - dt.timedelta(days=3)}}
    assert canal(sol(), wa) == (calculo.META_ANUNCIO_WA, calculo.META_ANUNCIO_WA, "Raider · 1202")


def test_toques_de_mas_de_30_dias_no_cuentan():
    wa = {"3001112233": {"toques": [(T - dt.timedelta(days=45), "A", calculo.META_ANUNCIO_WA, "x")],
                         "primer_entrante": T - dt.timedelta(days=45)}}
    assert canal(sol(), wa)[0] == calculo.WA_SIN_MARCA


def test_mismo_dia_gana_la_evidencia_mas_fuerte_y_el_ultimo_es_el_mas_reciente():
    wa = {"3001112233": {"toques": [(T - dt.timedelta(hours=2), "A", calculo.META_ANUNCIO_WA, "ad")]}}
    s = sol(atr={"utmSource": "whatsapp", "utmMedium": "alexandra", "capturedAt": T - dt.timedelta(minutes=5)})
    primero, ultimo, _ = canal(s, wa)
    assert primero == calculo.META_ANUNCIO_WA
    assert ultimo == calculo.META_ANUNCIO_WA  # mismo día: también gana la evidencia más fuerte
    wa["3001112233"]["toques"][0] = (T - dt.timedelta(days=5), "A", calculo.META_ANUNCIO_WA, "ad")
    assert canal(s, wa)[:2] == (calculo.META_ANUNCIO_WA, "WhatsApp · bot Alexandra")


@pytest.mark.parametrize("atr, esperado", [
    ({"gclid": "abc", "utmCampaign": "motos"}, calculo.GOOGLE_ADS),
    ({"utmSource": "google", "utmMedium": "cpc"}, calculo.GOOGLE_ADS),
    ({"fbclid": "x"}, calculo.META_LANDING),
    ({"utmSource": "fb", "utmCampaign": "120251747992840004"}, calculo.META_LANDING),
    ({"utmSource": "whatsapp", "utmMedium": "flujo"}, "WhatsApp · flujo Mercately"),
    ({"utmSource": "whatsapp", "utmMedium": "asesor"}, "WhatsApp · asesor"),
    ({"utmSource": "whatsapp", "utmMedium": "plantilla", "utmCampaign": "reactivacion-24h"}, "WhatsApp · plantilla"),
    ({"utmSource": "tiktok"}, calculo.OTRA_UTM),
    ({"landing": "/moto-a-cuotas"}, calculo.LANDING_SIN_CAMPANA),
])
def test_origen_guardado_en_la_solicitud(atr, esperado):
    assert canal(sol(atr=atr))[0] == esperado


def test_el_primer_toque_guardado_en_la_web_tambien_cuenta():
    s = sol(atr={"utmSource": "whatsapp", "utmMedium": "alexandra", "capturedAt": T,
                 "firstTouch": {"fbclid": "x", "utmCampaign": "c1", "capturedAt": T - dt.timedelta(days=2)}})
    assert canal(s)[:2] == (calculo.META_LANDING, "WhatsApp · bot Alexandra")


def test_aviso_recibimos_tu_solicitud_no_es_contacto_de_roddos():
    """Regresión: el aviso automático llega segundos DESPUÉS de crear la solicitud."""
    wa = {"3001112233": {"toques": [], "primer_mensaje": T + dt.timedelta(seconds=20), "primer_dir": "out"}}
    assert canal(sol(), wa)[0] == calculo.SIN_ORIGEN


def test_contacto_iniciado_por_roddos_y_whatsapp_sin_marca():
    antes = T - dt.timedelta(days=2)
    assert canal(sol(), {"3001112233": {"toques": [], "primer_mensaje": antes, "primer_dir": "out"}})[0] \
        == calculo.CONTACTO_RODDOS
    assert canal(sol(), {"3001112233": {"toques": [], "primer_entrante": antes, "primer_mensaje": antes,
                                        "primer_dir": "in"}})[0] == calculo.WA_SIN_MARCA


def test_visita_al_sitio_sin_campana_no_tapa_una_conversacion_de_whatsapp():
    s = sol(atr={"landing": "/solicitar", "referrer": "https://www.google.com/"})
    assert canal(s) == (calculo.SITIO, calculo.SITIO, "google.com")
    wa = {"3001112233": {"toques": [], "primer_entrante": T - dt.timedelta(days=1)}}
    assert canal(s, wa)[0] == calculo.WA_SIN_MARCA
    assert canal(sol(atr={"landing": "/"}))[2] == "directo"


# ---------------------------------------------------------------- totales

def test_calcular_une_ventas_por_documento_y_por_celular():
    sols = [
        sol("a", doc="111111", cel="3000000001", atr={"gclid": "g"}),
        sol("b", doc=None, cel="3000000002", atr={"fbclid": "f"}),
        sol("c", estado="RECHAZADA", doc="333333", cel="3000000003"),
        sol("d", estado="FORMALIZACION", doc="444444", cel="3000000004"),
        sol("viejo", creada=dt.datetime(2026, 6, 1), doc="555555", cel=None),
    ]
    ventas = [
        dict(fecha=dt.date(2026, 9, 12), doc="111111", cel=None, canal_texto="PAUTA/FACEBOOK"),
        dict(fecha=dt.date(2026, 9, 15), doc="999999", cel="3000000002", canal_texto="REFERIDO/PEPE"),
        dict(fecha=dt.date(2026, 9, 1), doc="444444", cel=None, canal_texto="PAUTA"),  # antes de la solicitud
    ]
    r = calcular(ventas, sols, {}, [], INICIO, generado_en=dt.datetime(2026, 9, 20))
    primer = {f["canal"]: f for f in r["cohortes"] if f["modelo"] == "primer"}
    assert primer[calculo.GOOGLE_ADS]["compras"] == 1
    assert primer[calculo.META_LANDING]["compras"] == 1
    assert primer[calculo.SIN_ORIGEN]["solicitudes"] == 2
    assert primer[calculo.SIN_ORIGEN]["aprobados"] == 1   # FORMALIZACION cuenta como aprobado
    assert primer[calculo.SIN_ORIGEN]["compras"] == 0     # la venta fue antes de esa solicitud
    assert sum(f["solicitudes"] for f in r["cohortes"] if f["modelo"] == "primer") == 4  # la de junio no entra
    sep = r["calidad"][0]
    assert (sep["ventas"], sep["ventas_con_solicitud"], sep["ventas_por_documento"]) == (3, 2, 1)
    declarados = {(f["canal_medido"], f["canal_declarado"]) for f in r["ventas"]}
    assert (calculo.GOOGLE_ADS, canal_venta.PAUTA_META) in declarados
    assert (calculo.META_LANDING, canal_venta.REFERIDO) in declarados


def test_venta_sin_solicitud_usa_whatsapp_de_los_60_dias_previos():
    wa = {"3009998877": {"toques": [(dt.datetime(2026, 8, 20), "A", calculo.META_ANUNCIO_WA, "ad")]}}
    ventas = [dict(fecha=dt.date(2026, 10, 1), doc="1", cel="3009998877", canal_texto="")]
    r = calcular(ventas, [], wa, [], INICIO)
    assert r["ventas"][0]["canal_medido"] == calculo.META_ANUNCIO_WA
    assert r["ventas"][0]["con_solicitud"] is False


def test_leads_y_su_paso_a_solicitud():
    leads = [dict(primer=T, cel="3001112233", fuente=calculo.META_ANUNCIO_WA, campana="ad 1"),
             dict(primer=T, cel=None, fuente="Instagram (mensaje directo)", campana=""),
             dict(primer=T, cel="3000000000", fuente=calculo.WA_SIN_MARCA, campana=""),
             dict(primer=dt.datetime(2026, 7, 1), cel="3000000009", fuente=calculo.WA_SIN_MARCA, campana="")]
    r = calcular([], [sol()], {}, leads, INICIO)
    por = {f["fuente"]: f for f in r["leads"]}
    assert por[calculo.META_ANUNCIO_WA]["con_solicitud"] == 1
    assert por["Instagram (mensaje directo)"]["con_telefono"] == 0
    assert sum(f["leads"] for f in r["leads"]) == 3  # el de julio no entra


def test_el_resumen_no_lleva_datos_personales():
    sols = [sol(doc="1023456789", cel="3157654321", atr={"utmSource": "whatsapp", "utmMedium": "asesor"})]
    ventas = [dict(fecha=dt.date(2026, 9, 12), doc="1023456789", cel="3157654321", canal_texto="REFERIDO/MARTA LOPEZ")]
    texto = json.dumps(calcular(ventas, sols, {}, [], INICIO), default=str)
    for dato in ("1023456789", "3157654321", "MARTA", "LOPEZ"):
        assert dato not in texto


# ---------------------------------------------------------------- almacén

def test_guardar_conserva_la_ejecucion_anterior():
    db = mongomock.MongoClient()["bsc_dashboard"]
    almacen.guardar(db, {"version": 1, "n": 1})
    almacen.guardar(db, {"version": 1, "n": 2})
    assert almacen.leer(db)["n"] == 2
    assert db[almacen.COLECCION].find_one({"_id": "anterior"})["n"] == 1
    assert almacen.leer(None) is None


# ---------------------------------------------------------------- página

def _abrir_marketing():
    return AppTest.from_file(os.path.join(RAIZ, "pages/6_Marketing.py"), default_timeout=60).run()


def test_pagina_sin_datos_explica_que_falta():
    at = _abrir_marketing()
    assert not at.exception
    assert any("Todavía no hay datos del funnel" in str(i.value) for i in at.info)


def test_pagina_con_datos(monkeypatch):
    sols = [sol("a", atr={"gclid": "g", "utmCampaign": "motos-bogota"}),
            sol("b", doc="2", cel="3002223344", estado="RECHAZADA")]
    ventas = [dict(fecha=dt.date(2026, 9, 12), doc="111111", cel=None, canal_texto="PAUTA")]
    leads = [dict(primer=T, cel="3001112233", fuente=calculo.META_ANUNCIO_WA, campana="Raider · 1202")]
    resumen = calcular(ventas, sols, {}, leads, INICIO, generado_en=dt.datetime(2026, 9, 20, 11))
    monkeypatch.setattr(almacen, "leer", lambda db: resumen)
    at = _abrir_marketing()
    assert not at.exception, [e.message for e in at.exception]
    textos = " ".join(str(s.value) for s in at.subheader)
    assert "¿Qué canal convierte en venta?" in textos and "Calidad del dato" in textos
    assert any("20/09/2026" in str(c.value) for c in at.caption)
