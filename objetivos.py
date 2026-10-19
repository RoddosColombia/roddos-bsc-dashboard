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
