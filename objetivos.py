"""Objetivos mensuales por rubro.

Desde Fase 1 (2026-09-23) las metas viven en Metas_RODDOS.xlsx, cargado
como cualquier otro archivo en 'Actualizar datos' y leído con
data_sources.leer_metas() — no en un JSON local. Esto evita el problema
de persistencia de Streamlit Community Cloud (el disco local se borra en
cada redeploy) y mantiene una sola forma de actualizar todo: subir un
Excel. Este módulo solo guarda la lógica de cálculo que no depende de
dónde vive el dato.
"""

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
