"""¿Los datos están al día? Compara la fecha de corte de cada archivo con hoy.

La rutina del instructivo es subir cada mañana los datos del día anterior. Por eso el
atraso se cuenta en DÍAS HÁBILES (lunes a viernes): un lunes, datos del viernes están
al día. Los festivos no se descuentan, así que el día después de un festivo puede
aparecer un aviso amarillo de un día de más; no es grave.

Módulo puro (sin Streamlit) para poder probarlo con cualquier fecha.
"""
import datetime

import numpy as np

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Días hábiles de atraso tolerados antes de avisar.
MAX_HABILES_AL_DIA = 1    # 0-1: al día (por ejemplo, la mañana antes de subir el archivo)
MAX_HABILES_ATRASO = 4    # 2-4: aviso amarillo. 5 o más (una semana): aviso rojo.

AL_DIA, ATRASO, GRAVE, SIN_FECHA = "al_dia", "atraso", "grave", "sin_fecha"


def _hoy():
    return datetime.date.today()


def fecha_larga(d, hoy):
    """'28 de septiembre' (y el año solo si no es el actual)."""
    txt = f"{d.day} de {MESES[d.month]}"
    return txt if d.year == hoy.year else f"{txt} de {d.year}"


def habiles_de_atraso(corte, hoy):
    """Días hábiles entre el día siguiente al corte y ayer (incluidos)."""
    if corte >= hoy:
        return 0
    return int(np.busday_count(corte + datetime.timedelta(days=1), hoy))


def revisar(cortes, hoy=None):
    """cortes: {nombre de la fuente: fecha de corte (date) o None}.
    Devuelve una lista de dicts con: fuente, corte, dias, habiles, nivel, texto."""
    hoy = hoy or _hoy()
    resultado = []
    for fuente, corte in cortes.items():
        if isinstance(corte, datetime.datetime):
            corte = corte.date()
        if corte is None:
            resultado.append(dict(fuente=fuente, corte=None, dias=None, habiles=None, nivel=SIN_FECHA,
                                  texto=f"{fuente}: no se pudo saber la fecha de corte"))
            continue
        dias = (hoy - corte).days
        habiles = habiles_de_atraso(corte, hoy)
        if habiles <= MAX_HABILES_AL_DIA:
            nivel = AL_DIA
        elif habiles <= MAX_HABILES_ATRASO:
            nivel = ATRASO
        else:
            nivel = GRAVE
        if dias <= 0:
            cuando = "de hoy"
        elif dias == 1:
            cuando = "de ayer"
        else:
            cuando = f"hace {dias} días"
        resultado.append(dict(fuente=fuente, corte=corte, dias=dias, habiles=habiles, nivel=nivel,
                              texto=f"{fuente}: datos del {fecha_larga(corte, hoy)} ({cuando})"))
    return resultado


def nivel_general(resultado):
    niveles = {r["nivel"] for r in resultado}
    for n in (GRAVE, ATRASO, SIN_FECHA):
        if n in niveles:
            return n
    return AL_DIA
