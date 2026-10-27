"""Utilidades compartidas del BSC de RODDOS."""
import os
import base64
import streamlit as st

# Identidad de marca RODDOS — tema OSCURO con efecto vidrio. Acentos claros para buen
# contraste sobre fondo oscuro. Los acentos van en hex de 6 dígitos: hero() y otras
# piezas les agregan transparencia al final (p. ej. f"{color}1F").
NEGRO = "#0B0E10"
CIAN = "#38D9F0"
VERDE = "#5BE49B"
AMBAR = "#F5B062"
ROJO = "#F87171"
NEUTRO = "#8E98A3"

TXT = "#EEF2F4"     # texto principal
TXT2 = "#B4BCC5"    # texto secundario
MUT = "#8E98A3"     # muted / captions
CARD_BG = "#1C2225B8"   # vidrio (con transparencia)
BORDE = "#FFFFFF1F"
TRACK = "#FFFFFF1A"     # fondo de barras

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
    color: #EEF2F4;
}

/* ---------- Fondo: dos capas, igual que la otra app de RODDOS con liquid glass ----------
   1) ::before = el SÍMBOLO de anillos del logo (static/roddos_anillos.png: arcos verdes y cian),
      ampliado y desenfocado, saliéndose por la derecha: el círculo azul pequeño del centro (en el
      46,8% / 50,8% del símbolo, radio 9,6%) queda justo antes del borde.
   2) ::after  = el logo completo de RODDOS (static/roddos_fondo.png), muy sutil y grande, cruzando la
      pantalla de izquierda a derecha (la "S" se sale por la derecha).
   Tamaños en vh/vw para que se vea igual en cualquier pantalla. */
.stApp { background: #0E1214; }
.stApp::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: url("/app/static/roddos_anillos.png") no-repeat;
    background-size: 92vh 92vh;
    /* x: borde derecho del círculo pequeño a 1,5vw del borde  ->  98,5vw - 0,096·92vh - 0,468·92vh
       y: centro del símbolo al 40% del alto                   ->  40vh - 0,508·92vh */
    background-position: calc(98.5vw - 51.9vh) -6.7vh;
    filter: blur(10px) saturate(0.85) brightness(0.7);
}
.stApp::after {
    content: ""; position: fixed; pointer-events: none; z-index: 0;
    left: 2vw; width: 112vw; height: 38vw;                 /* 112vw: la "S" queda fuera de la pantalla */
    bottom: calc(11vh - 10.6vw);                          /* la base de las letras al ~89% del alto */
    background: url("/app/static/roddos_fondo.png") no-repeat left bottom / contain;
    opacity: 0.55; filter: blur(1.5px);
}
[data-testid="stAppViewContainer"] { position: relative; z-index: 1; background: transparent; }
[data-testid="stHeader"], [data-testid="stMain"], [data-testid="stBottom"] > div { background: transparent; }

/* Más aire y ancho controlado */
[data-testid="stMainBlockContainer"] { padding-top: 1.6rem; max-width: 1180px; }

/* ---------- Vidrio: tarjetas de Streamlit y expanders ----------
   Streamlit 1.64 no marca los contenedores con borde: cada uno lleva key="vidrio_..." y
   Streamlit le pone la clase st-key-vidrio_... (el selector de antes ya no existía). */
[class*="st-key-vidrio"] {
    background: linear-gradient(145deg, rgba(255,255,255,0.11) 0%, rgba(255,255,255,0.035) 45%, rgba(255,255,255,0.065) 100%), rgba(26,31,33,0.36);
    backdrop-filter: blur(24px) saturate(175%);
    -webkit-backdrop-filter: blur(24px) saturate(175%);
    border: 1px solid rgba(255,255,255,0.16) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -1px 0 rgba(0,0,0,0.25), 0 14px 40px rgba(0,0,0,0.38);
    border-radius: 26px; position: relative;
}
/* tarjetas grandes (calendario de la Agenda): aire interior */
[class*="st-key-vidrio_agenda"] { padding: 18px 18px 26px; }
/* reflejo suave en la esquina superior izquierda (el "brillo" del vidrio líquido) */
[class*="st-key-vidrio"]::before {
    content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
    background: radial-gradient(120% 70% at 0% 0%, rgba(255,255,255,0.10), transparent 55%);
}
/* Solo en las tarjetas de indicadores: cifra grande y título pequeño en mayúsculas */
[class*="st-key-vidrio_kpi"] h3 {
    color: #EEF2F4; font-size: 1.85rem; font-weight: 800; margin: 0.15rem 0 0.35rem 0;
}
[class*="st-key-vidrio_kpi"] [data-testid="stCaptionContainer"]:first-child p {
    text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.68rem; color: #8E98A3; font-weight: 600;
}
[data-testid="stExpander"] details {
    background: linear-gradient(145deg, rgba(255,255,255,0.11) 0%, rgba(255,255,255,0.035) 45%, rgba(255,255,255,0.065) 100%), rgba(26,31,33,0.36);
    backdrop-filter: blur(24px) saturate(175%);
    -webkit-backdrop-filter: blur(24px) saturate(175%);
    border: 1px solid rgba(255,255,255,0.16) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -1px 0 rgba(0,0,0,0.25), 0 14px 40px rgba(0,0,0,0.38);
    border-radius: 20px;
}

