"""Lectura de las tres fuentes (SOLO LECTURA). Devuelve datos personales en memoria para el cruce;
nada de esto se guarda: funnel/almacen.py solo recibe los totales de funnel/calculo.py."""
import collections
import re
from urllib.parse import quote

import requests

from funnel import calculo
from funnel.inventario import celular, documento

GRAPH = "https://graph.microsoft.com/v1.0"
LP = re.compile(r"\((LP-[A-Z]+)\)")
FUENTE_CANAL = {"instagram": "Instagram (mensaje directo)", "messenger": "Messenger"}


# ---------------------------------------------------------------- RODDOS-web

def solicitudes(db):
    """Solicitudes de crédito con su origen y estado final. El documento y el celular salen de
    scoring_results (en creditapplications van cifrados)."""
    sols = {}
    for a in db.creditapplications.find({"deletedAt": {"$exists": False}},
                                        {"status": 1, "createdAt": 1, "attribution": 1}):
        sols[str(a["_id"])] = dict(id=str(a["_id"]), creada=a["createdAt"], estado=a.get("status"),
                                   atr=a.get("attribution") or {}, doc=None, cel=None)
    for r in db.scoring_results.find({}, {"application_id": 1, "numero_documento": 1, "numero_celular": 1,
                                          "kyc.numero_documento": 1, "kyc.numero_celular": 1}):
        s = sols.get(str(r.get("application_id")))
        if s:
            kyc = r.get("kyc") or {}
            s["doc"] = documento(r.get("numero_documento") or kyc.get("numero_documento"))
            s["cel"] = celular(r.get("numero_celular") or kyc.get("numero_celular"))
    return list(sols.values())


# ---------------------------------------------------------------- CRM-RODDOS

def _campana_anuncio(ref):
    titulo = re.sub(r"\s+", " ", (ref or {}).get("headline") or "").strip()[:70]
    ident = (ref or {}).get("source_id") or ""
    return " · ".join(x for x in (titulo, ident) if x) or "(anuncio sin datos)"


def whatsapp_por_celular(db, celulares):
    """Toques de WhatsApp de las personas que solicitaron o compraron (por celular)."""
    wa = {}
    telefonos = ["+57" + c for c in celulares]
    for i in range(0, len(telefonos), 2000):
        cursor = db.messages.aggregate([
            {"$match": {"channel": "whatsapp", "phone": {"$in": telefonos[i:i + 2000]}}},
            {"$project": {"phone": 1, "timestamp": 1, "direction": 1, "body": 1,
                          "ref": {"$ifNull": ["$referral", "$raw.referral"]}}},
            {"$sort": {"timestamp": 1}},
        ], allowDiskUse=True)
        for m in cursor:
            cel = celular(m.get("phone"))
            if not cel:
                continue
            w = wa.setdefault(cel, {"toques": []})
            ts = m["timestamp"]
            if m.get("direction") == "in":
                w.setdefault("primer_entrante", ts)
                if (m.get("ref") or {}).get("source_id"):
                    w["toques"].append((ts, "A", calculo.META_ANUNCIO_WA, _campana_anuncio(m["ref"])))
                lp = LP.search(m.get("body") or "")
                if lp:
                    w["toques"].append((ts, "E", calculo.LANDING_WA, lp.group(1)))
            w.setdefault("primer_mensaje", ts)
            w.setdefault("primer_dir", m.get("direction"))
    return wa


def leads(db, desde):
    """Personas nuevas que escribieron por WhatsApp, Instagram o Messenger desde `desde`.
    Persona = teléfono; sin teléfono (usernames de WhatsApp, Instagram, Messenger) = su contacto."""
    filas = db.messages.aggregate([
        {"$match": {"direction": "in"}},
        {"$sort": {"timestamp": 1}},
        {"$group": {
            "_id": {"$ifNull": ["$phone", {"$ifNull": ["$wa_user_id", "$contact_id"]}]},
            "primer": {"$first": "$timestamp"},
            "canal": {"$first": "$channel"},
            "texto": {"$first": "$body"},
            "ref": {"$max": {"$ifNull": ["$referral", "$raw.referral"]}},
            "telefono": {"$max": "$phone"},
        }},
        {"$match": {"primer": {"$gte": desde}}},
    ], allowDiskUse=True)
    salida = []
    for f in filas:
        ref = f.get("ref") or {}
        if f.get("canal") in FUENTE_CANAL:
            fuente, campana = FUENTE_CANAL[f["canal"]], ""
        elif ref.get("source_id"):
            fuente, campana = calculo.META_ANUNCIO_WA, _campana_anuncio(ref)
        elif LP.search(f.get("texto") or ""):
            fuente, campana = calculo.LANDING_WA, LP.search(f["texto"]).group(1)
        else:
            fuente, campana = calculo.WA_SIN_MARCA, ""
        salida.append(dict(primer=f["primer"], cel=celular(f.get("telefono")), fuente=fuente, campana=campana))
    return salida


# ---------------------------------------------------------------- SharePoint (Inventario 2026)

def descargar_sharepoint(tenant_id, client_id, client_secret, sitio, ruta, timeout=120):
    """Descarga un archivo de SharePoint por su ruta (Microsoft Graph, permiso de solo lectura)."""
    s = requests.Session()
    r = s.post(f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token", timeout=timeout,
               data={"grant_type": "client_credentials", "client_id": client_id,
                     "client_secret": client_secret, "scope": "https://graph.microsoft.com/.default"})
    if r.status_code != 200:
        raise RuntimeError(f"No se pudo iniciar sesión en Microsoft ({r.status_code}).")
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    site = s.get(f"{GRAPH}/sites/{sitio}", headers=h, timeout=timeout)
    site.raise_for_status()
    url = f"{GRAPH}/sites/{site.json()['id']}/drive/root:/{quote(ruta.strip('/'), safe='/')}:/content"
    arch = s.get(url, headers=h, timeout=timeout)
    if arch.status_code != 200:
        raise RuntimeError(f"No se pudo descargar '{ruta}' de SharePoint ({arch.status_code}).")
    return arch.content


def celulares_de_interes(ventas, sols):
    return {v["cel"] for v in ventas if v.get("cel")} | {s["cel"] for s in sols if s.get("cel")}


def resumen_fuentes(ventas, sols, wa, lds):
    """Conteos para el registro de la ejecución (sin datos personales)."""
    return dict(ventas=len(ventas), solicitudes=len(sols), personas_whatsapp=len(wa), leads=len(lds),
                leads_por_fuente=dict(collections.Counter(x["fuente"] for x in lds)))
