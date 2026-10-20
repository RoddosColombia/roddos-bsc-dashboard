"""Reconstruye las fotos de meses ANTERIORES a partir de la historia que ya traen los Excel.

El histórico (historico.py) empezó a guardar fotos en octubre de 2026. Pero los Excel tienen
historia: cada pago tiene su fecha, el Inventario trae un resumen mes a mes y el Embudo tiene
la fecha de cada lead y de cada decisión. Con eso se rellenan los meses anteriores.

Regla: solo se reconstruye lo que se puede calcular EXACTO, con las mismas fórmulas del tablero
en vivo (metricas.py). Lo que depende del estado actual de las cuotas (cartera vencida, mora) o
de una foto del día (motos disponibles) no se puede saber hacia atrás y queda vacío.

Una foto real (tomada en vivo) nunca se reemplaza por una reconstruida.
"""
import calendar
import datetime
import re

import pandas as pd

import formatos

MESES_ES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
            "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}
MAX_MESES = 12  # hacia atrás desde el mes de trabajo

INDICADORES_RECONSTRUIDOS = ["pagos_dinero", "pagos_num", "cuotas_mes", "ventas", "activaciones", "ci_dinero",
                             "leads", "formularios", "aprobados_rechazados", "pct_aprobacion"]


def mes_de_etiqueta(etiqueta, referencia):
    """'Marzo', 'mar-26', 'Marzo 2026' o una fecha -> (año, mes). Sin año, se asume el de
    `referencia`, o el anterior si el mes es posterior (p. ej. 'Diciembre' leído en enero)."""
    if isinstance(etiqueta, (datetime.date, datetime.datetime)):
        return etiqueta.year, etiqueta.month
    txt = str(etiqueta or "").strip().lower()
    m = re.match(r"([a-záéíóú]{3})[a-záéíóú]*\.?[\s\-/]*(\d{2,4})?$", txt)
    if not m or m.group(1) not in MESES_ES:
        return None
    mes = MESES_ES[m.group(1)]
    if m.group(2):
        anio = int(m.group(2))
        anio = anio + 2000 if anio < 100 else anio
    else:
        anio = referencia.year if mes <= referencia.month else referencia.year - 1
    return anio, mes


def _fin_de_mes(anio, mes):
    return datetime.date(anio, mes, calendar.monthrange(anio, mes)[1])


def _meses_anteriores(mes_trabajo):
    """Los MAX_MESES meses anteriores a mes_trabajo, como (año, mes)."""
    a, m = mes_trabajo.year, mes_trabajo.month
    out = []
    for _ in range(MAX_MESES):
        m -= 1
        if m == 0:
            a, m = a - 1, 12
        out.append((a, m))
    return out


def _de_recaudo(rec, anio, mes):
    """Pagos del mes y cuotas programadas al cierre (mismas fórmulas que metricas.py)."""
    cuotas = rec["cuotas"].copy()
    for col in ("Fecha prog.", "Fecha pago SISMO"):
        cuotas[col] = pd.to_datetime(cuotas[col], errors="coerce")
    ini, fin = datetime.date(anio, mes, 1), _fin_de_mes(anio, mes)
    pagos = cuotas.dropna(subset=["Fecha pago SISMO"])
    p = pagos[(pagos["Fecha pago SISMO"].dt.date >= ini) & (pagos["Fecha pago SISMO"].dt.date <= fin)]
    if p.empty:
        return {}
    progs = cuotas.dropna(subset=["Fecha prog."])
    return dict(pagos_num=float(len(p)), pagos_dinero=float(p["Pagado SISMO"].fillna(0).sum()),
                cuotas_mes=float((progs["Fecha prog."].dt.date <= fin).sum()))


