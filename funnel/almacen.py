"""Totales del funnel en la base del tablero (bsc_dashboard.funnel_resumen).

Dos documentos: "actual" (lo que muestra la página) y "anterior" (la ejecución previa, por si
hay que comparar o volver atrás). Nunca contienen datos personales.
"""
COLECCION = "funnel_resumen"


def guardar(db, resumen):
    col = db[COLECCION]
    previo = col.find_one({"_id": "actual"})
    if previo:
        previo["_id"] = "anterior"
        col.replace_one({"_id": "anterior"}, previo, upsert=True)
    col.replace_one({"_id": "actual"}, dict(resumen, _id="actual"), upsert=True)


def leer(db):
    return db[COLECCION].find_one({"_id": "actual"}) if db is not None else None
