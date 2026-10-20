"""Histórico mensual de indicadores ("fotos" del tablero).

Cada vez que se abre la página principal con datos cargados, se guarda una foto
de los indicadores del mes de trabajo. Hay UNA foto por mes: mientras el mes
está en curso se va actualizando, y la última que quede es el cierre de ese mes.
Así el tablero acumula historia aunque cada carga de Excel reemplace a la anterior.

Dónde se guarda (sección [historico] de .streamlit/secrets.toml):

    [historico]
    destino = "local"   # SQLite en data/historico.sqlite (por defecto)
    destino = "mongo"   # colección `historico` de la base configurada en [mongo]

Por defecto es "local": nunca se escribe en MongoDB a menos que se pida
explícitamente. Así se puede probar todo en el computador sin tocar la nube.
"""
import datetime
import json
import math
import os
import sqlite3

DIR_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RUTA_SQLITE = os.path.join(DIR_LOCAL, "historico.sqlite")

# Indicadores que se grafican en la página Histórico: clave, etiqueta, tipo, ¿más es mejor?
INDICADORES = [
    ("pagos_dinero", "Recaudo del mes", "dinero", True),
    ("ventas", "Ventas (motos)", "numero", True),
    ("activaciones", "Activaciones", "numero", True),
    ("ci_dinero", "Cuotas iniciales ($)", "dinero", True),
    ("vencidas_dinero", "Cartera vencida ($)", "dinero", False),
    ("mora_total", "Mora total ($)", "dinero", False),
    ("inventario_disponible", "Motos disponibles", "numero", None),
    ("leads", "Leads recibidos", "numero", True),
    ("pct_aprobacion", "% aprobación de crédito", "porcentaje", True),
]


# ---------------------------------------------------------------- almacenes

class AlmacenLocal:
    """SQLite en un archivo local. Gratis, sin red, ideal para desarrollo."""

    nombre = "local (SQLite)"

    def __init__(self, ruta=None):
        ruta = ruta or RUTA_SQLITE  # se lee al crear, así los tests pueden redirigirlo
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        self.ruta = ruta
        with self._con() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS fotos ("
                " periodo TEXT PRIMARY KEY, corte TEXT, guardado_en TEXT, datos TEXT)"
            )

    def _con(self):
        return sqlite3.connect(self.ruta)

    def obtener(self, periodo):
        with self._con() as con:
            fila = con.execute(
                "SELECT periodo, corte, guardado_en, datos FROM fotos WHERE periodo = ?", (periodo,)
            ).fetchone()
        return _fila_a_foto(fila) if fila else None

    def guardar(self, foto):
        with self._con() as con:
            con.execute(
                "INSERT OR REPLACE INTO fotos (periodo, corte, guardado_en, datos) VALUES (?, ?, ?, ?)",
                (foto["periodo"], foto["corte"], foto["guardado_en"], json.dumps(foto["datos"])),
            )

    def listar(self):
        with self._con() as con:
            filas = con.execute(
                "SELECT periodo, corte, guardado_en, datos FROM fotos ORDER BY periodo"
            ).fetchall()
        return [_fila_a_foto(f) for f in filas]


def _fila_a_foto(fila):
    periodo, corte, guardado_en, datos = fila
    return dict(periodo=periodo, corte=corte, guardado_en=guardado_en, datos=json.loads(datos))


class AlmacenMongo:
    """Colección `historico` en MongoDB. Un documento pequeño (~2 KB) por mes."""

    nombre = "MongoDB"

    def __init__(self, db):
        self.col = db.historico

    def obtener(self, periodo):
        doc = self.col.find_one({"_id": periodo})
        return _doc_a_foto(doc) if doc else None

    def guardar(self, foto):
        doc = dict(foto)
        doc["_id"] = doc.pop("periodo")
        self.col.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    def listar(self):
        return [_doc_a_foto(d) for d in self.col.find().sort("_id", 1)]


def _doc_a_foto(doc):
    doc = dict(doc)
    doc["periodo"] = doc.pop("_id")
    return doc


