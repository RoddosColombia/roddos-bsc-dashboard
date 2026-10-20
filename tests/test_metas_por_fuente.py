"""Cada indicador se compara con la meta del mes de SU archivo.

Caso real (19 oct 2026): Recaudo con datos del 14 de septiembre e Inventario del 12 de octubre.
Antes, las ventas de octubre se comparaban con la meta de septiembre.
"""
import datetime as dt
import os

from streamlit.testing.v1 import AppTest

import fixtures_excel as fx
import frescura
import historico
import objetivos as obj

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEP, OCT = dt.date(2026, 9, 14), dt.date(2026, 10, 12)
METAS = {9: dict(mes=dt.date(2026, 9, 1), ventas=100, ci_dinero=40e6, pct_aprobacion=0.5),
         10: dict(mes=dt.date(2026, 10, 1), ventas=30, ci_dinero=45e6, pct_aprobacion=0.6)}


class LectorFalso:
    def __init__(self):
        self.lecturas = []

    def __call__(self, fecha):
        self.lecturas.append(fecha)
        return METAS.get(fecha.month)


def test_ventas_usan_la_meta_del_mes_de_inventario():
    objetivos, por_fuente = obj.objetivos_del_mes(LectorFalso(), {"recaudo": SEP, "inventario": OCT, "embudo": OCT},
                                                  meta_pactada_recaudo=60e6)
    assert objetivos["ventas"] == 30 and objetivos["activaciones"] == 30     # octubre, no septiembre
    assert objetivos["ci_dinero"] == 45e6
    assert objetivos["pct_aprobacion"] == 0.6
    assert objetivos["pagos_dinero"] == 60e6                                   # la del archivo de Recaudo
    assert por_fuente["recaudo"]["mes"].month == 9 and por_fuente["inventario"]["mes"].month == 10


def test_sin_fecha_de_embudo_usa_el_mes_de_recaudo():
    objetivos, _ = obj.objetivos_del_mes(LectorFalso(), {"recaudo": SEP, "inventario": OCT, "embudo": None})
    assert objetivos["pct_aprobacion"] == 0.5


def test_lee_cada_mes_una_sola_vez():
    lector = LectorFalso()
    obj.objetivos_del_mes(lector, {"recaudo": OCT, "inventario": OCT, "embudo": OCT})
    assert len(lector.lecturas) == 1


def test_sin_archivo_de_metas_solo_queda_la_meta_de_recaudo():
    objetivos, _ = obj.objetivos_del_mes(lambda f: None, {"recaudo": SEP, "inventario": OCT}, 60e6)
    assert objetivos == {"pagos_dinero": 60e6}


def test_prorrateo_con_los_dias_del_mes_de_cada_fuente():
    assert obj.dias_del_mes_rubro("ventas", SEP, OCT) == 31          # octubre
    assert obj.dias_del_mes_rubro("pagos_dinero", SEP, OCT) == 30    # septiembre


def test_meses_en_espanol():
    assert frescura.mes_y_anio(dt.date(2026, 9, 14)) == "Septiembre 2026"
    assert frescura.mes_y_anio(dt.datetime(2026, 10, 1)) == "Octubre 2026"


def test_pagina_principal_con_archivos_en_meses_distintos(datos_prueba, reemplazar):
    """Recaudo en septiembre, Inventario en octubre (los Excel de prueba tienen metas de ambos meses)."""
    reemplazar("Proyeccion_Recaudo.xlsx", fx.wb_recaudo(hoy=dt.date(2026, 9, 20)))
    at = AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    at.run()
    assert not at.exception
    textos = " ".join(str(c.value) for c in at.caption)
    assert "Mes de trabajo: Octubre 2026 · Recaudo aún en septiembre" in textos
    assert "Metas vigentes desde Octubre 2026" in textos
    assert "están en meses distintos" in textos
    alm = historico.AlmacenLocal()
    octubre = alm.obtener("2026-10")["datos"]                # las ventas (Inventario) van a SU mes: octubre
    assert octubre["ventas"] == 12 and octubre["_metas"]["ventas"] == 30
    septiembre = alm.obtener("2026-09")["datos"]             # el recaudo (Recaudo) va a septiembre
    assert septiembre["_cortes"]["recaudo"] == "2026-09-20" and "inventario" not in septiembre["_cortes"]
