"""Interpretación de valores "humanos" de los Excel (fechas escritas como texto,
casillas Sí/No). Módulo puro, sin Streamlit: lo usan data_sources.py (para leer)
y validators.py (para validar), así ambos entienden exactamente lo mismo.
"""
import datetime
import re

MESES_ABR = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
             7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}
MESES_ABR_INV = {v: k for k, v in MESES_ABR.items()}

VALORES_SI = {"si", "sí", "x", "pagada", "pagado", "true", "verdadero"}
VALORES_NO = {"no", "pendiente", "false", "falso", ""}


def parse_fecha_corte(txt):
    """'Último registro: 21 sep 2026  ·  AL DÍA' -> date(2026, 9, 21). None si no se entiende."""
    if isinstance(txt, datetime.datetime):
        return txt.date()
    if isinstance(txt, datetime.date):
        return txt
    m = re.search(r"(\d{1,2})\s+([a-zA-Zé]{3})[a-zA-Zé]*\.?\s+(\d{4})", str(txt or ""))
    if not m:
        return None
    dia, mes_abr, anio = m.groups()
    mes = MESES_ABR_INV.get(mes_abr.lower().replace("é", "e"))
    if not mes:
        return None
    try:
        return datetime.date(int(anio), mes, int(dia))
    except ValueError:
        return None


def parse_actualizado(v):
    """Celda K2 del Inventario -> date. Acepta:
      - 'Actualizado: 09/10/2026' (texto) o una fecha de Excel;
      - 'Actualizado: 27/10/yyyy': la fórmula =TEXT(TODAY(),"dd/mm/yyyy") guardada desde un Excel
        en ESPAÑOL, que no entiende 'yyyy' (allá el año es 'aaaa') y lo deja como texto. Caso real
        (27 oct 2026). Se toma el año actual, o el anterior si esa fecha todavía no ha llegado;
      - el número de serie de Excel (si la celda tiene un formato de fecha que no se reconoce)."""
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if 20000 < v < 80000:  # número de serie de Excel (entre 1954 y 2119)
            return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))
        return None
    txt = str(v or "")
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", txt)
    if m:
        dia, mes, anio = (int(x) for x in m.groups())
    else:
        m = re.search(r"(\d{1,2})/(\d{1,2})/(?:yyyy|aaaa)\b", txt, re.IGNORECASE)
        if not m:
            return None
        dia, mes = (int(x) for x in m.groups())
        hoy = hoy_colombia()
        anio = hoy.year if (mes, dia) <= (hoy.month, hoy.day) else hoy.year - 1
    try:
        return datetime.date(anio, mes, dia)
    except ValueError:
        return None


def es_si(v):
    """Casilla 'Pagada': True, 1, 'Sí', 'si', 'X'... cuentan como pagada."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v == 1
    return isinstance(v, str) and v.strip().lower() in VALORES_SI


def valor_si_no_valido(v):
    if v is None or isinstance(v, bool) or (isinstance(v, (int, float)) and v in (0, 1)):
        return True
    return isinstance(v, str) and v.strip().lower() in VALORES_SI | VALORES_NO


def parse_fecha_texto(v):
    """Fecha de Excel, o texto escrito a mano en formato colombiano: 27/07/2026, 27-07-2026,
    27.07.2026 (día primero) o 2026-07-27. Devuelve datetime, o None si no se entiende.
    Importante: '05/09/2026' es 5 de septiembre, no 9 de mayo."""
    if isinstance(v, datetime.datetime):
        return v
    if isinstance(v, datetime.date):
        return datetime.datetime(v.year, v.month, v.day)
    if not isinstance(v, str):
        return None
    txt = v.strip()
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", txt)
    if m:
        dia, mes, anio = (int(x) for x in m.groups())
    else:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", txt)
        if not m:
            return None
        anio, mes, dia = (int(x) for x in m.groups())
    try:
        return datetime.datetime(anio, mes, dia)
    except ValueError:
        return None


# Columnas del embudo que hacen que una fila "tenga datos". Una fila que solo trae la
# 'Fecha lead' (por ejemplo, fechas pre-llenadas hacia abajo) es una fila vacía.
EMBUDO_COLS_CON_DATOS = ["Nombre", "Canal", "Telefono", "Decision", "Fecha formulario", "Fecha decision",
                         "Fecha agenda visita", "Estado agenda", "Resultado visita", "Motivo rechazo"]


def fila_embudo_vacia(d):
    return all(d.get(c) in (None, "") for c in EMBUDO_COLS_CON_DATOS)


def fila_encabezado(ws, columna, max_fila=10, por_defecto=4):
    """Número de la fila donde está el encabezado `columna` (busca en las primeras filas)."""
    for r in range(1, max_fila + 1):
        for c in ws[r]:
            if isinstance(c.value, str) and c.value.strip() == columna:
                return r
    return por_defecto


# ---------------------------------------------------------------- hora de Colombia
# Los servidores (Streamlit Cloud) corren en UTC: desde las 7 p. m. de Colombia, date.today() ya
# devuelve el día siguiente. Todo el tablero debe usar ESTAS funciones para "hoy" y "ahora".
# Colombia no tiene horario de verano: UTC-5 fijo (no hace falta la base de zonas horarias).
ZONA_COLOMBIA = datetime.timezone(datetime.timedelta(hours=-5), "COT")


def ahora_colombia():
    return datetime.datetime.now(ZONA_COLOMBIA)


def hoy_colombia():
    return ahora_colombia().date()


def a_hora_colombia(momento):
    """Un datetime (con zona, o UTC si viene sin zona como los de Mongo) a la hora de Colombia."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=datetime.timezone.utc)
    return momento.astimezone(ZONA_COLOMBIA)
