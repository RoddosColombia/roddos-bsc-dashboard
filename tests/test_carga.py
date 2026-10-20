"""carga.py: el camino único para aceptar un archivo (carga manual y SharePoint)."""
import io
import os

import mongomock

import carga
import data_sources as ds
import fixtures_excel as fx


def _bytes(wb):
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _fuente(nombre):
    return next(f for f in carga.fuentes() if f["nombre"] == nombre)


def test_archivo_bueno_se_guarda(_aislar):
    r = carga.procesar(_fuente("Recaudo"), _bytes(fx.wb_recaudo()))
    assert r == dict(ok=True, errores=[], aviso=None)
    assert ds.leer_recaudo()["dashboard"]["meta_pactada"] == 60_000_000


def test_archivo_malo_no_toca_el_anterior(datos_prueba):
    antes = open(ds.F_RECAUDO, "rb").read()
    wb = fx.wb_recaudo()
    wb.remove(wb["Detalle Cuotas"])
    r = carga.procesar(_fuente("Recaudo"), _bytes(wb))
    assert not r["ok"] and r["errores"]
    assert open(ds.F_RECAUDO, "rb").read() == antes


def test_no_es_un_excel(_aislar):
    r = carga.procesar(_fuente("Metas del mes"), b"esto no es un excel")
    assert not r["ok"] and "No se pudo abrir" in r["errores"][0]


def test_guarda_la_version_anterior(datos_prueba):
    antes = open(ds.F_METAS, "rb").read()
    assert carga.procesar(_fuente("Metas del mes"), _bytes(fx.wb_metas()))["ok"]
    anterior = os.path.join(os.path.dirname(ds.F_METAS), "versiones", "Metas_RODDOS.xlsx.anterior.xlsx")
    assert open(anterior, "rb").read() == antes


def test_respaldo_en_mongo(_aislar, monkeypatch):
    db = mongomock.MongoClient()["bsc_dashboard"]
    monkeypatch.setattr(ds, "db_respaldo", lambda: db)
    contenido = _bytes(fx.wb_inventario())
    assert carga.procesar(_fuente("Inventario / Ventas"), contenido)["ok"]
    assert db.archivos.find_one({"_id": "Inventario_2026.xlsx"})["actual"] == contenido


def test_si_falla_el_respaldo_el_archivo_igual_queda_y_avisa(_aislar, monkeypatch):
    class DBRota:
        @property
        def archivos(self):
            raise RuntimeError("sin conexión")
    monkeypatch.setattr(ds, "db_respaldo", lambda: DBRota())
    r = carga.procesar(_fuente("Inventario / Ventas"), _bytes(fx.wb_inventario()))
    assert r["ok"] and "NO quedó respaldado" in r["aviso"]
    assert os.path.exists(ds.F_INVENTARIO)
