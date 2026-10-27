"""Gráficos de la Vista de reunión (plotly). Funciones puras: reciben números y devuelven
una figura, para poder probarlas sin abrir la página.

Pensados para proyectar en un comité: pocos elementos, números grandes, colores de semáforo
y formato colombiano (punto de miles, coma decimal).
"""
import plotly.graph_objects as go

# Tema oscuro con vidrio (ver utils.py): acentos claros y textos claros sobre fondo transparente.
CIAN, VERDE, AMBAR, ROJO = "#38D9F0", "#5BE49B", "#F5B062", "#F87171"
TXT, TXT2, GRIS = "#EEF2F4", "#B4BCC5", "#8E98A3"
GRIS_CLARO = "rgba(255,255,255,0.10)"   # pistas de los medidores y líneas de la grilla
OSCURO = "#0E1214"                      # texto SOBRE las barras claras
FUENTE = "Raleway, Montserrat, sans-serif"
SEPARADORES = ",."  # decimal "," y miles "." (formato colombiano)


def color_estado(valor, meta_a_hoy, negativo_malo=False):
    """Verde / ámbar / rojo comparando con lo esperado A HOY (no con la meta del mes completo)."""
    if valor is None or not meta_a_hoy:
        return GRIS
    r = valor / meta_a_hoy
    if negativo_malo:
        return VERDE if r <= 0.5 else AMBAR if r <= 1.0 else ROJO
    return VERDE if r >= 0.95 else AMBAR if r >= 0.75 else ROJO


def texto_estado(valor, meta_a_hoy, negativo_malo=False):
    c = color_estado(valor, meta_a_hoy, negativo_malo)
    if c == GRIS:
        return "Sin meta"
    if negativo_malo:
        return {VERDE: "Bajo control", AMBAR: "Vigilar", ROJO: "Atención"}[c]
    return {VERDE: "En meta", AMBAR: "En camino", ROJO: "Rezagado"}[c]


def millones(v):
    """45.300.000 -> '45,3 M' (formato colombiano)."""
    txt = f"{v / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{txt} M"


def valor_corto(v, tipo="numero"):
    """Texto que va encima de cada columna: '45,3 M', '1.234', '60%'."""
    if v is None:
        return ""
    if tipo == "dinero":
        return millones(v)
    if tipo == "porcentaje":
        return f"{v * 100:.0f}%"
    return f"{v:,.0f}".replace(",", ".")


def partir_etiqueta(texto, largo=12):
    """Etiqueta larga del eje -> dos líneas equilibradas, cortando en el espacio más cercano a la
    mitad: 'Mary Alexandra Suárez' -> 'Mary Alexandra<br>Suárez'. Así los nombres completos (RRHH)
    no se montan unos sobre otros. Las de `largo` letras o menos quedan igual."""
    texto = str(texto)
    espacios = [i for i, c in enumerate(texto) if c == " "]
    if len(texto) <= largo or not espacios:
        return texto
    corte = min(espacios, key=lambda i: abs(i - len(texto) / 2))
    return texto[:corte] + "<br>" + texto[corte + 1:]


def pulir(fig, tipo="numero"):
    """Para las gráficas de barras de las páginas (pedido de los jefes, oct 2026):
    - el valor de cada columna escrito encima, sin tener que pasar el mouse;
    - sin zoom accidental al arrastrar (los ejes quedan fijos);
    - etiquetas del eje horizontales y con espacio, para que no se corten;
    - margen arriba de la columna más alta para que su número quepa.
    Las barras cuyo nombre empieza por "Meta" no llevan número (son la referencia)."""
    maximo, horizontal = 0, False
    for tr in fig.data:
        if tr.type != "bar":
            continue
        horizontal = tr.orientation == "h"
        valores = [v for v in (tr.x if horizontal else tr.y) if v is not None]
        maximo = max([maximo] + [float(v) for v in valores])
        if (tr.name or "").startswith("Meta"):
            continue
        tr.text = [valor_corto(v, tipo) for v in (tr.x if horizontal else tr.y)]
        # dentro de la punta de la columna si cabe (no choca con la línea de meta); afuera si es baja
        tr.textposition = "auto"
        tr.insidetextanchor = "end"
        tr.textangle = 0
        tr.insidetextfont = dict(size=11, color=OSCURO)
        tr.outsidetextfont = dict(size=11, color=TXT)
        tr.cliponaxis = False
    fig.update_layout(dragmode=False)
    fig.update_xaxes(fixedrange=True, automargin=True)
    fig.update_yaxes(fixedrange=True, automargin=True)
    if maximo > 0:
        if horizontal:
            fig.update_xaxes(range=[0, maximo * 1.25])
        else:
            fig.update_xaxes(tickangle=0)
            fig.update_yaxes(range=[0, maximo * 1.2])
            # etiquetas largas (p. ej. nombres completos en RRHH): en varias líneas, sin montarse
            # ojo: tr.x puede ser un arreglo de numpy/pandas ("x or []" falla con esos): se compara con None
            categorias = list(dict.fromkeys(str(c) for tr in fig.data if tr.type == "bar" and tr.x is not None
                                            for c in tr.x))
            if categorias and max(len(str(c)) for c in categorias) > 10:
                fig.update_xaxes(tickvals=categorias, ticktext=[partir_etiqueta(c) for c in categorias],
                                 tickfont=dict(size=11))
    return fig


