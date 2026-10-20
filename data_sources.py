"""Lectura de los Excel reales de RODDOS.

Arquitectura: RODDOS se publica en Streamlit Community Cloud, que no tiene
acceso a OneDrive/SharePoint (ni lectura en vivo ni persistencia entre
reinicios del servidor). Por eso la actualización es 100% por carga manual:
la página "Actualizar datos" (pages/0_Actualizar_Datos.py) sube cada Excel,
lo guarda en bsc-streamlit/data_raw/*.xlsx, y estas funciones leen de ahí.
Cada función lee el archivo tal como quedó en la última carga — no es lectura
en vivo del archivo real. Cada carga también se respalda en MongoDB (respaldo.py)
y, si el servidor reinició y data_raw/ quedó vacío, se recupera al arrancar.

Las celdas leídas están ancladas a la estructura de hoja tal como existe hoy
(hojas "Dashboard" de cada archivo). Si esas hojas cambian de layout, esto
se rompe de forma visible (valores None), no de forma silenciosa.
"""
import os
import datetime
import pandas as pd
import openpyxl
import streamlit as st
from pymongo.errors import PyMongoError

import formatos
import respaldo

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_raw")
F_INVENTARIO = os.path.join(RAW_DIR, "Inventario_2026.xlsx")
F_RECAUDO = os.path.join(RAW_DIR, "Proyeccion_Recaudo.xlsx")
F_CONCILIACION = os.path.join(RAW_DIR, "Cruce_SISMO_Wava.xlsx")
F_TESORERIA = os.path.join(RAW_DIR, "Flujo_Pagos_Deudas.xlsx")
F_RRHH = os.path.join(RAW_DIR, "Control_RRHH_Nomina_RODDOS_2026.xlsx")
F_EMBUDO = os.path.join(RAW_DIR, "Embudo_Comercial_RODDOS.xlsx")
F_METAS = os.path.join(RAW_DIR, "Metas_RODDOS.xlsx")
F_COBRANZA = os.path.join(RAW_DIR, "Cobranza_Semanal.xlsx")
ARCHIVOS = [F_INVENTARIO, F_RECAUDO, F_CONCILIACION, F_TESORERIA, F_RRHH, F_EMBUDO, F_METAS, F_COBRANZA]


@st.cache_resource
def db_respaldo():
    try:
        cfg = st.secrets["mongo"]
    except (FileNotFoundError, KeyError):
        return None
    if "PEGA_AQUI" in cfg["uri"]:
        return None
    return respaldo.conectar(cfg["uri"], cfg["db"])


@st.cache_resource
def restaurar_desde_respaldo():
    db = db_respaldo()
    if db is None:
        return []
    return respaldo.restaurar_faltantes(db, ARCHIVOS)


try:
    restaurar_desde_respaldo()
except PyMongoError as e:
    st.warning(f"No se pudo recuperar el respaldo en la nube: {e}")

def _filas_tabla(ws, fila_ini, col_clave, es_fila=lambda v: v is not None):
    """Números de fila de una tabla que empieza en `fila_ini`, sin tope fijo.

    Recorre hacia abajo mientras la celda de `col_clave` cumpla `es_fila` y se
    detiene en la primera que no (fin de la tabla). Así, cuando el Excel agrega
    semanas, días o meses nuevos, el tablero los lee sin tocar el código.
    """
    filas = []
    for r in range(fila_ini, ws.max_row + 1):
        if not es_fila(ws[f"{col_clave}{r}"].value):
            break
        filas.append(r)
    return filas


def faltantes(*rutas):
    """Nombres de los archivos de `rutas` que todavía no se han cargado en data_raw/."""
    return [os.path.basename(r) for r in rutas if not os.path.exists(r)]


MESES_ABR = formatos.MESES_ABR


def _indice(headers, nombre, por_defecto=None):
    """Posición de una columna por su encabezado (tolerante a espacios sobrantes)."""
    limpios = [h.strip() if isinstance(h, str) else h for h in headers]
    return limpios.index(nombre) if nombre in limpios else por_defecto


