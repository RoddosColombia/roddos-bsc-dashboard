"""Histórico por fuente: cada indicador se guarda en el mes de SU archivo.

Caso real (20 oct 2026): Recaudo con datos de septiembre; Inventario y Embudo de octubre.
Antes: solo existía la foto de septiembre, y además llevaba adentro las ventas de octubre.
"""
import datetime as dt
import os

from streamlit.testing.v1 import AppTest

import data_sources as ds
import fixtures_excel as fx
import historico
import metricas as mx

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEP = dt.date(2026, 9, 20)


def _recaudo_en_septiembre(reemplazar):
    reemplazar("Proyeccion_Recaudo.xlsx", fx.wb_recaudo(hoy=SEP))


def _abrir_principal():
    at = AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    return at.run()


# ---------------------------------------------------------------- el "ayer" del embudo

def test_embudo_usa_su_propia_fecha_y_no_la_de_recaudo(datos_prueba, reemplazar):
    _recaudo_en_septiembre(reemplazar)
    data = mx.construir_metricas()
    assert data["hoy_recaudo"] == SEP
    assert data["hoy_emb"] == fx.HOY                         # el último lead es del 9 de octubre
    M = data["metricas"]
    assert M["leads"]["mes"] == 12                           # leads de OCTUBRE (antes: septiembre → 0)
    assert M["leads"]["corte"] == str(fx.HOY)


def test_fecha_del_embudo_no_pasa_de_hoy():
    import pandas as pd
    emb = pd.DataFrame({"Fecha lead": pd.to_datetime(["2026-10-01", "2099-01-01"])})
    assert mx.fecha_corte_embudo(emb, hoy=dt.date(2026, 10, 20)) == dt.date(2026, 10, 1)


# ---------------------------------------------------------------- fotos por fuente

def test_cada_fuente_va_a_su_mes_y_octubre_aparece(datos_prueba, reemplazar):
    _recaudo_en_septiembre(reemplazar)
    _abrir_principal()
    alm = historico.AlmacenLocal()
    sep, octubre = alm.obtener("2026-09"), alm.obtener("2026-10")
    assert octubre is not None                                                  # octubre ya se ve
    assert set(octubre["datos"]["_cortes"]) == {"inventario", "embudo"}
    assert octubre["datos"]["ventas"] == 12 and octubre["datos"]["leads"] == 12
    assert "pagos_dinero" not in octubre["datos"]                               # el recaudo no es de octubre
    assert sep["datos"]["_cortes"] == {"recaudo": "2026-09-20"}
    assert sep["datos"]["ventas"] == 11                                         # ventas de SEPTIEMBRE (reconstruidas)
    assert "ventas" in sep["datos"]["_reconstruidas"]
    assert historico.es_reconstruida(sep) and not historico.es_reconstruida(octubre)


def test_dato_en_vivo_reemplaza_al_reconstruido_pero_no_al_reves(_aislar, tmp_path):
    alm = historico.AlmacenLocal(str(tmp_path / "h.sqlite"))
    historico.registrar_reconstruidas(alm, [dict(periodo="2026-10", corte="2026-10-31", guardado_en="x",
                                                 datos={"ventas": 5.0, "_metas": {"ventas": 30}})])
    M = {"ventas": {"mes": 27}, "pagos_dinero": {"mes": 1.0}}
    historico.registrar_en_vivo(alm, M, {"inventario": dt.date(2026, 10, 20)})
    d = alm.obtener("2026-10")["datos"]
    assert d["ventas"] == 27 and "ventas" not in d["_reconstruidas"]
    historico.registrar_reconstruidas(alm, [dict(periodo="2026-10", corte="2026-10-31", guardado_en="x",
                                                 datos={"ventas": 5.0})])
    assert alm.obtener("2026-10")["datos"]["ventas"] == 27                     # el reconstruido no pisa el real


def test_un_archivo_viejo_no_pisa_uno_mas_reciente(_aislar, tmp_path):
    alm = historico.AlmacenLocal(str(tmp_path / "h.sqlite"))
    historico.registrar_en_vivo(alm, {"ventas": {"mes": 27}}, {"inventario": dt.date(2026, 10, 20)})
    historico.registrar_en_vivo(alm, {"ventas": {"mes": 3}}, {"inventario": dt.date(2026, 10, 2)})
    assert alm.obtener("2026-10")["datos"]["ventas"] == 27


def test_sin_cambios_no_escribe(_aislar, tmp_path):
    alm = historico.AlmacenLocal(str(tmp_path / "h.sqlite"))
    M, cortes = {"ventas": {"mes": 27}}, {"inventario": dt.date(2026, 10, 20)}
    assert historico.registrar_en_vivo(alm, M, cortes) == 1
    assert historico.registrar_en_vivo(alm, M, cortes) == 0


# ---------------------------------------------------------------- la foto vieja de producción

def test_foto_vieja_con_ventas_de_otro_mes_se_limpia(datos_prueba, reemplazar):
    """La foto de septiembre que guardó la versión anterior lleva las ventas del Inventario de
    octubre (anotado en _corte_inventario). Se descartan y se reconstruyen las de septiembre."""
    alm = historico.AlmacenLocal()
    alm.guardar(dict(periodo="2026-09", corte="2026-09-14", guardado_en="x", datos={
        "pagos_dinero": 9e6, "ventas": 27.0, "leads": 4.0, "_corte_inventario": "2026-10-12",
        "_metas": {"ventas": 30.0, "pagos_dinero": 60e6}}))
    _recaudo_en_septiembre(reemplazar)
    _abrir_principal()
    d = alm.obtener("2026-09")["datos"]
    assert d["ventas"] == 11 and d["_metas"]["ventas"] == 100                  # las de septiembre, no 27
    assert d["_cortes"]["recaudo"] == "2026-09-20"                             # recaudo actualizado
    assert "ventas" in d["_reconstruidas"]


def test_foto_vieja_del_mismo_mes_se_conserva(_aislar, tmp_path):
    alm = historico.AlmacenLocal(str(tmp_path / "h.sqlite"))
    alm.guardar(dict(periodo="2026-10", corte="2026-10-09", guardado_en="x",
                     datos={"ventas": 12.0, "_corte_inventario": "2026-10-09", "_metas": {}}))
    historico.registrar_reconstruidas(alm, [dict(periodo="2026-10", corte="2026-10-31", guardado_en="x",
                                                 datos={"ventas": 1.0})])
    assert alm.obtener("2026-10")["datos"] == {"ventas": 12.0, "_corte_inventario": "2026-10-09", "_metas": {}}


def test_aviso_de_frescura_incluye_el_embudo(datos_prueba, reemplazar):
    _recaudo_en_septiembre(reemplazar)
    at = _abrir_principal()
    textos = " ".join(str(e.value) for e in list(at.error) + list(at.warning)) + " ".join(str(c.value) for c in at.caption)
    assert "Recaudo: datos del 20 de septiembre" in textos and "Embudo: datos del 9 de octubre" in textos