def almacen():
    """Devuelve el almacén configurado. Sin configuración → local (nunca Mongo por accidente)."""
    import streamlit as st

    try:
        destino = str(st.secrets["historico"]["destino"]).strip().lower()
    except Exception:
        destino = "local"
    if destino == "mongo":
        import data_sources as ds

        db = ds.db_respaldo()
        if db is None:
            raise RuntimeError(
                "[historico] destino = \"mongo\" pero la sección [mongo] de secrets.toml no está configurada."
            )
        return AlmacenMongo(db)
    return AlmacenLocal()


# ---------------------------------------------------------------- fotos

def _ahora():
    import formatos

    return formatos.ahora_colombia().replace(tzinfo=None)


def _numero(v):
    """Convierte a float apto para JSON (numpy, Decimal, etc.); None si no es un número válido."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def armar_foto(metricas, hoy_recaudo, hoy_inv, objetivos=None, ahora=None):
    """Arma la foto del mes a partir del diccionario M de metricas.construir_metricas()."""
    ahora = ahora or _ahora()
    datos = {clave: _numero(r.get("mes")) for clave, r in metricas.items()}
    datos["_metas"] = {k: _numero(v) for k, v in (objetivos or {}).items()}
    datos["_corte_inventario"] = str(hoy_inv) if hoy_inv else None
    return dict(
        periodo=hoy_recaudo.strftime("%Y-%m"),
        corte=str(hoy_recaudo),
        guardado_en=ahora.isoformat(timespec="seconds"),
        datos=datos,
    )


def registrar(alm, foto):
    """Guarda la foto si aporta algo nuevo. Devuelve True si escribió.

    - Si ya hay una foto de ese mes con un corte MÁS RECIENTE, no la pisa
      (alguien subió un Excel viejo por error).
    - Si los datos son idénticos a los guardados, no escribe (evita escrituras
      innecesarias cada vez que alguien abre el tablero).
    """
    previa = alm.obtener(foto["periodo"])
    if previa:
        if (previa.get("corte") or "") > (foto["corte"] or ""):
            return False
        if previa.get("datos") == foto["datos"] and previa.get("corte") == foto["corte"]:
            return False
    alm.guardar(foto)
    return True


# ---------------------------------------------------------------- fotos por fuente (formato actual)
#
# Cada indicador se guarda en el mes de SU archivo: si Recaudo está en septiembre e Inventario en
# octubre, el recaudo va a la foto de septiembre y las ventas a la de octubre. Dentro de cada foto:
#   datos["_cortes"]        {fuente: fecha de corte} de las fuentes tomadas EN VIVO en ese mes
#   datos["_reconstruidas"] claves que vienen de reconstruir.py (se reemplazan si llega el dato en vivo)
#   datos["_metas"]         meta de cada indicador ese mes

FUENTES = ("recaudo", "inventario", "embudo")
CLAVES_INVENTARIO = {"ventas", "facturacion", "ci_completas", "ci_parciales", "ci_dinero", "activaciones",
                     "dias_inventario", "inventario_bodega", "inventario_disponible"}
CLAVES_EMBUDO = {"leads", "formularios", "aprobados_rechazados", "pct_aprobacion", "agendas_totales",
                 "agendas_hoy", "agendas_cumplidas_ayer", "agendas_incumplidas", "agendas_compraron",
                 "pct_conversion_agenda"}


def fuente_de(clave):
    if clave in CLAVES_INVENTARIO:
        return "inventario"
    if clave in CLAVES_EMBUDO:
        return "embudo"
    return "recaudo"


def _normalizada(foto):
    """Lleva una foto del formato anterior (una sola fecha para todo) al formato por fuente."""
    datos = json.loads(json.dumps(foto.get("datos") or {}))
    if "_cortes" not in datos:
        if datos.pop("_reconstruida", False):
            datos["_cortes"] = {}
            datos["_reconstruidas"] = [k for k in datos if not k.startswith("_")]
        else:
            # Foto en vivo del formato anterior: Recaudo y Embudo se tomaron con la fecha de la foto.
            # El Inventario pudo venir de OTRO mes (se anotaba en "_corte_inventario"): si no coincide
            # con el mes de la foto, esas cifras no son de este mes y se descartan, para que la
            # reconstrucción ponga las correctas del resumen mensual.
            datos["_cortes"] = {"recaudo": foto.get("corte"), "embudo": foto.get("corte")}
            corte_inv = datos.get("_corte_inventario")
            if corte_inv and str(corte_inv)[:7] == foto.get("periodo"):
                datos["_cortes"]["inventario"] = corte_inv
            elif corte_inv:
                for k in list(datos):
                    if fuente_de(k) == "inventario":
                        datos.pop(k)
                for k in list(datos.get("_metas") or {}):
                    if fuente_de(k) == "inventario":
                        datos["_metas"].pop(k)
            else:
                datos["_cortes"]["inventario"] = foto.get("corte")
            datos["_reconstruidas"] = []
        datos.pop("_corte_inventario", None)
    datos.setdefault("_metas", {})
    datos.setdefault("_reconstruidas", [])
    return dict(foto, datos=datos)


def es_reconstruida(foto):
    """True si algún indicador del mes viene de la reconstrucción (se marca con * en pantalla)."""
    return bool(_normalizada(foto)["datos"].get("_reconstruidas"))


def _vacia(periodo, corte, ahora):
    return dict(periodo=periodo, corte=corte, guardado_en=ahora.isoformat(timespec="seconds"),
                datos={"_cortes": {}, "_reconstruidas": [], "_metas": {}})


def registrar_en_vivo(alm, metricas, cortes, objetivos=None, ahora=None):
    """Guarda los indicadores de cada fuente en la foto del mes de SU fecha de corte.

    metricas: el dict M de metricas.construir_metricas().
    cortes: {"recaudo": date, "inventario": date, "embudo": date o None}.
    Un archivo más viejo que el ya registrado para ese mes no pisa nada. Devuelve cuántas fotos escribió.
    """
    ahora = ahora or _ahora()
    escritas = 0
    for fuente, corte in cortes.items():
        if corte is None:
            continue
        periodo, corte_txt = corte.strftime("%Y-%m"), str(corte)
        previa = alm.obtener(periodo)
        foto = _normalizada(previa) if previa else _vacia(periodo, corte_txt, ahora)
        d = foto["datos"]
        if (d["_cortes"].get(fuente) or "") > corte_txt:
            continue  # ya hay un dato más reciente de esta fuente para ese mes
        antes = json.dumps(d, sort_keys=True)
        claves = [k for k in metricas if fuente_de(k) == fuente]
        for k in claves:
            d[k] = _numero(metricas[k].get("mes"))
        for k, v in (objetivos or {}).items():
            if fuente_de(k) == fuente:
                d["_metas"][k] = _numero(v)
        d["_cortes"][fuente] = corte_txt
        d["_reconstruidas"] = [k for k in d["_reconstruidas"] if k not in claves]
        if previa and json.dumps(d, sort_keys=True) == antes:
            continue
        foto["corte"] = max(c for c in d["_cortes"].values() if c)
        foto["guardado_en"] = ahora.isoformat(timespec="seconds")
        alm.guardar(foto)
        escritas += 1
    return escritas


def registrar_reconstruidas(alm, fotos):
    """Completa los meses con datos reconstruidos (reconstruir.py) SIN pisar nunca un dato en vivo:
    en cada mes solo se llenan los indicadores de las fuentes que no tienen foto en vivo.
    Devuelve cuántas fotos escribió."""
    escritas = 0
    for nueva in fotos:
        previa = alm.obtener(nueva["periodo"])
        foto = _normalizada(previa) if previa else _vacia(nueva["periodo"], nueva["corte"],
                                                         _ahora())
        d = foto["datos"]
        antes = json.dumps(d, sort_keys=True)
        en_vivo = set(d["_cortes"])
        for k, v in nueva["datos"].items():
            if k.startswith("_") or fuente_de(k) in en_vivo:
                continue
            d[k] = v
            if k not in d["_reconstruidas"]:
                d["_reconstruidas"].append(k)
        for k, v in (nueva["datos"].get("_metas") or {}).items():
            if fuente_de(k) not in en_vivo:
                d["_metas"][k] = v
        if previa and json.dumps(d, sort_keys=True) == antes:
            continue
        alm.guardar(foto)
        escritas += 1
    return escritas