@st.cache_data(ttl=600)
def leer_inventario(ruta=None):
    wb = openpyxl.load_workbook(ruta or F_INVENTARIO, data_only=True)
    ws = wb["Dashboard"]

    def g(coord):
        # vacía -> 0 (así funcionaba siempre). Un error de Excel (#REF!, #N/A...) o un texto -> None:
        # el tablero muestra "—" en vez de un número falso. Las celdas críticas las exige el validador.
        v = ws[coord].value
        if v is None:
            return 0
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    # K2: "Actualizado: 09/10/2026" (texto) o una fecha de Excel
    k2 = ws["K2"].value
    actualizado_fecha = formatos.parse_actualizado(k2)
    actualizado_txt = k2 if isinstance(k2, str) else (f"Actualizado: {actualizado_fecha:%d/%m/%Y}" if actualizado_fecha else "")

    hoy = {
        "actualizado": actualizado_txt,
        "actualizado_fecha": actualizado_fecha,
        "vendidas_mes": g("B7"), "activadas_mes": g("D7"), "ci_mes": g("F7"),
        "plan_separe_no_activados": g("H7"), "pendientes_activar_total": g("J7"),
        "negocios_hoy": g("B12"), "ci_completa_hoy": g("D12"), "ci_parcial_hoy": g("F12"),
        "sin_abono_hoy": g("H12"), "pendientes_factura": g("J12"),
        "disp_raider": g("B18"), "disp_sport": g("D18"), "disp_apache": g("F18"),
        "disp_total": g("H18"), "pendientes_entrega": g("J18"),
        "facturacion_acum_anio": g("B23"), "motos_facturadas_anio": g("D23"),
        "ci_recaudadas_anio": g("F23"),
    }
    # resumen mensual: desde la fila 27 hacia abajo, un mes por fila (sin tope: crece con el año).
    # columnas N/O (fact), Q/R (ci), T/U/V/W (vend/act/fact). Se omite una eventual fila de TOTAL.
    meses = []
    for r in _filas_tabla(ws, 27, "N"):
        mes_lbl = ws[f"N{r}"].value
        if str(mes_lbl).strip().lower().startswith("total"):
            continue
        fact = ws[f"O{r}"].value
        ci = ws[f"R{r}"].value
        vend = ws[f"U{r}"].value
        act = ws[f"V{r}"].value
        facturadas = ws[f"W{r}"].value
        meses.append(dict(
            mes=mes_lbl,
            facturacion=fact if isinstance(fact, (int, float)) else None,
            cuotas_iniciales=ci if isinstance(ci, (int, float)) else None,
            vendidas=vend if isinstance(vend, (int, float)) else None,
            activadas=act if isinstance(act, (int, float)) else None,
            facturadas=facturadas if isinstance(facturadas, (int, float)) else None,
        ))
    df_mensual = pd.DataFrame(meses)

    # inventario motos: conteo por estado/ubicacion
    ws2 = wb["Inventario motos"]
    header = [c.value for c in ws2[1]]
    idx_placa = _indice(header, "Placa", 0)
    idx_estado = _indice(header, "Estado")
    idx_ubic = _indice(header, "Ubicación")
    disponibles = 0
    en_site = 0
    for row in ws2.iter_rows(min_row=2, values_only=True):
        if row[idx_placa] is None:
            continue
        if row[idx_estado] == "Disponible":
            disponibles += 1
        if row[idx_ubic] == "Site":
            en_site += 1

    plan_separe_detalle = []
    ws3 = wb["Plan separe"]
    # localizar encabezados reales (la hoja tiene un bloque de texto arriba)
    header_row = None
    for r in range(1, 15):
        vals = [ws3.cell(row=r, column=c).value for c in range(2, 12)]
        if "Crédito" in vals or "Cliente" in vals:
            header_row = r
            break
    if header_row:
        hdrs = [ws3.cell(row=header_row, column=c).value for c in range(2, 12)]
        for r in range(header_row + 1, ws3.max_row + 1):
            vals = [ws3.cell(row=r, column=c).value for c in range(2, 12)]
            if all(v is None for v in vals):
                continue
            plan_separe_detalle.append(dict(zip(hdrs, vals)))

    return dict(hoy=hoy, mensual=df_mensual, motos_disponibles_raw=disponibles,
                motos_en_site=en_site, plan_separe=plan_separe_detalle)


