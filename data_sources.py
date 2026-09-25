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

import respaldo

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_raw")
F_INVENTARIO = os.path.join(RAW_DIR, "Inventario_2026.xlsx")
F_RECAUDO = os.path.join(RAW_DIR, "Proyeccion_Recaudo.xlsx")
F_CONCILIACION = os.path.join(RAW_DIR, "Cruce_SISMO_Wava.xlsx")
F_TESORERIA = os.path.join(RAW_DIR, "Flujo_Pagos_Deudas.xlsx")
F_RRHH = os.path.join(RAW_DIR, "Control_RRHH_Nomina_RODDOS_2026.xlsx")
F_EMBUDO = os.path.join(RAW_DIR, "Embudo_Comercial_RODDOS.xlsx")
F_METAS = os.path.join(RAW_DIR, "Metas_RODDOS.xlsx")
ARCHIVOS = [F_INVENTARIO, F_RECAUDO, F_CONCILIACION, F_TESORERIA, F_RRHH, F_EMBUDO, F_METAS]


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

MESES_ABR = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
             7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}


@st.cache_data(ttl=600)
def leer_inventario():
    wb = openpyxl.load_workbook(F_INVENTARIO, data_only=True)
    ws = wb["Dashboard"]

    def g(coord):
        v = ws[coord].value
        return v if v is not None else 0

    actualizado_txt = ws["K2"].value or ""
    actualizado_fecha = None
    try:
        parte = actualizado_txt.split(":")[-1].strip()
        actualizado_fecha = datetime.datetime.strptime(parte, "%d/%m/%Y").date()
    except Exception:
        actualizado_fecha = None

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
    # resumen mensual: filas 27-34 (mar a sep), columnas N/O (fact), Q/R (ci), T/U/V/W (vend/act/fact)
    meses = []
    for r in range(27, 35):
        mes_lbl = ws[f"N{r}"].value
        if not mes_lbl:
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
    idx_estado = header.index("Estado")
    idx_ubic = header.index("Ubicación")
    disponibles = 0
    en_site = 0
    for row in ws2.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
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
def leer_recaudo():
    wb = openpyxl.load_workbook(F_RECAUDO, data_only=True)
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
    # serie diaria de recaudo (P10:S..)
    diario = []
    for r in range(10, 40):
        fecha = wsD[f"P{r}"].value
        ingreso = wsD[f"Q{r}"].value
        acumulado = wsD[f"R{r}"].value
        if fecha is None:
            continue
        diario.append(dict(fecha=fecha, ingreso_dia=ingreso if isinstance(ingreso, (int, float)) else None,
                            acumulado_mes=acumulado if isinstance(acumulado, (int, float)) else None))
    df_diario = pd.DataFrame(diario)

    # tablero semanal (fila 10 = encabezados, filas 11-15 = Sem 36-40)
    wsS = wb["Resumen Semanal"]
    semanas = []
    for r in range(11, 16):
        sem = wsS.cell(row=r, column=1).value
        if not sem or not str(sem).startswith("Sem"):
            continue
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
    headers = [c.value for c in wsC[2]]
    rows = []
    for row in wsC.iter_rows(min_row=3, values_only=True):
        if row[4] is None:  # Cód. crédito
            continue
        rows.append(row)
    df_cuotas = pd.DataFrame(rows, columns=headers)

    return dict(dashboard=dashboard, diario=df_diario, semanal=df_semanal, cuotas=df_cuotas)


MESES_ABR_INV = {v: k for k, v in MESES_ABR.items()}


def _parse_fecha_corte(txt):
    # ej: "Último registro: 21 sep 2026  ·  AL DÍA" -> date(2026, 9, 21)
    import re
    m = re.search(r"(\d{1,2})\s+([a-zA-Zé]{3})\.?\s+(\d{4})", txt or "")
    if not m:
        return None
    dia, mes_abr, anio = m.groups()
    mes = MESES_ABR_INV.get(mes_abr.lower().replace("é", "e"))
    if not mes:
        return None
    return datetime.date(int(anio), mes, int(dia))


@st.cache_data(ttl=600)
def leer_tesoreria():
    wb = openpyxl.load_workbook(F_TESORERIA, data_only=True)
    ws = wb["Tablero mes"]

    def g(coord):
        v = ws[coord].value
        return v if v is not None else 0

    corte_txt = ws["J4"].value or ""
    dashboard = dict(
        mes_control=ws["C4"].value,
        corte_txt=corte_txt,
        corte_fecha=_parse_fecha_corte(corte_txt),
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
def leer_rrhh():
    wb = openpyxl.load_workbook(F_RRHH, data_only=True)

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
def leer_embudo():
    """Lee Embudo_Comercial_RODDOS.xlsx (misma estructura que la Plantilla_Embudo_Comercial.xlsx
    descargable). Descarta la fila de ejemplo y cualquier fila sin 'Fecha lead'."""
    if not os.path.exists(F_EMBUDO):
        return pd.DataFrame()
    wb = openpyxl.load_workbook(F_EMBUDO, data_only=True)
    ws = wb["Embudo_Diario"]
    headers = [c.value for c in ws[1]]
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(headers, row))
        if d.get("Fecha lead") is None:
            continue
        if isinstance(d.get("Notas"), str) and "fila de ejemplo" in d["Notas"].lower():
            continue
        filas.append(d)
    df = pd.DataFrame(filas)
    for col in ["Fecha lead", "Fecha formulario", "Fecha decision", "Fecha agenda visita"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data(ttl=600)
def leer_metas(referencia=None):
    """Lee la fila de Metas_RODDOS.xlsx que corresponde al mes de 'referencia'
    (por defecto, hoy). Si no hay fila para ese mes exacto, usa la más
    reciente que sea <= esa fecha (evita que el tablero se rompa si
    todavia no se ha diligenciado la fila del mes en curso)."""
    if not os.path.exists(F_METAS):
        return None
    ref = referencia or datetime.date.today()
    wb = openpyxl.load_workbook(F_METAS, data_only=True)
    ws = wb["Metas"]
    headers = [c.value for c in ws[4]]
    filas = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        if row[0] is None:
            continue
        d = dict(zip(headers, row))
        filas.append(d)
    if not filas:
        return None
    candidatas = [f for f in filas if f["Mes"].date() <= ref] or filas
    fila = max(candidatas, key=lambda f: f["Mes"])
    return dict(
        mes=fila["Mes"].date(),
        ventas=fila["Meta ventas (unidades)"],
        pct_aprobacion=fila["Meta % aprobación crédito"],
        pct_agendas=fila["Meta % cumplimiento agendas"],
        pct_mora_tope=fila["Meta % mora tope"],
        ci_dinero=fila["Meta ingreso cuotas iniciales ($)"],
        gasto_fijo=fila["Gasto fijo mensual ($)"],
    )


@st.cache_data(ttl=600)
def leer_conciliacion():
    wb = openpyxl.load_workbook(F_CONCILIACION, data_only=True)
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
