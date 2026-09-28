"""Utilidades compartidas del BSC de RODDOS."""
import streamlit as st

# Identidad de marca RODDOS
NEGRO = "#121212"
CIAN = "#00E5FF"
VERDE = "#00C853"
AMBAR = "#FFB300"
ROJO = "#FF5252"
NEUTRO = "#9AA0A6"

_ESTILO = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Raleway:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, span, div, label, input, textarea, button {
    font-family: 'Raleway', sans-serif;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    letter-spacing: -0.01em;
}
h1 { color: #FFFFFF; }

/* Tarjetas de indicadores (st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #1A1A1A;
    border: 1px solid #2C2C2C !important;
    border-radius: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.4);
}
/* Número grande dentro de la tarjeta */
[data-testid="stVerticalBlockBorderWrapper"] h3 {
    color: #FFFFFF;
    font-size: 1.85rem;
    font-weight: 800;
    margin: 0.15rem 0 0.35rem 0;
}
/* Etiqueta de la tarjeta */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"]:first-child p {
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.68rem;
    color: #9AA0A6;
    font-weight: 600;
}
/* Barra de progreso en acento cian */
[data-testid="stProgress"] div[role="progressbar"] > div { background-color: #00E5FF; }
</style>
"""


def estilo_roddos():
    """Inyecta la identidad visual de RODDOS. Llamar tras set_page_config en cada página."""
    st.markdown(_ESTILO, unsafe_allow_html=True)


CARD = "background:#1A1A1A;border:1px solid #2C2C2C;border-radius:14px;padding:16px 18px;"


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def hsafe(s):
    """'$' como entidad HTML: se ve como $ y no dispara KaTeX dentro de HTML."""
    return str(s).replace("$", "&#36;")


def kpi(etiqueta, valor, chip_txt=None, chip_color=NEUTRO, sub=None, valor_color="#FFFFFF", tam=26):
    """Tarjeta de indicador estilo CEO. Usar dentro de `with col:` para grillas."""
    chip = f"<span style='color:{chip_color};font-size:12px;font-weight:700'>● {chip_txt}</span>" if chip_txt else ""
    subhtml = f"<div style='color:#8A8F94;font-size:12px;margin-top:3px'>{hsafe(sub)}</div>" if sub else ""
    html(f"<div style='{CARD}'>"
         f"<div style='color:#9AA0A6;font-size:13px'>{hsafe(etiqueta)}</div>"
         f"<div style='font-family:Montserrat,sans-serif;font-weight:800;font-size:{tam}px;color:{valor_color};margin:4px 0'>{hsafe(valor)}</div>"
         f"{chip}{subhtml}</div>")


def hero(etiqueta, valor, chip_txt=None, chip_color=NEUTRO, sub=None):
    """Tarjeta de número principal, grande, con pill a la derecha."""
    chip = (f"<span style='background:{chip_color}22;color:{chip_color};font-size:12px;font-weight:700;"
            f"padding:4px 12px;border-radius:20px;white-space:nowrap'>{chip_txt}</span>") if chip_txt else ""
    subhtml = f"<div style='font-size:13px;color:#9AA0A6;margin-top:8px'>{hsafe(sub)}</div>" if sub else ""
    html(f"<div style='{CARD}'>"
         f"<div style='display:flex;justify-content:space-between;align-items:flex-start'>"
         f"<div><div style='color:#9AA0A6;font-size:13px'>{hsafe(etiqueta)}</div>"
         f"<div style='margin-top:4px'><span style='font-family:Montserrat,sans-serif;font-weight:800;font-size:38px;color:#FFFFFF'>{hsafe(valor)}</span></div></div>"
         f"{chip}</div>{subhtml}</div>")


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