@st.cache_data(ttl=600)
def leer_recaudo(ruta=None):
    wb = openpyxl.load_workbook(ruta or F_RECAUDO, data_only=True)
    wsD = wb["Dashboard"]

    def g(coord):
        v = wsD[coord].value
        return v if v is not None else 0

    dashboard = dict(
        cuotas_prog_mes=g("B5"), monto_prog_mes=g("D5"), saldo_a_cobrar=g("F5"),
        meta_pactada=g("H5"), ingreso_mes_acum=g("B8"), falta_meta=g("D8"),
        pct_cumplimiento=g("F8"), mora_vencida_activos=g("B11"),
        creditos_activos_mora=g("D11"), provision_estimada=g("F11"),
    )
    # serie diaria de recaudo (P10:S..), sin tope fijo: cubre meses de 31 días
    diario = []
    for r in _filas_tabla(wsD, 10, "P"):
        fecha = wsD[f"P{r}"].value
        ingreso = wsD[f"Q{r}"].value
        acumulado = wsD[f"R{r}"].value
        diario.append(dict(fecha=fecha, ingreso_dia=ingreso if isinstance(ingreso, (int, float)) else None,
                            acumulado_mes=acumulado if isinstance(acumulado, (int, float)) else None))
    df_diario = pd.DataFrame(diario)

    # tablero semanal (fila 10 = encabezados, datos desde la fila 11). Se leen todas
    # las filas "Sem NN" seguidas, sin importar cuántas semanas tenga el archivo.
    wsS = wb["Resumen Semanal"]
    semanas = []
    for r in _filas_tabla(wsS, 11, "A", es_fila=lambda v: str(v or "").strip().startswith("Sem")):
        sem = wsS.cell(row=r, column=1).value
        rango = wsS.cell(row=r, column=2).value
        cuotas = wsS.cell(row=r, column=3).value
        meta = wsS.cell(row=r, column=4).value
        ingreso_real = wsS.cell(row=r, column=5).value
        pagado_su_sem = wsS.cell(row=r, column=6).value
        pct_oport = wsS.cell(row=r, column=7).value
        pendiente = wsS.cell(row=r, column=9).value
        semanas.append(dict(semana=sem, rango=rango, cuotas=cuotas, meta=meta,
                             ingreso_real=ingreso_real, pagado_en_semana=pagado_su_sem,
                             pct_cumplimiento_oportuno=pct_oport, pendiente_por_cobrar=pendiente))
    df_semanal = pd.DataFrame(semanas)

    # detalle de cuotas (fuente mas granular: pagos y vencidas por dia)
    # fila 1 = titulo de la hoja, fila 2 = encabezados reales, datos desde fila 3
    wsC = wb["Detalle Cuotas"]
    headers = [h.strip() if isinstance(h, str) else h for h in (c.value for c in wsC[2])]
    idx_codigo = _indice(headers, "Cód. crédito", 4)  # por nombre: no depende del orden de columnas
    rows = []
    for row in wsC.iter_rows(min_row=3, values_only=True):
        if row[idx_codigo] is None:
            continue
        rows.append(row)
    df_cuotas = pd.DataFrame(rows, columns=headers)

    return dict(dashboard=dashboard, diario=df_diario, semanal=df_semanal, cuotas=df_cuotas)


MESES_ABR_INV = formatos.MESES_ABR_INV
_parse_fecha_corte = formatos.parse_fecha_corte  # se conserva el nombre por compatibilidad