def _base(fig, alto, arriba=50):
    margen = fig.layout.margin
    fig.update_layout(height=alto, separators=SEPARADORES,
                      margin=dict(l=margen.l if margen.l is not None else 25,
                                  r=margen.r if margen.r is not None else 25, t=arriba, b=margen.b if margen.b is not None else 15),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FUENTE, color=TXT, size=13))
    return fig


def _escala(valor, tipo):
    """Para dinero se muestran millones (más legible proyectado): 45.300.000 -> 45,3 M."""
    if valor is None:
        return None
    return valor / 1e6 if tipo == "dinero" else valor * 100 if tipo == "porcentaje" else valor


def medidor(titulo, valor, meta_mes, meta_a_hoy, tipo="numero"):
    """Velocímetro: la barra es lo logrado; la raya oscura, lo esperado a hoy; el fondo gris
    llega hasta la meta del mes. tipo: "dinero", "porcentaje" o "numero"."""
    v, m, h = _escala(valor, tipo), _escala(meta_mes, tipo), _escala(meta_a_hoy, tipo)
    tope = max(x for x in (v or 0, m or 0, h or 0, 1)) * 1.1
    sufijo = " M" if tipo == "dinero" else "%" if tipo == "porcentaje" else ""
    formato = ",.1f" if tipo == "dinero" else ",.0f"
    color = color_estado(valor, meta_a_hoy)
    gauge = dict(
        axis=dict(range=[0, tope], tickformat=",.0f", nticks=5, tickfont=dict(size=9, color=GRIS)),
        bar=dict(color=color, thickness=0.6),
        bgcolor="rgba(0,0,0,0)", borderwidth=0,
        steps=[dict(range=[0, m or 0], color=GRIS_CLARO)],
    )
    if h:
        gauge["threshold"] = dict(line=dict(color=TXT, width=4), thickness=0.85, value=h)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=v or 0,
        number=dict(suffix=sufijo, valueformat=formato, font=dict(size=22, color=TXT)),
        title=dict(text=f"<b>{titulo}</b><br><span style='font-size:11px;color:{color}'>"
                        f"● {texto_estado(valor, meta_a_hoy)}</span>", font=dict(size=13)),
        gauge=gauge,
    ))
    fig.update_layout(margin=dict(l=35, r=35, t=70, b=5))
    return _base(fig, 220, arriba=70)


def embudo(etapas):
    """etapas: [(nombre, valor)]. Muestra cuántos pasan y qué % de la etapa anterior."""
    etapas = [(n, v) for n, v in etapas if v is not None]
    textos = []
    for i, (_, v) in enumerate(etapas):
        previo = etapas[i - 1][1] if i else None
        pct = f"  ·  {v / previo * 100:.0f}%".replace(".", ",") if previo else ""
        textos.append(f"<b>{v:,.0f}</b>".replace(",", ".") + pct)
    fig = go.Figure(go.Funnel(
        y=[n for n, _ in etapas], x=[v for _, v in etapas],
        text=textos, textinfo="text",
        # dentro de las barras anchas (texto blanco); fuera de las angostas, donde no cabría
        textposition=["inside" if v >= 0.4 * etapas[0][1] else "outside" for _, v in etapas],
        textfont=dict(size=13, color=[OSCURO if v >= 0.4 * etapas[0][1] else TXT for _, v in etapas]),
        marker=dict(color=[CIAN, "#2CC3DC", "#4FB3C8", VERDE, "#3FC883"][:len(etapas)]),
        connector=dict(fillcolor=GRIS_CLARO, line=dict(width=0)),
    ))
    fig.update_yaxes(tickfont=dict(size=12))
    fig.update_layout(margin=dict(l=10, r=60, b=10))
    return _base(fig, 320, arriba=20)


