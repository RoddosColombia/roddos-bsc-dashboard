"""Respaldo de los Excel subidos en MongoDB (base `bsc_dashboard` del clúster de COMPAS).

Streamlit Cloud borra el disco en cada reinicio: al arrancar, los archivos que falten
en data_raw/ se reescriben desde aquí. Un documento por archivo: versión actual + 1 anterior.
"""
import os
import datetime

from pymongo import MongoClient


def conectar(uri, nombre_db):
    return MongoClient(uri, serverSelectionTimeoutMS=8000)[nombre_db]


def guardar(db, nombre_archivo, contenido):
    previo = db.archivos.find_one({"_id": nombre_archivo}, {"actual": 1, "subido_en": 1})
    db.archivos.replace_one(
        {"_id": nombre_archivo},
        {
            "actual": contenido,
            "subido_en": datetime.datetime.now(datetime.timezone.utc),
            "anterior": previo["actual"] if previo else None,
            "anterior_subido_en": previo["subido_en"] if previo else None,
        },
        upsert=True,
    )


def restaurar_faltantes(db, rutas):
    restaurados = []
    for ruta in rutas:
        if os.path.exists(ruta):
            continue
        nombre = os.path.basename(ruta)
        doc = db.archivos.find_one({"_id": nombre}, {"actual": 1})
        if not doc:
            continue
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as f:
            f.write(doc["actual"])
        restaurados.append(nombre)
    return restaurados