@st.cache_data(ttl=600)
def leer_tesoreria(ruta=None):
    wb = openpyxl.load_workbook(ruta or F_TESORERIA, data_only=True)
    ws = wb["Tablero mes"]

    def g(coord):
        v = ws[coord].value
        return v if v is not None else 0

    j4 = ws["J4"].value
    corte_txt = j4 if isinstance(j4, str) else (f"{j4:%d/%m/%Y}" if isinstance(j4, datetime.date) else "")
    mes_control = ws["C4"].value
    dashboard = dict(
        mes_control=mes_control if isinstance(mes_control, datetime.datetime) else None,
        corte_txt=corte_txt,
        corte_fecha=formatos.parse_fecha_corte(j4),
        presupuesto_mes=g("B8"), ejecutado_mes=g("E8"),
        ingreso_real_mes=g("H8"), pct_cumplimiento_meta=g("K8"),
        caja_disponible_total=g("E14"), resultado_mes=g("B14"),
        mayor_egreso_dia=g("H14"), egresos_por_clasificar=g("K14"),
    )

    wsE = wb["Base real egresos"]
    headersE = [c.value for c in wsE[1]]
    rowsE = [row for row in wsE.iter_rows(min_row=2, values_only=True) if row[0] is not None]
    dfE = pd.DataFrame(rowsE, columns=headersE)
    dfE["Fecha"] = pd.to_datetime(dfE["Fecha"], errors="coerce")
    # solo movimientos reales: se descartan duplicados, reversados y traslados entre cuentas propias
    egresos = dfE[(dfE["Es duplicado"] == "No") & (dfE["Es reversado"] == "No") & (dfE["Es traslado"] == "No")].copy()

    wsI = wb["Base real ingresos"]
    headersI = [c.value for c in wsI[1]]
    rowsI = [row for row in wsI.iter_rows(min_row=2, values_only=True) if row[0] is not None]
    dfI = pd.DataFrame(rowsI, columns=headersI)
    dfI["Fecha"] = pd.to_datetime(dfI["Fecha"], errors="coerce")
    ingresos = dfI[(dfI["Es traslado"] == "No") & (dfI["Es reverso de egreso"] == "No")].copy()

    # pago a Auteco del mes: saldo pendiente de las facturas cuyo "Mes de pago" cae en el mes de control
    mes_ctrl = dashboard["mes_control"]
    pago_auteco_mes = 0.0
    if "Facturas Auteco" in wb.sheetnames and mes_ctrl:
        wsA = wb["Facturas Auteco"]
        headersA = [c.value for c in wsA[2]]
        idxA = {h: i for i, h in enumerate(headersA)}
        for row in wsA.iter_rows(min_row=3, values_only=True):
            mp = row[idxA.get("Mes de pago", -1)] if "Mes de pago" in idxA else None
            if isinstance(mp, datetime.datetime) and mp.year == mes_ctrl.year and mp.month == mes_ctrl.month:
                saldo = row[idxA.get("Saldo pendiente ($)", -1)] if "Saldo pendiente ($)" in idxA else None
                pago_auteco_mes += saldo or 0
    dashboard["pago_auteco_mes"] = pago_auteco_mes

    return dict(dashboard=dashboard, egresos=egresos, ingresos=ingresos)


def _tabla_desde(ws, col_nombre, header_row=3, data_start=4):
    headers = [c.value for c in ws[header_row]]
    filas = []
    for row in ws.iter_rows(min_row=data_start, values_only=True):
        if row[0] is None and row[1] is None:
            continue
        d = dict(zip(headers, row))
        if d.get(col_nombre) in (None, "TOTAL"):
            continue
        filas.append(d)
    return pd.DataFrame(filas)


@st.cache_data(ttl=600)
def leer_rrhh(ruta=None):
    wb = openpyxl.load_workbook(ruta or F_RRHH, data_only=True)

    empleados = _tabla_desde(wb["Empleados"], "Nombre completo")
    nomina = _tabla_desde(wb["NominaMensual"], "Empleado")
    vacaciones = _tabla_desde(wb["Vacaciones"], "Empleado")

    # celdas de fecha vacias en Excel a veces se leen como datetime.time(0,0) en vez de None
    for df in (empleados, vacaciones):
        if "Fecha ingreso" in df.columns:
            df["Fecha ingreso"] = df["Fecha ingreso"].apply(
                lambda v: v if isinstance(v, datetime.datetime) else None
            )

    return dict(
        headcount=len(empleados),
        empleados=empleados,
        nomina=nomina,
        costo_total_empresa_mes=float(nomina["COSTO TOTAL EMPRESA/MES"].sum()) if not nomina.empty else 0,
        neto_legal_total=float(nomina["NETO LEGAL a pagar"].sum()) if not nomina.empty else 0,
        brecha_legal_total=float(nomina["Brecha vs. legal"].sum()) if not nomina.empty else 0,
        vacaciones=vacaciones,
        dias_pendientes_total=float(vacaciones["Días pendientes"].sum()) if not vacaciones.empty else 0,
        provision_vacaciones_total=float(vacaciones["Provisión pendiente estimada"].sum()) if not vacaciones.empty else 0,
    )


