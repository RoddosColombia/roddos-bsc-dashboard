"""Valida cada archivo subido en 'Actualizar datos' antes de reemplazar
los datos anteriores. Cada validador recibe un Workbook de openpyxl y
devuelve una lista de errores en español, en lenguaje simple, citando la
fila exacta cuando aplica. Lista vacía = archivo aceptado.

Los archivos que son exportaciones de un sistema (Recaudo, Inventario,
Tesorería, RRHH, Conciliación) se validan por estructura — hojas y
columnas esperadas — porque el contenido ya viene limpio de su sistema
de origen. El Embudo Comercial lo diligencia una persona a mano, así que
además se valida fila por fila.
"""
import datetime


def _hojas_faltantes(wb, hojas_esperadas):
    return [h for h in hojas_esperadas if h not in wb.sheetnames]


def _columnas_faltantes(ws, columnas_esperadas, fila_header):
    headers = [c.value for c in ws[fila_header]]
    return [c for c in columnas_esperadas if c not in headers]


def _error_estructura(nombre_archivo, faltan_hojas=None, hoja=None, faltan_cols=None):
    if faltan_hojas:
        return [f"A este archivo le faltan la(s) hoja(s) {faltan_hojas}. ¿Es el {nombre_archivo} correcto?"]
    if faltan_cols:
        return [f"En la hoja '{hoja}' faltan la(s) columna(s) {faltan_cols}. ¿Cambió el formato de la exportación?"]
    return []


def validar_recaudo(wb):
    hojas = ["Dashboard", "Resumen Semanal", "Detalle Cuotas", "Creditos SISMO"]
    faltan = _hojas_faltantes(wb, hojas)
    if faltan:
        return _error_estructura("archivo de Recaudo", faltan_hojas=faltan)
    faltan_cols = _columnas_faltantes(
        wb["Detalle Cuotas"],
        ["Fecha prog.", "Semana", "Cód. crédito", "Cliente", "Monto cuota", "Estado", "Clasificación meta"],
        fila_header=2,
    )
    return _error_estructura("archivo de Recaudo", hoja="Detalle Cuotas", faltan_cols=faltan_cols)


def validar_inventario(wb):
    hojas = ["Dashboard", "Inventario motos", "Plan separe"]
    faltan = _hojas_faltantes(wb, hojas)
    if faltan:
        return _error_estructura("archivo de Inventario", faltan_hojas=faltan)
    faltan_cols = _columnas_faltantes(
        wb["Inventario motos"], ["Placa", "Ubicación", "Estado"], fila_header=1
    )
    return _error_estructura("archivo de Inventario", hoja="Inventario motos", faltan_cols=faltan_cols)


def validar_conciliacion(wb):
    hojas = ["Problemas y solución"]
    faltan = _hojas_faltantes(wb, hojas)
    return _error_estructura("archivo de Conciliación SISMO↔Wava", faltan_hojas=faltan)


def validar_tesoreria(wb):
    hojas = ["Tablero mes", "Base real egresos", "Base real ingresos"]
    faltan = _hojas_faltantes(wb, hojas)
    if faltan:
        return _error_estructura("archivo de Tesorería", faltan_hojas=faltan)
    faltan_cols = _columnas_faltantes(
        wb["Base real egresos"],
        ["Fecha", "Valor", "Es duplicado", "Es reversado", "Es traslado"],
        fila_header=1,
    )
    return _error_estructura("archivo de Tesorería", hoja="Base real egresos", faltan_cols=faltan_cols)


def validar_rrhh(wb):
    hojas = ["Empleados", "NominaMensual", "Vacaciones"]
    faltan = _hojas_faltantes(wb, hojas)
    if faltan:
        return _error_estructura("archivo de RRHH", faltan_hojas=faltan)
    faltan_cols = _columnas_faltantes(
        wb["Empleados"], ["Nombre completo", "Salario básico"], fila_header=3
    )
    return _error_estructura("archivo de RRHH", hoja="Empleados", faltan_cols=faltan_cols)


CANALES_VALIDOS = {"Meta Ads", "Google Ads", "Referido", "Walk-in / punto fisico", "WhatsApp organico", "TikTok"}
DECISIONES_VALIDAS = {"Aprobado", "Rechazado", None}
ESTADOS_AGENDA_VALIDOS = {"Pendiente", "Cumplida", "No cumplida", "No aplica", None}


