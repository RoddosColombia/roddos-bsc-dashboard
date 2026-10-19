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
    """Celda K2 del Inventario: 'Actualizado: 09/10/2026' (o una fecha de Excel) -> date."""
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(v or ""))
    if not m:
        return None
    dia, mes, anio = (int(x) for x in m.groups())
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