@st.cache_data(ttl=600)
def leer_embudo(ruta=None):
    """Lee Embudo_Comercial_RODDOS.xlsx (misma estructura que la Plantilla_Embudo_Comercial.xlsx
    descargable). Descarta la fila de ejemplo y cualquier fila sin 'Fecha lead'."""
    ruta = ruta or F_EMBUDO
    if not os.path.exists(ruta):
        return pd.DataFrame()
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb["Embudo_Diario"]
    headers = [h.strip() if isinstance(h, str) else h for h in (c.value for c in ws[1])]
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(headers, row))
        if d.get("Fecha lead") is None:
            continue
        if isinstance(d.get("Notas"), str) and "fila de ejemplo" in d["Notas"].lower():
            continue
        if formatos.fila_embudo_vacia(d):
            continue  # solo trae la fecha: no es un lead
        filas.append(d)
    df = pd.DataFrame(filas)
    for col in ["Fecha lead", "Fecha formulario", "Fecha decision", "Fecha agenda visita"]:
        if col in df.columns:
            # celda por celda y con el día primero: '05/09/2026' es 5 de septiembre
            df[col] = pd.to_datetime(df[col].map(formatos.parse_fecha_texto), errors="coerce")
    return df


@st.cache_data(ttl=600)
def leer_metas(referencia=None, ruta=None):
    """Lee la fila de Metas_RODDOS.xlsx que corresponde al mes de 'referencia'
    (por defecto, hoy). Si no hay fila para ese mes exacto, usa la más
    reciente que sea <= esa fecha (evita que el tablero se rompa si
    todavia no se ha diligenciado la fila del mes en curso).
    Las filas cuyo 'Mes' no es una fecha real se ignoran (el validador ya las rechaza)."""
    ruta = ruta or F_METAS
    if not os.path.exists(ruta):
        return None
    ref = referencia or formatos.hoy_colombia()
    if isinstance(ref, datetime.datetime):
        ref = ref.date()
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb["Metas"]
    fila_h = formatos.fila_encabezado(ws, "Mes")
    headers = [h.strip() if isinstance(h, str) else h for h in (c.value for c in ws[fila_h])]
    filas = []
    for row in ws.iter_rows(min_row=fila_h + 1, values_only=True):
        d = dict(zip(headers, row))
        mes = d.get("Mes")
        if isinstance(mes, datetime.datetime):
            d["Mes"] = mes.date()
        elif not isinstance(mes, datetime.date):
            continue
        filas.append(d)
    if not filas:
        return None
    candidatas = [f for f in filas if f["Mes"] <= ref] or filas
    fila = max(candidatas, key=lambda f: f["Mes"])
    return dict(
        mes=fila["Mes"],
        ventas=fila["Meta ventas (unidades)"],
        pct_aprobacion=fila["Meta % aprobación crédito"],
        pct_agendas=fila["Meta % cumplimiento agendas"],
        pct_mora_tope=fila["Meta % mora tope"],
        ci_dinero=fila["Meta ingreso cuotas iniciales ($)"],
        gasto_fijo=fila["Gasto fijo mensual ($)"],
    )


