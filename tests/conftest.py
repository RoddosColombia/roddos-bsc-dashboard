"""Configuración común de los tests.

Regla: ningún test lee ni escribe los datos reales del proyecto (data_raw/, data/).
El fixture automático `_aislar` redirige TODAS las rutas de archivos a una carpeta
temporal vacía; `datos_prueba` la llena con los Excel inventados de fixtures_excel.py.
"""
import os
import sys

import pytest
import streamlit as st

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

import data_sources as ds  # noqa: E402
import fixtures_excel  # noqa: E402
import historico  # noqa: E402

RUTAS = {
    "F_RECAUDO": "Proyeccion_Recaudo.xlsx",
    "F_INVENTARIO": "Inventario_2026.xlsx",
    "F_CONCILIACION": "Cruce_SISMO_Wava.xlsx",
    "F_TESORERIA": "Flujo_Pagos_Deudas.xlsx",
    "F_RRHH": "Control_RRHH_Nomina_RODDOS_2026.xlsx",
    "F_EMBUDO": "Embudo_Comercial_RODDOS.xlsx",
    "F_METAS": "Metas_RODDOS.xlsx",
    "F_COBRANZA": "Cobranza_Semanal.xlsx",
}


@pytest.fixture(autouse=True)
def _aislar(tmp_path, monkeypatch):
    raw = tmp_path / "data_raw"
    raw.mkdir()
    for attr, nombre in RUTAS.items():
        monkeypatch.setattr(ds, attr, str(raw / nombre))
    monkeypatch.setattr(ds, "ARCHIVOS", [str(raw / n) for n in RUTAS.values()])
    monkeypatch.setattr(historico, "RUTA_SQLITE", str(tmp_path / "historico.sqlite"))
    st.cache_data.clear()
    yield raw
    st.cache_data.clear()


@pytest.fixture
def datos_prueba(_aislar):
    """Carpeta data_raw temporal con los 8 Excel de prueba."""
    fixtures_excel.generar_todos(str(_aislar))
    return _aislar


@pytest.fixture
def reemplazar(_aislar):
    """Guarda un Workbook (normalmente dañado a propósito) en lugar de uno de los 8 archivos."""
    def _reemplazar(nombre_archivo, wb):
        wb.save(str(_aislar / nombre_archivo))
        st.cache_data.clear()
    return _reemplazar