def _de_inventario(inv, referencia):
    """{(año, mes): {...}} desde el resumen mensual del Inventario."""
    out = {}
    mensual = inv.get("mensual")
    if mensual is None or mensual.empty:
        return out
    for fila in mensual.to_dict("records"):
        am = mes_de_etiqueta(fila.get("mes"), referencia)
        if am is None:
            continue
        datos = {}
        for clave, col in (("ventas", "vendidas"), ("activaciones", "activadas"), ("ci_dinero", "cuotas_iniciales")):
            v = fila.get(col)
            if isinstance(v, (int, float)) and not pd.isna(v):
                datos[clave] = float(v)
        if datos:
            out[am] = datos
    return out


def _de_embudo(embudo, anio, mes):
    if embudo is None or embudo.empty:
        return {}
    ini, fin = datetime.date(anio, mes, 1), _fin_de_mes(anio, mes)

    def contar(col, filtro=None):
        if col not in embudo.columns:
            return 0
        con_fecha = embudo[embudo[col].notna()]
        m = con_fecha[(con_fecha[col].dt.date >= ini) & (con_fecha[col].dt.date <= fin)]
        return len(filtro(m) if filtro is not None else m)

    leads = contar("Fecha lead")
    if not leads:
        return {}
    aprob = contar("Fecha decision", lambda m: m[m["Decision"] == "Aprobado"])
    rech = contar("Fecha decision", lambda m: m[m["Decision"] == "Rechazado"])
    return dict(leads=float(leads), formularios=float(contar("Fecha formulario")),
                aprobados_rechazados=float(aprob + rech),
                pct_aprobacion=round(aprob / (aprob + rech), 4) if (aprob + rech) else None)


def _metas_del_mes(leer_metas, anio, mes):
    try:
        fila = leer_metas(_fin_de_mes(anio, mes))
    except Exception:
        return {}
    if not fila or fila["mes"] > _fin_de_mes(anio, mes):
        return {}
    return {k: v for k, v in dict(ventas=fila.get("ventas"), activaciones=fila.get("ventas"),
                                  ci_dinero=fila.get("ci_dinero"),
                                  pct_aprobacion=fila.get("pct_aprobacion")).items() if v is not None}


def reconstruir(rec, inv, embudo, leer_metas, mes_trabajo, hoy_inv=None, ahora=None, hoy_emb=None):
    """Fotos de meses anteriores con los datos reconstruibles de cada fuente.

    Cada fuente se reconstruye solo para los meses ANTERIORES a su propio mes de corte (el mes de
    corte lo toma la foto en vivo): Recaudo hasta antes de `mes_trabajo`, Inventario hasta antes de
    `hoy_inv`, Embudo hasta antes de `hoy_emb`.

    rec / inv: lo que devuelven data_sources.leer_recaudo() / leer_inventario().
    embudo: DataFrame de data_sources.leer_embudo() (o None).
    leer_metas: data_sources.leer_metas.
    """
    ahora = ahora or formatos.ahora_colombia().replace(tzinfo=None)
    actual = {"recaudo": mes_trabajo, "inventario": hoy_inv or mes_trabajo, "embudo": hoy_emb or mes_trabajo}
    actual = {k: (v.year, v.month) for k, v in actual.items()}
    ultimo = max(actual.values())
    por_mes_inv = _de_inventario(inv, hoy_inv or mes_trabajo)
    fotos = []
    for anio, mes in sorted(_meses_anteriores(datetime.date(ultimo[0], ultimo[1], 1))):
        datos = {}
        if (anio, mes) < actual["recaudo"]:
            datos.update(_de_recaudo(rec, anio, mes))
        if (anio, mes) < actual["inventario"]:
            datos.update(por_mes_inv.get((anio, mes), {}))
        if (anio, mes) < actual["embudo"]:
            datos.update(_de_embudo(embudo, anio, mes))
        if not datos:
            continue
        datos["_metas"] = _metas_del_mes(leer_metas, anio, mes)
        datos["_reconstruida"] = True
        fotos.append(dict(periodo=f"{anio}-{mes:02d}", corte=str(_fin_de_mes(anio, mes)),
                          guardado_en=ahora.isoformat(timespec="seconds"), datos=datos))
    return fotos