def validar_embudo(wb):
    if "Embudo_Diario" not in wb.sheetnames:
        return ["A este archivo le falta la hoja 'Embudo_Diario'. ¿Es la Plantilla_Embudo_Comercial correcta?"]

    ws = wb["Embudo_Diario"]
    headers = [c.value for c in ws[1]]
    requeridas = ["Fecha lead", "Canal", "Nombre", "Etapa actual"]
    faltan_cols = [c for c in requeridas if c not in headers]
    if faltan_cols:
        return [f"En la hoja 'Embudo_Diario' faltan la(s) columna(s) {faltan_cols}."]

    idx = {h: i for i, h in enumerate(headers)}
    hoy = datetime.date.today()
    errores = []

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        fecha_lead = row[idx["Fecha lead"]]
        if fecha_lead is None:
            continue  # fila en blanco del formato, se ignora

        notas_idx = idx.get("Notas")
        if notas_idx is not None and isinstance(row[notas_idx], str) and "fila de ejemplo" in row[notas_idx].lower():
            continue  # la fila de ejemplo de la plantilla, se ignora

        canal = row[idx["Canal"]]
        if canal is not None and canal not in CANALES_VALIDOS:
            errores.append(f"Fila {i}: el canal '{canal}' no está en la lista — usa el desplegable de la columna Canal.")

        if not row[idx["Nombre"]]:
            errores.append(f"Fila {i}: falta el nombre del cliente.")

        if isinstance(fecha_lead, (datetime.date, datetime.datetime)):
            fecha_lead_d = fecha_lead.date() if isinstance(fecha_lead, datetime.datetime) else fecha_lead
            if fecha_lead_d > hoy:
                errores.append(f"Fila {i}: la fecha del lead ({fecha_lead_d}) es una fecha futura — revisa si hay un error de tecleo.")

        if "Decision" in idx:
            decision = row[idx["Decision"]]
            if decision not in DECISIONES_VALIDAS:
                errores.append(f"Fila {i}: la decisión '{decision}' no es válida — debe ser 'Aprobado', 'Rechazado' o quedar vacía.")

        if "Estado agenda" in idx:
            estado_agenda = row[idx["Estado agenda"]]
            if estado_agenda not in ESTADOS_AGENDA_VALIDOS:
                errores.append(f"Fila {i}: el estado de agenda '{estado_agenda}' no es válido — usa el desplegable de la columna.")

        if "Fecha agenda visita" in idx and "Estado agenda" in idx:
            f_agenda = row[idx["Fecha agenda visita"]]
            e_agenda = row[idx["Estado agenda"]]
            if f_agenda is not None and e_agenda is None:
                errores.append(f"Fila {i}: tiene fecha de agenda pero no tiene 'Estado agenda' — no se va a poder contar como cumplida o no.")

    return errores


def validar_metas(wb):
    if "Metas" not in wb.sheetnames:
        return ["A este archivo le falta la hoja 'Metas'. ¿Es la plantilla correcta?"]
    ws = wb["Metas"]
    headers = [c.value for c in ws[4]]
    requeridas = ["Mes", "Meta ventas (unidades)", "Meta % aprobación crédito",
                  "Meta % cumplimiento agendas", "Meta % mora tope",
                  "Meta ingreso cuotas iniciales ($)", "Gasto fijo mensual ($)"]
    faltan = [c for c in requeridas if c not in headers]
    if faltan:
        return [f"En la hoja 'Metas' faltan la(s) columna(s) {faltan}."]

    idx = {h: i for i, h in enumerate(headers)}
    errores = []
    numericas = ["Meta ventas (unidades)", "Meta ingreso cuotas iniciales ($)", "Gasto fijo mensual ($)"]
    porcentajes = ["Meta % aprobación crédito", "Meta % cumplimiento agendas", "Meta % mora tope"]
    for i, row in enumerate(ws.iter_rows(min_row=5, values_only=True), start=5):
        if row[idx["Mes"]] is None:
            continue
        for col in numericas:
            v = row[idx[col]]
            if not isinstance(v, (int, float)) or v < 0:
                errores.append(f"Fila {i}: '{col}' debe ser un número mayor o igual a 0 (hoy: {v!r}).")
        for col in porcentajes:
            v = row[idx[col]]
            if not isinstance(v, (int, float)) or not (0 <= v <= 1):
                errores.append(f"Fila {i}: '{col}' debe ser un porcentaje entre 0% y 100% (hoy: {v!r}).")
    return errores


VALIDADORES = {
    "recaudo": validar_recaudo,
    "inventario": validar_inventario,
    "conciliacion": validar_conciliacion,
    "tesoreria": validar_tesoreria,
    "rrhh": validar_rrhh,
    "embudo": validar_embudo,
    "metas": validar_metas,
}