/* ---------- Menú lateral: panel de vidrio flotante ---------- */
[data-testid="stSidebar"] { background: transparent; border-right: none; }
[data-testid="stSidebarContent"] {
    background: linear-gradient(145deg, rgba(255,255,255,0.11) 0%, rgba(255,255,255,0.035) 45%, rgba(255,255,255,0.065) 100%), rgba(26,31,33,0.36);
    backdrop-filter: blur(24px) saturate(175%);
    -webkit-backdrop-filter: blur(24px) saturate(175%);
    border: 1px solid rgba(255,255,255,0.16) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -1px 0 rgba(0,0,0,0.25), 0 14px 40px rgba(0,0,0,0.38);
    border-radius: 26px;
    margin: 14px; height: calc(100% - 28px);
    width: calc(100% - 28px); box-sizing: border-box;   /* margen a ambos lados, sin salirse */
}
[data-testid="stSidebarNav"] a { border-radius: 12px; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: #5BE49B26; }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: #EEF2F4; font-weight: 700; }

/* ---------- Acentos ---------- */
[data-testid="stProgress"] div[role="progressbar"] > div { background-color: #5BE49B; }
[data-testid="stSegmentedControl"] button[aria-checked="true"] {
    background: #5BE49B26; border-color: #5BE49B; color: #5BE49B;
}
/* Gráficos: cada uno en su tarjeta de vidrio líquido */
[data-testid="stPlotlyChart"] {
    background: linear-gradient(145deg, rgba(255,255,255,0.11) 0%, rgba(255,255,255,0.035) 45%, rgba(255,255,255,0.065) 100%), rgba(26,31,33,0.36);
    backdrop-filter: blur(24px) saturate(175%);
    -webkit-backdrop-filter: blur(24px) saturate(175%);
    border: 1px solid rgba(255,255,255,0.16);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -1px 0 rgba(0,0,0,0.25), 0 14px 40px rgba(0,0,0,0.38);
    border-radius: 24px; padding: 0; overflow: hidden; margin-bottom: 6px;   /* sin padding: evita el scroll */
}
/* sin la barra de herramientas de Plotly (zoom, mover...): es un tablero de consulta */
.modebar-container { display: none !important; }

/* ---------- Avisos rojos / amarillos / azules en vidrio líquido ----------
   Base oscura y desenfoque DEBAJO del color del aviso: el texto se lee limpio aunque detrás pasen
   los anillos del fondo. */
[data-testid="stAlert"] {
    background: rgba(14,18,20,0.66);
    backdrop-filter: blur(24px) saturate(160%);
    -webkit-backdrop-filter: blur(24px) saturate(160%);
    border-radius: 22px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 14px 40px rgba(0,0,0,0.38);
}
[data-testid="stAlertContainer"] { border-radius: 22px; border: 1px solid rgba(255,255,255,0.12); }
</style>
"""


def estilo_roddos():
    """Inyecta la identidad visual de RODDOS. Llamar tras set_page_config."""
    st.markdown(_ESTILO, unsafe_allow_html=True)


def encabezado(subtitulo=""):
    """Cabecera de vidrio con el logo de RODDOS (blanco) y el subtítulo de la página."""
    img = (f"<img src='data:image/png;base64,{LOGO_B64}' style='height:56px;display:block'/>"
           if LOGO_B64 else
           "<span style='color:#fff;font-family:Montserrat,sans-serif;font-weight:800;font-size:34px'>RODDOS</span>")
    sub = (f"<div style='color:{TXT2};font-size:14px;margin-top:8px;font-family:Montserrat,sans-serif'>{subtitulo}</div>"
           if subtitulo else "")
    st.markdown(f"<div style='{CARD}padding:20px 26px;margin-bottom:18px'>{img}{sub}</div>", unsafe_allow_html=True)


# Tarjeta de vidrio líquido para el HTML propio (kpi, hero, tarjetas de las páginas)
CARD = ("background:linear-gradient(145deg,rgba(255,255,255,0.11) 0%,rgba(255,255,255,0.035) 45%,"
        "rgba(255,255,255,0.065) 100%),rgba(26,31,33,0.36);"
        "backdrop-filter:blur(24px) saturate(175%);-webkit-backdrop-filter:blur(24px) saturate(175%);"
        "border:1px solid rgba(255,255,255,0.16);border-radius:24px;padding:18px 20px;"
        "box-shadow:inset 0 1px 0 rgba(255,255,255,0.28),inset 0 -1px 0 rgba(0,0,0,0.25),0 14px 40px rgba(0,0,0,0.38);"
        "margin-bottom:14px;")


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


def sincronizar_sharepoint(mostrar_alertas=True, forzar=False):
    """Trae de SharePoint los archivos que cambiaron (si la conexión está configurada; si no,
    no hace nada). Va al inicio de cada página, ANTES de leer los datos. Ver sharepoint.py."""
    import sharepoint

    if sharepoint.config() is None:
        return None
    with st.spinner("Revisando cambios en SharePoint…"):
        estado = sharepoint.sincronizar_si_toca(forzar=forzar)
    if mostrar_alertas and estado:
        for _, archivo, _ in sharepoint.rechazados(estado):
            st.warning(f"⚠️ El archivo **{archivo}** en SharePoint tiene errores y no se cargó: se muestra la "
                       "última versión buena. El detalle está en 📤 Actualizar datos.")
        if estado.get("_error"):
            st.warning(f"⚠️ No se pudo revisar SharePoint ({estado['_error']}). Se muestran los últimos datos cargados.")
    return estado


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
    """Texto plano listo para meter en HTML: escapa <, > y & (un nombre como "Cliente A & B" o una
    nota "saldo < 0" ya no rompen la tarjeta) y pone '$' como entidad para que no dispare KaTeX."""
    import html as _html

    return _html.escape(str(s), quote=False).replace("$", "&#36;")


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
    "financiera": "#7FB3D5",
    "cliente": "#5BE49B",
    "procesos": "#F5B062",
    "aprendizaje": "#B794F4",
    "ok": "#5BE49B",
    "alerta": "#F5B062",
    "critico": "#F87171",
    "neutro": "#8E98A3",
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