@st.cache_data(ttl=600)
def leer_cobranza_semanal(ruta=None):
    """Lee Cobranza_Semanal.xlsx (seguimiento semanal de cobranza).
    Toma los totales de la hoja 'Dashboard'; si una celda no está recalculada
    (None), la calcula desde las hojas de detalle para no quedar en blanco.
    'Pagada' acepta casilla de verificación o texto ('Sí', 'X'...), como dice el instructivo."""
    ruta = ruta or F_COBRANZA
    if not os.path.exists(ruta):
        return None
    wb = openpyxl.load_workbook(ruta, data_only=True)
    if "Dashboard" not in wb.sheetnames:
        return None
    d = wb["Dashboard"]

    def num(coord):
        v = d[coord].value
        return v if isinstance(v, (int, float)) else None

    hoja_sem = "Cuotas de la semana" if "Cuotas de la semana" in wb.sheetnames else None
    hoja_ven = "Cuotas vencidas" if "Cuotas vencidas" in wb.sheetnames else None

    def _valores(hoja, col_valor="Valor cuota a pagar esta semana"):
        if hoja is None:
            return []
        ws = wb[hoja]
        headers = [c.value for c in ws[1]]
        idx = {h: i for i, h in enumerate(headers)}
        cv = idx.get("Valor cuota a pagar esta semana", idx.get("Valor cuota vencida"))
        cp = idx.get("Pagada")
        filas = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if cv is None or row[cv] is None:
                continue
            filas.append((row[cv], formatos.es_si(row[cp]) if cp is not None else False))
        return filas

    sem = _valores(hoja_sem)
    ven = _valores(hoja_ven)

    def _sum(filas):
        return float(sum(v for v, _ in filas if isinstance(v, (int, float))))

    def _sum_pag(filas):
        return float(sum(v for v, p in filas if p and isinstance(v, (int, float))))

    potencial_semana = num("B4")
    potencial_vencidas = num("C4")
    if potencial_semana is None:
        potencial_semana = _sum(sem)
    if potencial_vencidas is None:
        potencial_vencidas = _sum(ven)
    potencial_total = num("D4")
    if potencial_total is None:
        potencial_total = potencial_semana + potencial_vencidas

    n_cuotas_semana = num("E4") if num("E4") is not None else len(sem)
    n_vencidas = num("F4") if num("F4") is not None else len(ven)
    total_cuotas = num("G4") if num("G4") is not None else (n_cuotas_semana + n_vencidas)
    cuotas_cobradas = num("H4")
    if cuotas_cobradas is None:
        cuotas_cobradas = sum(1 for _, p in (sem + ven) if p)
    cobrado_dinero = num("J4")
    if cobrado_dinero is None:
        cobrado_dinero = _sum_pag(sem) + _sum_pag(ven)
    pct_avance = num("K4")
    if pct_avance is None:
        pct_avance = (cobrado_dinero / potencial_total) if potencial_total else 0.0

    # objetivo por día: se calcula desde la hoja de detalle (agrupando por fecha
    # de pago), no desde el Dashboard, para no depender de que Excel recalcule.
    DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    agg = {}
    if hoja_sem is not None:
        ws = wb[hoja_sem]
        headers = [c.value for c in ws[1]]
        idx = {h: i for i, h in enumerate(headers)}
        cf = idx.get("Fecha de pago")
        cv = idx.get("Valor cuota a pagar esta semana")
        if cf is not None and cv is not None:
            for row in ws.iter_rows(min_row=2, values_only=True):
                f = row[cf]
                if not isinstance(f, datetime.datetime):
                    continue
                fd = f.date()
                a = agg.setdefault(fd, {"n": 0, "obj": 0.0})
                a["n"] += 1
                a["obj"] += (row[cv] or 0) if isinstance(row[cv], (int, float)) else 0
    por_dia = [dict(dia=DIAS_ES[f.weekday()], fecha=f, n=v["n"], objetivo=v["obj"])
               for f, v in sorted(agg.items())]
    fechas = [x["fecha"] for x in por_dia]
    titulo = d["B1"].value or "Cobranza de la semana"

    return dict(
        titulo=titulo,
        semana_ini=min(fechas) if fechas else None,
        semana_fin=max(fechas) if fechas else None,
        potencial_semana=potencial_semana,
        potencial_vencidas=potencial_vencidas,
        potencial_total=potencial_total,
        n_cuotas_semana=int(n_cuotas_semana),
        n_vencidas=int(n_vencidas),
        total_cuotas=int(total_cuotas),
        cuotas_cobradas=int(cuotas_cobradas),
        cobrado_dinero=cobrado_dinero,
        pct_avance=pct_avance,
        por_dia=por_dia,
    )


@st.cache_data(ttl=600)
def leer_conciliacion(ruta=None):
    # opcional: sin archivo, el panel de conciliación simplemente no se muestra
    ruta = ruta or F_CONCILIACION
    if not os.path.exists(ruta):
        return dict(problemas=[], n_pagos_sin_registrar=0, monto_en_riesgo=0)
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb["Problemas y solución"]
    problemas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        problemas.append(dict(num=row[0], problema=row[1], casos=row[2], monto=row[3], solucion=row[4]))
    ws2 = wb["Pagos sin registrar SISMO"]
    pagos_sin_registrar = []
    for row in ws2.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        pagos_sin_registrar.append(row)
    return dict(problemas=problemas, n_pagos_sin_registrar=len(pagos_sin_registrar),
                monto_en_riesgo=sum(p["monto"] for p in problemas if isinstance(p["monto"], (int, float))))
