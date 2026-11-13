"""Ventas (RODDOTIZADO) desde Inventario 2026.xlsx, pestaña Facturación.

Toda fila con "Fecha venta" es una venta: cualquier valor de "Canal venta" significa que compró.
Se leen solo las columnas necesarias para el cruce; los nombres de clientes no se leen.
"""
import datetime
import io
import re

import openpyxl
from openpyxl.utils.datetime import from_excel

import formatos

HOJA = "Facturación"
COL_FECHA, COL_DOC, COL_CEL, COL_CANAL = "Fecha venta", "# Documento", "Celular", "Canal venta"


class ErrorInventario(Exception):
    pass


def solo_digitos(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r"\D", "", str(v or ""))


def documento(v):
    d = solo_digitos(v).lstrip("0")
    return d if len(d) >= 5 else None


def celular(v):
    """Celular colombiano de 10 dígitos (3xxxxxxxxx), con o sin 57 / +57 adelante."""
    d = solo_digitos(v)
    if d.startswith("57") and len(d) == 12:
        d = d[2:]
    return d if re.fullmatch(r"3\d{9}", d) else None


def fecha(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return from_excel(v).date()
        except (ValueError, OverflowError):
            return None
    f = formatos.parse_fecha_texto(v)
    return f.date() if f else None


def _normalizar_encabezado(v):
    return re.sub(r"\s+", " ", str(v or "")).strip().lower()


def leer_ventas(contenido):
    """contenido: bytes del .xlsx. Devuelve [{fecha: date, doc, cel, canal_texto}] (sin nombres)."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as e:  # archivo dañado o que no es Excel
        raise ErrorInventario(f"No se pudo abrir el Inventario: {e}") from e
    if HOJA not in wb.sheetnames:
        raise ErrorInventario(f"Al Inventario le falta la pestaña '{HOJA}'.")
    filas = wb[HOJA].iter_rows(values_only=True)
    encabezado = next(filas, None) or ()
    idx = {_normalizar_encabezado(v): i for i, v in enumerate(encabezado) if v is not None}
    faltan = [c for c in (COL_FECHA, COL_DOC, COL_CEL, COL_CANAL) if _normalizar_encabezado(c) not in idx]
    if faltan:
        raise ErrorInventario(f"En la pestaña '{HOJA}' faltan las columnas {faltan}.")
    i_f, i_d, i_c, i_k = (idx[_normalizar_encabezado(c)] for c in (COL_FECHA, COL_DOC, COL_CEL, COL_CANAL))

    ventas = []
    for fila in filas:
        def celda(i):
            return fila[i] if i < len(fila) else None
        f = fecha(celda(i_f))
        if not f:
            continue
        ventas.append(dict(fecha=f, doc=documento(celda(i_d)), cel=celular(celda(i_c)),
                           canal_texto=str(celda(i_k) or "").strip()))
    wb.close()
    return ventas


def hoy_colombia():
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).date()
