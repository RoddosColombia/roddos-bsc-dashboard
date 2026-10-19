"""Utilidades compartidas del BSC de RODDOS."""
import os
import base64
import streamlit as st

# Identidad de marca RODDOS — tema CLARO con acentos de marca
NEGRO = "#0F1115"
CIAN = "#00B8D4"    # cian legible sobre fondo claro
VERDE = "#00A344"
AMBAR = "#E08600"
ROJO = "#E5484D"
NEUTRO = "#8A909C"

TXT = "#1A1D23"     # texto principal
TXT2 = "#5B616E"    # texto secundario
MUT = "#8A909C"     # muted / captions
CARD_BG = "#FFFFFF"
BORDE = "#E6E8EC"
TRACK = "#EAECEF"   # fondo de barras

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "roddos_logo_blanco.png")
try:
    with open(LOGO_PATH, "rb") as _f:
        LOGO_B64 = base64.b64encode(_f.read()).decode()
except Exception:
    LOGO_B64 = ""

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
h1, h2, h3, h4, h5, h6 { color: #1A1D23; }

/* Más aire y ancho controlado para que no se vea recargado */
[data-testid="stMainBlockContainer"] { padding-top: 1.6rem; max-width: 1160px; }

/* Tarjetas de indicadores (st.container(border=True)) — claras */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border: 1px solid #E6E8EC !important;
    border-radius: 16px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.05);
}
[data-testid="stVerticalBlockBorderWrapper"] h3 {
    color: #1A1D23;
    font-size: 1.85rem;
    font-weight: 800;
    margin: 0.15rem 0 0.35rem 0;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"]:first-child p {
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.68rem;
    color: #8A909C;
    font-weight: 600;
}
/* Barra de progreso y acentos en cian */
[data-testid="stProgress"] div[role="progressbar"] > div { background-color: #00B8D4; }
/* Selector de período: activo en cian */
[data-testid="stSegmentedControl"] button[aria-checked="true"] {
    background: #E6F7FB; border-color: #00B8D4; color: #008BA3;
}
</style>
"""


def estilo_roddos():
    """Inyecta la identidad visual de RODDOS. Llamar tras set_page_config."""
    st.markdown(_ESTILO, unsafe_allow_html=True)


def encabezado(subtitulo=""):
    """Cabecera con el logo de RODDOS en una franja oscura de marca (se ve sobre el fondo claro)."""
    img = (f"<img src='data:image/png;base64,{LOGO_B64}' style='height:56px;display:block'/>"
           if LOGO_B64 else
           "<span style='color:#fff;font-family:Montserrat,sans-serif;font-weight:800;font-size:34px'>RODDOS</span>")
    sub = (f"<div style='color:#AEB4BD;font-size:13px;margin-top:6px;font-family:Montserrat,sans-serif'>{subtitulo}</div>"
           if subtitulo else "")
    st.markdown(
        f"<div style='background:#0F1115;border-radius:16px;padding:18px 24px;margin-bottom:16px'>{img}{sub}</div>",
        unsafe_allow_html=True)


CARD = "background:#FFFFFF;border:1px solid #E6E8EC;border-radius:16px;padding:16px 18px;box-shadow:0 1px 2px rgba(16,24,40,0.05);"


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def pedir_archivos(faltantes):
    """Muestra qué archivos faltan para esta página y detiene la ejecución sin error.

    Se usa cuando data_raw/ no tiene los Excel que la página necesita (instalación
    nueva, servidor reiniciado sin respaldo, etc.), en vez de dejar que la app se
    caiga con FileNotFoundError.
    """
    lista = "\n".join(f"- `{n}`" for n in faltantes)
    st.info(
        "📂 **Todavía no hay datos para mostrar esta página.**\n\n"
        "Sube estos archivos en **📤 Actualizar datos** (menú de la izquierda):\n\n"
        f"{lista}"
    )
    st.stop()


def leer_seguro(lector, archivo, *args, **kwargs):
    """Para fuentes OPCIONALES de una página: si la lectura falla, muestra un aviso
    y devuelve None, y el resto de la página sigue funcionando."""
    try:
        return lector(*args, **kwargs)
    except Exception as e:
        st.warning(f"⚠️ No se pudo leer **{archivo}** ({type(e).__name__}: {e}). "
                   "Esa sección queda sin datos; revisa el archivo y vuelve a subirlo en 📤 Actualizar datos.")
        return None


def cargar_o_detener(lector, archivos, *args, **kwargs):
    """Para la fuente PRINCIPAL de una página: si la lectura falla, muestra un mensaje
    claro (en vez del error técnico de Python) y detiene la página."""
    try:
        return lector(*args, **kwargs)
    except Exception as e:
        nombres = ", ".join(f"**{a}**" for a in ([archivos] if isinstance(archivos, str) else archivos))
        st.error(f"No se pudieron leer los datos de {nombres}. Lo más probable es que el archivo cargado "
                 "tenga un formato distinto al esperado. Súbelo de nuevo en 📤 Actualizar datos; si el "
                 "problema sigue, comparte este detalle con quien mantiene el tablero:")
        st.code(f"{type(e).__name__}: {e}")
        st.stop()


def mostrar_frescura(cortes):
    """Aviso de datos desactualizados. `cortes`: {fuente: fecha de corte}. Ver frescura.py."""
    import frescura

    res = frescura.revisar(cortes)
    nivel = frescura.nivel_general(res)
    if nivel == frescura.AL_DIA:
        st.caption("✅ Datos al día · " + " · ".join(r["texto"] for r in res))
        return
    lineas = "\n".join(f"- {'🔴' if r['nivel'] == frescura.GRAVE else '⚠️' if r['nivel'] != frescura.AL_DIA else '✅'} "
                       f"{r['texto']}" for r in res)
    cuerpo = ("Los números de esta página corresponden a esas fechas, no a hoy. "
              "Los responsables de cada archivo deben actualizarlo en SharePoint y subirlo en "
              "📤 Actualizar datos (ver instructivo).")
    if nivel == frescura.GRAVE:
        st.error(f"**Los datos no están al día.**\n\n{lineas}\n\n{cuerpo}")
    else:
        st.warning(f"**Algunos datos están atrasados.**\n\n{lineas}\n\n{cuerpo}")


def mostrar_avisos(avisos):
    for a in avisos or []:
        st.warning(f"⚠️ {a}")


def hsafe(s):
    """'$' como entidad HTML: se ve como $ y no dispara KaTeX dentro de HTML."""
    return str(s).replace("$", "&#36;")


def kpi(etiqueta, valor, chip_txt=None, chip_color=NEUTRO, sub=None, valor_color=TXT, tam=26):
    """Tarjeta de indicador estilo CEO. Usar dentro de `with col:` para grillas."""
    chip = f"<span style='color:{chip_color};font-size:12px;font-weight:700'>● {chip_txt}</span>" if chip_txt else ""
    subhtml = f"<div style='color:{MUT};font-size:12px;margin-top:3px'>{hsafe(sub)}</div>" if sub else ""
    html(f"<div style='{CARD}'>"
         f"<div style='color:{TXT2};font-size:13px'>{hsafe(etiqueta)}</div>"
         f"<div style='font-family:Montserrat,sans-serif;font-weight:800;font-size:{tam}px;color:{valor_color};margin:4px 0'>{hsafe(valor)}</div>"
         f"{chip}{subhtml}</div>")


def hero(etiqueta, valor, chip_txt=None, chip_color=NEUTRO, sub=None):
    """Tarjeta de número principal, grande, con pill a la derecha."""
    chip = (f"<span style='background:{chip_color}1F;color:{chip_color};font-size:12px;font-weight:700;"
            f"padding:4px 12px;border-radius:20px;white-space:nowrap'>{chip_txt}</span>") if chip_txt else ""
    subhtml = f"<div style='font-size:13px;color:{TXT2};margin-top:8px'>{hsafe(sub)}</div>" if sub else ""
    html(f"<div style='{CARD}'>"
         f"<div style='display:flex;justify-content:space-between;align-items:flex-start'>"
         f"<div><div style='color:{TXT2};font-size:13px'>{hsafe(etiqueta)}</div>"
         f"<div style='margin-top:4px'><span style='font-family:Montserrat,sans-serif;font-weight:800;font-size:38px;color:{TXT}'>{hsafe(valor)}</span></div></div>"
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
