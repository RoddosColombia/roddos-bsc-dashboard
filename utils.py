"""Utilidades compartidas del BSC de RODDOS."""


def cop(n) -> str:
    """Formatea un numero como pesos colombianos: $1.234.567"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    sign = "-" if n < 0 else ""
    n = abs(round(n))
    return f"{sign}${n:,.0f}".replace(",", ".")


PALETTE = {
    "financiera": "#2E4053",
    "cliente": "#1F6F5C",
    "procesos": "#B7791F",
    "aprendizaje": "#6B46C1",
    "ok": "#1F6F5C",
    "alerta": "#B7791F",
    "critico": "#9C2B0F",
    "neutro": "#7A7A7A",
}


def semaforo(valor, umbral_verde, umbral_amarillo, invertido=False):
    """Devuelve color segun umbrales. Si invertido=True, menor es mejor."""
    if invertido:
        if valor <= umbral_verde:
            return PALETTE["ok"]
        if valor <= umbral_amarillo:
            return PALETTE["alerta"]
        return PALETTE["critico"]
    if valor >= umbral_verde:
        return PALETTE["ok"]
    if valor >= umbral_amarillo:
        return PALETTE["alerta"]
    return PALETTE["critico"]
