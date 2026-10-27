"""Celda K2 del Inventario ('Actualizado: ...'). Caso real (27 oct 2026): el maestro guardado desde
un Excel en español quedaba 'Actualizado: 27/10/yyyy' y el tablero decía que no sabía la fecha."""
import datetime as dt

import pytest

import data_sources as ds
import fixtures_excel as fx
import formatos


@pytest.fixture
def hoy_27_oct(monkeypatch):
    monkeypatch.setattr(formatos, "hoy_colombia", lambda: dt.date(2026, 10, 27))


@pytest.mark.parametrize("valor, esperado", [
    ("Actualizado: 27/10/2026", dt.date(2026, 10, 27)),
    ("Actualizado: 27/10/yyyy", dt.date(2026, 10, 27)),     # Excel en español: el año queda literal
    ("Actualizado: 27/10/aaaa", dt.date(2026, 10, 27)),
    ("Actualizado: 27/10/YYYY", dt.date(2026, 10, 27)),
    ("Actualizado: 30/12/yyyy", dt.date(2025, 12, 30)),     # una fecha que aún no llega este año: año anterior
    (46322.0, dt.date(2026, 10, 27)),                       # número de serie de Excel
    (dt.datetime(2026, 10, 27, 8, 0), dt.date(2026, 10, 27)),
    ("Actualizado: 31/02/yyyy", None),
    ("Actualizado:", None),
    (None, None),
    (True, None),
    (5, None),
])
def test_k2(hoy_27_oct, valor, esperado):
    assert formatos.parse_actualizado(valor) == esperado


def test_inventario_con_k2_en_espanol_tiene_fecha(hoy_27_oct, datos_prueba, reemplazar):
    wb = fx.wb_inventario()
    wb["Dashboard"]["K2"] = "Actualizado: 27/10/yyyy"
    reemplazar("Inventario_2026.xlsx", wb)
    assert ds.leer_inventario()["hoy"]["actualizado_fecha"] == dt.date(2026, 10, 27)
