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
    ahora = ahora or datetime.datetime.now()
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
