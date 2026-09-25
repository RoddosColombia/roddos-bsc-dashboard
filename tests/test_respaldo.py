import os
import sys
import tomllib
import datetime

import mongomock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import respaldo

SECRETS = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "secrets.toml")


@pytest.fixture
def db():
    return mongomock.MongoClient()["bsc_dashboard"]


def test_guardar_primera_vez_no_tiene_anterior(db):
    respaldo.guardar(db, "Metas_RODDOS.xlsx", b"v1")
    doc = db.archivos.find_one({"_id": "Metas_RODDOS.xlsx"})
    assert doc["actual"] == b"v1"
    assert doc.get("anterior") is None
    assert isinstance(doc["subido_en"], datetime.datetime)


def test_guardar_mueve_actual_a_anterior_y_conserva_solo_uno(db):
    respaldo.guardar(db, "Metas_RODDOS.xlsx", b"v1")
    respaldo.guardar(db, "Metas_RODDOS.xlsx", b"v2")
    respaldo.guardar(db, "Metas_RODDOS.xlsx", b"v3")
    doc = db.archivos.find_one({"_id": "Metas_RODDOS.xlsx"})
    assert doc["actual"] == b"v3"
    assert doc["anterior"] == b"v2"
    assert db.archivos.count_documents({}) == 1


def test_guardar_no_mezcla_archivos(db):
    respaldo.guardar(db, "A.xlsx", b"a")
    respaldo.guardar(db, "B.xlsx", b"b")
    assert db.archivos.find_one({"_id": "A.xlsx"})["actual"] == b"a"
    assert db.archivos.find_one({"_id": "B.xlsx"})["actual"] == b"b"


def test_restaurar_escribe_solo_los_que_faltan(db, tmp_path):
    respaldo.guardar(db, "A.xlsx", b"desde_mongo_a")
    respaldo.guardar(db, "B.xlsx", b"desde_mongo_b")
    ruta_a = tmp_path / "A.xlsx"
    ruta_b = tmp_path / "B.xlsx"
    ruta_b.write_bytes(b"local_b")

    restaurados = respaldo.restaurar_faltantes(db, [str(ruta_a), str(ruta_b)])

    assert ruta_a.read_bytes() == b"desde_mongo_a"
    assert ruta_b.read_bytes() == b"local_b"
    assert restaurados == ["A.xlsx"]


def test_restaurar_ignora_archivos_sin_respaldo(db, tmp_path):
    ruta = tmp_path / "Nunca_subido.xlsx"
    assert respaldo.restaurar_faltantes(db, [str(ruta)]) == []
    assert not ruta.exists()


def test_restaurar_crea_la_carpeta_si_no_existe(db, tmp_path):
    respaldo.guardar(db, "A.xlsx", b"a")
    ruta = tmp_path / "data_raw" / "A.xlsx"
    respaldo.restaurar_faltantes(db, [str(ruta)])
    assert ruta.read_bytes() == b"a"


@pytest.mark.skipif(not os.path.exists(SECRETS), reason="sin .streamlit/secrets.toml")
def test_conexion_real_atlas():
    with open(SECRETS, "rb") as f:
        cfg = tomllib.load(f)["mongo"]
    if "PEGA_AQUI" in cfg["uri"]:
        pytest.skip("secrets.toml todavía tiene el texto de ejemplo")
    db = respaldo.conectar(cfg["uri"], cfg["db"])
    respaldo.guardar(db, "_prueba_conexion.xlsx", b"ok")
    assert db.archivos.find_one({"_id": "_prueba_conexion.xlsx"})["actual"] == b"ok"
    db.archivos.delete_one({"_id": "_prueba_conexion.xlsx"})
