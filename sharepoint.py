"""Lectura automática de los Excel desde SharePoint (Microsoft Graph, solo lectura).

El equipo diligencia los Excel en la carpeta de SharePoint y el tablero los toma solo:
cada cierto tiempo revisa si algún archivo cambió (por su eTag) y descarga únicamente
los que cambiaron. Cada archivo nuevo pasa por carga.procesar(): la misma validación y
prueba de lectura que la carga manual. Si un archivo trae errores, se rechaza, se sigue
mostrando la última versión buena y se avisa en el tablero.

Configuración en .streamlit/secrets.toml (sin esta sección, nada de esto se activa):

    [sharepoint]
    activo = true
    tenant_id = "..."            # Directory (tenant) ID
    client_id = "..."            # Application (client) ID
    client_secret = "..."        # el valor del secreto (¡nunca en el repositorio!)
    sitio = "roddossas.sharepoint.com:/sites/RODDOSSAS"
    carpeta = "RODDOS/8. DASHBOARD BSC RODDOS/1 Fuentes al día"
    intervalo_minutos = 10       # cada cuánto revisar si hay cambios
    espera_minutos = 5           # no tomar un archivo guardado hace menos de esto (puede estar a medio editar)

    # Opcional: archivos que viven en OTRA carpeta (ruta completa dentro de Documentos).
    # Claves: recaudo, inventario, conciliacion, tesoreria, rrhh, embudo, metas, cobranza.
    [sharepoint.archivos]
    inventario = "RODDOS/2. OPERACIONES/MOTOS/Inventario 2026.xlsx"

Permiso necesario en Microsoft Entra ID: Sites.Selected (aplicación) con rol "read" sobre el sitio.
"""
import datetime
import json
import os
import threading
import time
from urllib.parse import quote

import requests

import carga
import data_sources as ds

GRAPH = "https://graph.microsoft.com/v1.0"
TIMEOUT = 60

OK, RECHAZADO, EN_EDICION, NO_ENCONTRADO = "ok", "rechazado", "en_edicion", "no_encontrado"


class ErrorSharePoint(Exception):
    """Fallo de conexión o de permisos con SharePoint (no del contenido de los archivos)."""


# ---------------------------------------------------------------- cliente de Microsoft Graph

# Códigos AADSTS más comunes al iniciar sesión, explicados en simple.
# (La respuesta de Microsoft nunca incluye el secreto, así que mostrarla es seguro.)
CODIGOS_AADSTS = {
    "AADSTS700016": "el client_id no corresponde a ninguna aplicación de este tenant (¿copiaste el Id. de objeto, "
                    "o tenant_id y client_id están intercambiados?)",
    "AADSTS90002": "el tenant_id no existe (¿copiaste otro identificador?)",
    "AADSTS900023": "el tenant_id no tiene un formato válido (revisa espacios o comillas de más)",
    "AADSTS7000215": "el client_secret no es válido: debe ser el VALOR del secreto, no el 'Id. de secreto'",
    "AADSTS7000222": "el client_secret venció: crea uno nuevo en 'Certificados y secretos'",
    "AADSTS700024": "la hora del servidor no coincide con la de Microsoft; vuelve a intentar en unos minutos",
}


def _explicar_error_token(r):
    try:
        descripcion = (r.json().get("error_description") or "").splitlines()[0]
    except Exception:
        descripcion = ""
    codigo = next((c for c in CODIGOS_AADSTS if descripcion.startswith(c + ":")), None)
    if codigo:
        return f"Causa: {CODIGOS_AADSTS[codigo]}. [{codigo}]"
    if descripcion:
        return f"Microsoft dice: {descripcion[:220]}"
    return "Revisa tenant_id, client_id y client_secret (¿venció el secreto?)."


