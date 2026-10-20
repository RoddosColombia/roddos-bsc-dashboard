"""Objetivos mensuales por rubro.

Desde Fase 1 (2026-09-23) las metas viven en Metas_RODDOS.xlsx, cargado
como cualquier otro archivo en 'Actualizar datos' y leído con
data_sources.leer_metas() — no en un JSON local. Esto evita el problema
de persistencia de Streamlit Community Cloud (el disco local se borra en
cada redeploy) y mantiene una sola forma de actualizar todo: subir un
Excel. Este módulo solo guarda la lógica de cálculo que no depende de
dónde vive el dato.
"""
import calendar

# rubros que se ACUMULAN durante el mes (comparar contra meta prorrateada al dia
# de hoy, no contra la meta del mes completo -- si no, el dia 5 del mes siempre
# se ve "rezagado" aunque vaya perfecto).
RUBROS_FLUJO_MENSUAL = {
    "ventas", "ci_dinero", "activaciones", "pagos_num", "pagos_dinero",
    "ci_completas", "ci_parciales", "facturacion",
}


def proyeccion_cierre(valor_a_hoy: float, dia_del_mes: int, dias_del_mes: int, objetivo: float):
    """Proyecta el cierre de mes con el ritmo promedio observado hasta hoy."""
    if dia_del_mes <= 0 or valor_a_hoy is None:
        return None, None, None
    ritmo_diario = valor_a_hoy / dia_del_mes
    proyeccion = ritmo_diario * dias_del_mes
    dias_restantes = max(1, dias_del_mes - dia_del_mes)
    ritmo_requerido = max(0, (objetivo - valor_a_hoy)) / dias_restantes if objetivo else None
    return proyeccion, ritmo_diario, ritmo_requerido


# rubros que salen del Excel de Inventario: su "hoy" es la fecha de corte de ese
# archivo (celda K2), no la de Recaudo. Los dos archivos pueden subirse en días distintos.
RUBROS_FUENTE_INVENTARIO = {
    "ventas", "facturacion", "ci_completas", "ci_parciales", "ci_dinero", "activaciones", "dias_inventario",
}


def fecha_corte_rubro(clave, hoy_recaudo, hoy_inv):
    """Fecha de corte que aplica a un rubro según el archivo del que sale."""
    return hoy_inv if clave in RUBROS_FUENTE_INVENTARIO else hoy_recaudo


def proyeccion_rubro(clave, valor_a_hoy, objetivo, hoy_recaudo, hoy_inv):
    """Proyección de cierre usando el día y la longitud del mes de la fuente del rubro.

    Antes se usaba siempre el día de Recaudo: si Inventario venía de otro día, ventas y
    cuotas iniciales se proyectaban con un ritmo equivocado.
    """
    corte = fecha_corte_rubro(clave, hoy_recaudo, hoy_inv)
    dias_del_mes = calendar.monthrange(corte.year, corte.month)[1]
    return proyeccion_cierre(valor_a_hoy, corte.day, dias_del_mes, objetivo)


def dias_del_mes_rubro(clave, hoy_recaudo, hoy_inv):
    """Días del mes de la fuente del rubro (para prorratear su meta)."""
    corte = fecha_corte_rubro(clave, hoy_recaudo, hoy_inv)
    return calendar.monthrange(corte.year, corte.month)[1]


# De qué archivo sale cada indicador con meta, y qué columna de Metas_RODDOS.xlsx le corresponde.
# La meta se toma del MES DE CORTE DE ESE ARCHIVO: si Inventario ya está en octubre y Recaudo
# sigue en septiembre, las ventas se comparan con la meta de octubre, no con la de septiembre.
FUENTE_DE_META = {
    "ventas": ("inventario", "ventas"),
    "activaciones": ("inventario", "ventas"),
    "ci_dinero": ("inventario", "ci_dinero"),
    "pct_aprobacion": ("embudo", "pct_aprobacion"),
}


def objetivos_del_mes(leer_metas, cortes, meta_pactada_recaudo=None):
    """Arma las metas de cada indicador según el mes de corte de su archivo.

    leer_metas: función fecha -> fila de metas (dict) o None (data_sources.leer_metas).
    cortes: {"recaudo": date, "inventario": date, "embudo": date o None}.
    meta_pactada_recaudo: la meta de recaudo que trae el propio archivo de Recaudo.

    Devuelve (objetivos {clave: valor}, metas_por_fuente {fuente: fila de metas o None}).
    Si una fuente no tiene fecha, usa las metas del mes de Recaudo.
    """
    por_mes = {}

    def metas_de(fecha):
        if fecha is None:
            return None
        k = (fecha.year, fecha.month)
        if k not in por_mes:
            por_mes[k] = leer_metas(fecha)
        return por_mes[k]

    metas_por_fuente = {fuente: metas_de(fecha) for fuente, fecha in cortes.items()}
    objetivos = {}
    for clave, (fuente, campo) in FUENTE_DE_META.items():
        fila = metas_por_fuente.get(fuente) or metas_por_fuente.get("recaudo")
        if fila and fila.get(campo) is not None:
            objetivos[clave] = fila[campo]
    if meta_pactada_recaudo:
        objetivos["pagos_dinero"] = meta_pactada_recaudo
    return objetivos, metas_por_fuente


def fecha_de_texto(v):
    """'2026-10-12' (como guarda metricas el corte) -> date; None si no aplica."""
    import datetime

    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v)) if v else None
    except ValueError:
        return None
