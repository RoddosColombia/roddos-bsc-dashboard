import datetime
import os
import sys

import mongomock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import historico  # noqa: E402

M = {"pagos_dinero": {"mes": 1000.0}, "ventas": {"mes": 5}, "leads": {"mes": None}}


def _foto(corte, pagos=1000.0):
    m = {**M, "pagos_dinero": {"mes": pagos}}
    return historico.armar_foto(m, corte, corte, {"pagos_dinero": 2000})


@pytest.fixture(params=["local", "mongo"])
def alm(request, tmp_path):
    if request.param == "local":
        return historico.AlmacenLocal(str(tmp_path / "h.sqlite"))
    return historico.AlmacenMongo(mongomock.MongoClient()["bsc_dashboard"])


def test_armar_foto_usa_mes_del_corte():
    f = _foto(datetime.date(2026, 10, 9))
    assert f["periodo"] == "2026-10"
    assert f["datos"]["pagos_dinero"] == 1000.0
    assert f["datos"]["leads"] is None
    assert f["datos"]["_metas"]["pagos_dinero"] == 2000.0


def test_una_foto_por_mes_se_actualiza(alm):
    assert historico.registrar(alm, _foto(datetime.date(2026, 10, 5), 500))
    assert historico.registrar(alm, _foto(datetime.date(2026, 10, 9), 900))
    fotos = alm.listar()
    assert len(fotos) == 1
    assert fotos[0]["datos"]["pagos_dinero"] == 900


def test_excel_viejo_no_pisa_foto_mas_reciente(alm):
    historico.registrar(alm, _foto(datetime.date(2026, 10, 9), 900))
    assert not historico.registrar(alm, _foto(datetime.date(2026, 10, 2), 100))
    assert alm.obtener("2026-10")["datos"]["pagos_dinero"] == 900


def test_datos_iguales_no_escribe(alm):
    assert historico.registrar(alm, _foto(datetime.date(2026, 10, 9)))
    assert not historico.registrar(alm, _foto(datetime.date(2026, 10, 9)))


def test_meses_distintos_se_acumulan_en_orden(alm):
    historico.registrar(alm, _foto(datetime.date(2026, 11, 3)))
    historico.registrar(alm, _foto(datetime.date(2026, 9, 30)))
    historico.registrar(alm, _foto(datetime.date(2026, 10, 31)))
    assert [f["periodo"] for f in alm.listar()] == ["2026-09", "2026-10", "2026-11"]


def test_sin_configuracion_usa_local_nunca_mongo(monkeypatch, tmp_path):
    monkeypatch.setattr(historico, "RUTA_SQLITE", str(tmp_path / "h.sqlite"))
    assert isinstance(historico.almacen(), historico.AlmacenLocal)