class ClienteGraph:
    def __init__(self, tenant_id, client_id, client_secret, sitio, carpeta, sesion=None):
        self.tenant_id, self.client_id, self.client_secret = tenant_id, client_id, client_secret
        self.sitio, self.carpeta = sitio, carpeta.strip("/")
        self.sesion = sesion or requests.Session()
        self._token, self._token_vence = None, 0.0
        self._site_id = None

    def _token_vigente(self):
        if self._token and time.time() < self._token_vence - 60:
            return self._token
        r = self.sesion.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data={"grant_type": "client_credentials", "client_id": self.client_id,
                  "client_secret": self.client_secret, "scope": "https://graph.microsoft.com/.default"},
            timeout=TIMEOUT)
        if r.status_code != 200:
            raise ErrorSharePoint(f"No se pudo iniciar sesión en Microsoft ({r.status_code}). "
                                  f"{_explicar_error_token(r)}")
        datos = r.json()
        self._token = datos["access_token"]
        self._token_vence = time.time() + int(datos.get("expires_in", 3600))
        return self._token

    def _get(self, url, stream=False):
        r = self.sesion.get(url, headers={"Authorization": f"Bearer {self._token_vigente()}"},
                            timeout=TIMEOUT, stream=stream)
        if r.status_code in (401, 403):
            raise ErrorSharePoint(f"SharePoint negó el acceso ({r.status_code}). Revisa que la aplicación "
                                  "tenga permiso de lectura sobre el sitio (Sites.Selected).")
        if r.status_code == 404:
            raise ErrorSharePoint(f"No se encontró en SharePoint: {url}. Revisa 'sitio' y 'carpeta'.")
        if r.status_code != 200:
            raise ErrorSharePoint(f"Error de SharePoint ({r.status_code}) en {url}.")
        return r

    def site_id(self):
        if self._site_id is None:
            self._site_id = self._get(f"{GRAPH}/sites/{self.sitio}").json()["id"]
        return self._site_id

    def listar(self):
        """Archivos de la carpeta: [{id, nombre, etag, modificado (datetime UTC), tamano}]."""
        ruta = quote(self.carpeta, safe="/")
        url = (f"{GRAPH}/sites/{self.site_id()}/drive/root:/{ruta}:/children"
               "?$select=id,name,eTag,lastModifiedDateTime,size,file&$top=200")
        items = []
        while url:
            datos = self._get(url).json()
            for it in datos.get("value", []):
                if "file" not in it:
                    continue  # subcarpetas
                items.append(dict(
                    id=it["id"], nombre=it["name"], etag=it.get("eTag"), tamano=it.get("size"),
                    modificado=datetime.datetime.fromisoformat(it["lastModifiedDateTime"].replace("Z", "+00:00")),
                ))
            url = datos.get("@odata.nextLink")
        return items

    def obtener(self, ruta):
        """Un archivo por su ruta dentro de Documentos (para los que viven en otra carpeta)."""
        it = self._get(f"{GRAPH}/sites/{self.site_id()}/drive/root:/{quote(ruta.strip('/'), safe='/')}"
                       "?$select=id,name,eTag,lastModifiedDateTime,size,file").json()
        return dict(id=it["id"], nombre=it["name"], etag=it.get("eTag"), tamano=it.get("size"),
                    modificado=datetime.datetime.fromisoformat(it["lastModifiedDateTime"].replace("Z", "+00:00")))

    def descargar(self, item_id):
        return self._get(f"{GRAPH}/sites/{self.site_id()}/drive/items/{item_id}/content").content


# ---------------------------------------------------------------- configuración

def config():
    """La sección [sharepoint] de los secrets, o None si no está configurada o activa."""
    import streamlit as st

    try:
        cfg = dict(st.secrets["sharepoint"])
    except Exception:
        return None
    if not cfg.get("activo", True):
        return None
    faltan = [k for k in ("tenant_id", "client_id", "client_secret", "sitio", "carpeta") if not cfg.get(k)]
    if faltan:
        return dict(_error=f"Falta(n) {faltan} en la sección [sharepoint] de los secrets.")
    return cfg


def crear_cliente(cfg):
    return ClienteGraph(cfg["tenant_id"], cfg["client_id"], cfg["client_secret"], cfg["sitio"], cfg["carpeta"])


# ---------------------------------------------------------------- estado de la sincronización

def _ruta_estado():
    # junto a los datos (data_raw/ no se sube a GitHub); se lee en el momento por si los tests la redirigen
    return os.path.join(os.path.dirname(ds.F_RECAUDO), ".sharepoint_estado.json")