def tendencia(titulo, periodos, valores, metas=None, reconstruidos=None, tipo="numero"):
    """Barras por mes con la línea de meta. Los meses reconstruidos van en un tono más claro."""
    reconstruidos = reconstruidos or [False] * len(periodos)
    vals = [_escala(v, tipo) for v in valores]
    fig = go.Figure(go.Bar(
        x=periodos, y=vals, name=titulo,
        # el título ya dice "(millones)": en columnas angostas basta la cifra ("52,7"), siempre horizontal
        text=[(f"{v / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") if v is not None else "")
              if tipo == "dinero" else valor_corto(v, tipo) for v in valores],
        textposition="auto", insidetextanchor="end", textangle=0,
        insidetextfont=dict(size=10, color=OSCURO), outsidetextfont=dict(size=10, color=TXT), cliponaxis=False,
        marker=dict(color=[("rgba(56,217,240,0.35)" if r else CIAN) for r in reconstruidos]),
        hovertemplate="%{x}: %{y:,.1f}" + (" M" if tipo == "dinero" else "") + "<extra></extra>",
    ))
    if metas and any(x is not None for x in metas):
        fig.add_trace(go.Scatter(x=periodos, y=[_escala(m, tipo) for m in metas], name="Meta",
                                 mode="lines+markers", line=dict(color=TXT, dash="dash", width=2)))
    tope = max([x for x in vals if x is not None] + [_escala(m, tipo) for m in (metas or []) if m is not None] + [1])
    fig.update_layout(title=dict(text=f"<b>{titulo}</b>" + (" (millones)" if tipo == "dinero" else ""),
                                 font=dict(size=13)),
                      showlegend=False, dragmode=False,
                      yaxis=dict(gridcolor=GRIS_CLARO, range=[0, tope * 1.3], tickfont=dict(size=10), fixedrange=True),
                      xaxis=dict(tickfont=dict(size=10), tickangle=0, fixedrange=True))
    fig.update_layout(margin=dict(l=35, r=10, b=30))
    return _base(fig, 240, arriba=40)


def cascada_resultado(recaudo, cuotas_iniciales, gasto_fijo, auteco):
    """Cómo se llega al resultado objetivo del mes: + recaudo + CI − gasto fijo − Auteco."""
    pasos = [("Recaudo<br>(meta)", recaudo or 0), ("Cuotas iniciales<br>(meta)", cuotas_iniciales or 0),
             ("Gasto<br>fijo", -(gasto_fijo or 0)), ("Pago<br>Auteco", -(auteco or 0))]
    resultado = sum(v for _, v in pasos)
    valores = [v for _, v in pasos] + [resultado]

    # rango con aire arriba y abajo para que ninguna etiqueta exterior quede cortada
    acumulado, techo, piso = 0, 0, 0
    for _, v in pasos:
        acumulado += v
        techo, piso = max(techo, acumulado), min(piso, acumulado)
    piso = min(piso, resultado)
    span = (techo - piso) or 1
    # barras altas: etiqueta adentro (blanca); barras chicas: afuera, donde sí cabe
    adentro = [abs(v) >= 0.15 * span for v in valores]

    fig = go.Figure(go.Waterfall(
        x=[n for n, _ in pasos] + ["Resultado"], y=[v / 1e6 for v in valores],
        measure=["relative"] * len(pasos) + ["total"],
        text=[millones(v) for v in valores],
        textposition=["inside" if a else "outside" for a in adentro],
        insidetextfont=dict(color=OSCURO, size=12), outsidetextfont=dict(color=TXT, size=12),
        cliponaxis=False,
        increasing=dict(marker=dict(color=VERDE)), decreasing=dict(marker=dict(color=ROJO)),
        totals=dict(marker=dict(color=CIAN if resultado >= 0 else ROJO)),
        connector=dict(line=dict(color=GRIS, width=1, dash="dot")),
    ))
    fig.add_hline(y=0, line=dict(color=TXT2, width=1))
    fig.update_layout(title=dict(text="<b>Resultado objetivo del mes</b> (millones)", font=dict(size=13)),
                      showlegend=False,
                      yaxis=dict(gridcolor=GRIS_CLARO, tickfont=dict(size=10),
                                 range=[(piso - 0.18 * span) / 1e6, (techo + 0.15 * span) / 1e6]),
                      xaxis=dict(tickfont=dict(size=11)))
    fig.update_layout(margin=dict(l=45, r=15, b=45))
    return _base(fig, 360, arriba=45)