def leer_estado():
    try:
        with open(_ruta_estado(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _guardar_estado(estado):
    os.makedirs(os.path.dirname(_ruta_estado()), exist_ok=True)
    with open(_ruta_estado(), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1, default=str)


def _normalizar(nombre):
    return nombre.lower().replace(" ", "").replace("_", "").replace("-", "")


def _buscar(items, fuente):
    buscados = {_normalizar(n) for n in [os.path.basename(fuente["archivo"])] + fuente.get("alias", [])}
    for it in items:
        if _normalizar(it["nombre"]) in buscados and not it["nombre"].startswith("~$"):
            return it
    return None


# ---------------------------------------------------------------- sincronización

def sincronizar(cliente, espera_minutos=5, forzar=False, ahora=None, rutas=None):
    """Revisa la carpeta y carga los archivos que cambiaron.

    - Sin cambios (mismo eTag que la última revisión): no descarga nada.
    - Guardado hace menos de `espera_minutos` (y sin `forzar`): se deja para la próxima, por si
      alguien lo está editando todavía.
    - Con cambios: lo descarga y lo pasa por carga.procesar(). Si se rechaza, el tablero sigue
      con la versión anterior y el estado guarda los errores para mostrarlos.

    rutas: {clave de la fuente: ruta del archivo} para los que viven en otra carpeta
    (p. ej. el inventario maestro de Operaciones). Mandan sobre lo que haya en la carpeta.

    Devuelve el estado completo: {nombre de la fuente: {...}, "_revisado_en": ..., "_error": ...}.
    Un fallo de conexión no tumba nada: queda en "_error" y los datos actuales siguen igual.
    """
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    estado = leer_estado()
    estado["_revisado_en"] = ahora.isoformat(timespec="seconds")
    try:
        items = cliente.listar()
    except Exception as e:
        estado["_error"] = str(e)
        _guardar_estado(estado)
        return estado
    estado.pop("_error", None)
    rutas = rutas or {}

    for fuente in carga.fuentes():
        nombre = fuente["nombre"]
        previo = estado.get(nombre, {})
        ruta_propia = rutas.get(fuente["clave"])
        if ruta_propia:
            try:
                item = cliente.obtener(ruta_propia)
            except Exception as e:
                estado[nombre] = dict(previo, resultado=NO_ENCONTRADO, ruta=ruta_propia,
                                      errores=[f"No se encontró {ruta_propia}: {e}"])
                continue
        else:
            item = _buscar(items, fuente)
        if item is None:
            estado[nombre] = dict(previo, resultado=NO_ENCONTRADO)
            continue
        local_existe = os.path.exists(fuente["archivo"])
        sin_cambios = previo.get("etag") == item["etag"] and previo.get("resultado") in (OK, RECHAZADO)
        if sin_cambios and (local_existe or previo.get("resultado") == RECHAZADO):
            continue
        reciente = ahora - item["modificado"] < datetime.timedelta(minutes=espera_minutos)
        if reciente and not forzar:
            estado[nombre] = dict(previo, resultado=EN_EDICION, archivo_sharepoint=item["nombre"],
                                  modificado=item["modificado"].isoformat())
            continue
        try:
            r = carga.procesar(fuente, cliente.descargar(item["id"]))
        except Exception as e:
            estado["_error"] = f"No se pudo descargar {item['nombre']}: {e}"
            continue
        estado[nombre] = dict(
            etag=item["etag"], archivo_sharepoint=ruta_propia or item["nombre"], modificado=item["modificado"].isoformat(),
            revisado_en=ahora.isoformat(timespec="seconds"),
            resultado=OK if r["ok"] else RECHAZADO, errores=r["errores"][:20], aviso=r["aviso"],
        )
    _guardar_estado(estado)
    return estado


_candado = threading.Lock()
_ultima_revision = {"t": 0.0}


def sincronizar_si_toca(forzar=False):
    """Para las páginas: sincroniza como máximo cada `intervalo_minutos` (o ya, con forzar).
    Sin configuración devuelve None y no hace nada. Nunca lanza excepciones."""
    cfg = config()
    if cfg is None:
        return None
    if "_error" in cfg:
        return dict(_error=cfg["_error"])
    intervalo = float(cfg.get("intervalo_minutos", 10)) * 60
    if not forzar and time.time() - _ultima_revision["t"] < intervalo:
        return leer_estado()
    if not _candado.acquire(blocking=False):
        return leer_estado()  # otra sesión está sincronizando en este momento
    try:
        _ultima_revision["t"] = time.time()
        return sincronizar(crear_cliente(cfg), espera_minutos=float(cfg.get("espera_minutos", 5)), forzar=forzar,
                           rutas=dict(cfg.get("archivos") or {}))
    except Exception as e:
        return dict(leer_estado(), _error=str(e))
    finally:
        _candado.release()


def rechazados(estado):
    """[(fuente, archivo en SharePoint, errores)] de los archivos que SharePoint trae con errores."""
    return [(k, v.get("archivo_sharepoint"), v.get("errores", [])) for k, v in (estado or {}).items()
            if not k.startswith("_") and isinstance(v, dict) and v.get("resultado") == RECHAZADO]
