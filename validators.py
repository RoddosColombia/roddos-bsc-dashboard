"""Valida cada archivo subido en 'Actualizar datos' antes de reemplazar
los datos anteriores. Cada validador recibe un Workbook de openpyxl abierto con
data_only=True (los mismos VALORES que verá el tablero, no las fórmulas) y
devuelve una lista de errores en español, en lenguaje simple, citando la fila
exacta cuando aplica. Lista vacía = archivo aceptado.

Regla de oro: todo lo que data_sources.py y metricas.py leen sin protección
tiene que estar verificado aquí. Si un archivo pasa la validación, el tablero
no se puede caer por culpa de ese archivo. tests/test_validadores.py comprueba
esa promesa caso por caso.

Qué se revisa:
  - Estructura: hojas y columnas que el código usa.
  - Tipos: las columnas que se suman deben ser números; las de fecha, fechas
    reales (no texto que parezca fecha).
  - Recálculo: si el Excel se guardó sin recalcular (celdas del Dashboard
    vacías), se pide abrirlo y guardarlo en Excel.
  - Sentido común: fechas de pago en el futuro, meses repetidos en Metas,
    valores fuera de las listas desplegables.
"""
import datetime

import formatos

MAX_ERRORES_POR_COLUMNA = 5


# ---------------------------------------------------------------- utilidades

def _hojas_faltantes(wb, hojas_esperadas):
    return [h for h in hojas_esperadas if h not in wb.sheetnames]


def _encabezados(ws, fila_header):
    return [c.value.strip() if isinstance(c.value, str) else c.value for c in ws[fila_header]]


def _columnas_faltantes(ws, columnas_esperadas, fila_header):
    headers = _encabezados(ws, fila_header)
    return [c for c in columnas_esperadas if c not in headers]


def _error_estructura(nombre_archivo, faltan_hojas=None, hoja=None, faltan_cols=None):
    if faltan_hojas:
        return [f"A este archivo le faltan la(s) hoja(s) {faltan_hojas}. ¿Es el {nombre_archivo} correcto?"]
    if faltan_cols:
        return [f"En la hoja '{hoja}' faltan la(s) columna(s) {faltan_cols}. ¿Cambió el formato del archivo?"]
    return []


def _estructura(wb, nombre_archivo, hojas, columnas):
    """hojas: lista de hojas obligatorias. columnas: {hoja: (fila_encabezado, [columnas])}."""
    faltan = _hojas_faltantes(wb, hojas)
    if faltan:
        return _error_estructura(nombre_archivo, faltan_hojas=faltan)
    for hoja, (fila, cols) in columnas.items():
        faltan_cols = _columnas_faltantes(wb[hoja], cols, fila)
        if faltan_cols:
            return _error_estructura(nombre_archivo, hoja=hoja, faltan_cols=faltan_cols)
    return []


def _es_fecha(v):
    return isinstance(v, (datetime.date, datetime.datetime))


def _es_numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _a_fecha(v):
    return v.date() if isinstance(v, datetime.datetime) else v


def _filas(ws, fila_header, incluir=None):
    """Recorre las filas de datos como dicts {encabezado: valor}, con su número de fila.
    `incluir(d)` decide qué filas cuentan (p. ej. las que tienen código de crédito)."""
    headers = _encabezados(ws, fila_header)
    for n, row in enumerate(ws.iter_rows(min_row=fila_header + 1, values_only=True), start=fila_header + 1):
        d = dict(zip(headers, row))
        if all(v is None for v in row):
            continue
        if incluir is not None and not incluir(d):
            continue
        yield n, d


class _Acumulador:
    """Junta errores sin inundar la pantalla: máximo N por (hoja, columna, tipo)."""

    def __init__(self):
        self.errores = []
        self._conteo = {}

    def agregar(self, clave, mensaje):
        k = self._conteo.get(clave, 0)
        self._conteo[clave] = k + 1
        if k < MAX_ERRORES_POR_COLUMNA:
            self.errores.append(mensaje)

    def cerrar(self):
        for clave, k in self._conteo.items():
            if k > MAX_ERRORES_POR_COLUMNA:
                hoja, col, _ = clave
                self.errores.append(f"... y {k - MAX_ERRORES_POR_COLUMNA} fila(s) más con el mismo problema "
                                    f"en '{col}' (hoja '{hoja}').")
        return self.errores


def _revisar_tipos(acc, ws, hoja, fila_header, numericas=(), fechas=(), incluir=None, no_futuras=()):
    manana = formatos.hoy_colombia() + datetime.timedelta(days=1)
    for n, d in _filas(ws, fila_header, incluir):
        for col in numericas:
            v = d.get(col)
            if v is not None and not _es_numero(v):
                acc.agregar((hoja, col, "num"),
                            f"Hoja '{hoja}', fila {n}: '{col}' debe ser un número (hoy dice {v!r}).")
        for col in fechas:
            v = d.get(col)
            if v is not None and not _es_fecha(v):
                acc.agregar((hoja, col, "fecha"),
                            f"Hoja '{hoja}', fila {n}: '{col}' debe ser una fecha de Excel, no texto "
                            f"(hoy dice {v!r}).")
        for col in no_futuras:
            v = d.get(col)
            if _es_fecha(v) and _a_fecha(v) > manana:
                acc.agregar((hoja, col, "futura"),
                            f"Hoja '{hoja}', fila {n}: '{col}' es {_a_fecha(v)}, una fecha futura — "
                            "revisa si hay un error de tecleo.")


def _sin_recalcular(ws, celdas, nombre_archivo):
    """Si TODAS las celdas clave están vacías, el archivo se guardó sin que Excel calculara
    las fórmulas (pasa al generarlo con otro programa). El tablero mostraría todo en cero."""
    if all(ws[c].value is None for c in celdas):
        return [f"La hoja '{ws.title}' del {nombre_archivo} tiene las celdas de resumen vacías "
                f"({', '.join(celdas)}). Ábrelo en Excel, guárdalo (Ctrl+S) para que recalcule "
                "y vuelve a subirlo."]
    return []


def _celdas_numericas(ws, celdas):
    errores = []
    for c in celdas:
        v = ws[c].value
        if v is not None and not _es_numero(v):
            errores.append(f"Hoja '{ws.title}', celda {c}: debe ser un número (hoy dice {v!r}). "
                           "¿La fórmula da error (#¡REF!, #¡VALOR!)?")
    return errores


# ---------------------------------------------------------------- Recaudo

RECAUDO_COLS_CUOTAS = ["Fecha prog.", "Semana", "Cód. crédito", "Cliente", "Monto cuota", "Estado",
                       "Clasificación meta", "Fecha pago SISMO", "Pagado SISMO", "Saldo a cobrar"]
RECAUDO_CELDAS_DASHBOARD = ["B5", "D5", "F5", "H5", "B8", "B11"]


def validar_recaudo(wb):
    nombre = "archivo de Recaudo"
    errores = _estructura(wb, nombre, ["Dashboard", "Resumen Semanal", "Detalle Cuotas", "Creditos SISMO"],
                          {"Detalle Cuotas": (2, RECAUDO_COLS_CUOTAS)})
    if errores:
        return errores
    errores = _sin_recalcular(wb["Dashboard"], RECAUDO_CELDAS_DASHBOARD, nombre)
    errores += _celdas_numericas(wb["Dashboard"], RECAUDO_CELDAS_DASHBOARD)
    if errores:
        return errores

    ws = wb["Detalle Cuotas"]
    con_codigo = lambda d: d.get("Cód. crédito") is not None  # noqa: E731
    if not any(True for _ in _filas(ws, 2, con_codigo)):
        return ["La hoja 'Detalle Cuotas' no tiene ninguna cuota (columna 'Cód. crédito' vacía). "
                "¿Se pegó la descarga de SISMO?"]
    if not any(_es_fecha(d.get("Fecha prog.")) for _, d in _filas(ws, 2, con_codigo)):
        return ["La hoja 'Detalle Cuotas' no tiene ninguna 'Fecha prog.' válida: el tablero no puede "
                "saber de qué mes son los datos."]

    acc = _Acumulador()
    _revisar_tipos(acc, ws, "Detalle Cuotas", 2, incluir=con_codigo,
                   numericas=["Monto cuota", "Pagado SISMO", "Saldo a cobrar"],
                   fechas=["Fecha prog.", "Fecha pago SISMO"],
                   no_futuras=["Fecha pago SISMO"])
    return acc.cerrar()


# ---------------------------------------------------------------- Inventario

# Críticas: ventas, activaciones y cuotas iniciales del mes, y motos disponibles. Deben ser números.
# Las demás celdas del Dashboard pueden traer un error de Excel (#REF!, #N/A) sin bloquear el archivo:
# el lector las muestra como "—". Caso real (oct 2026): el maestro de Operaciones trae #REF! en H7.
INVENTARIO_CELDAS_DASHBOARD = ["B7", "D7", "F7", "H18"]
INVENTARIO_CELDAS_NUMERICAS = INVENTARIO_CELDAS_DASHBOARD


def validar_inventario(wb):
    nombre = "archivo de Inventario"
    errores = _estructura(wb, nombre, ["Dashboard", "Inventario motos", "Plan separe"],
                          {"Inventario motos": (1, ["Placa", "Ubicación", "Estado"])})
    if errores:
        return errores
    errores = _sin_recalcular(wb["Dashboard"], INVENTARIO_CELDAS_DASHBOARD, nombre)
    errores += _celdas_numericas(wb["Dashboard"], INVENTARIO_CELDAS_NUMERICAS)
    return errores


# ---------------------------------------------------------------- Conciliación

def validar_conciliacion(wb):
    return _estructura(wb, "archivo de Conciliación SISMO↔Wava",
                       ["Problemas y solución", "Pagos sin registrar SISMO"], {})


# ---------------------------------------------------------------- Tesorería

TESORERIA_CELDAS_TABLERO = ["B8", "E8", "H8", "K8", "B14", "E14", "H14", "K14"]
TESORERIA_COLS_EGRESOS = ["Fecha", "Valor", "Categoría normalizada", "Es duplicado", "Es reversado", "Es traslado"]
TESORERIA_COLS_INGRESOS = ["Fecha", "Valor", "Es traslado", "Es reverso de egreso"]


def validar_tesoreria(wb):
    nombre = "archivo de Tesorería"
    errores = _estructura(wb, nombre, ["Tablero mes", "Base real egresos", "Base real ingresos"],
                          {"Base real egresos": (1, TESORERIA_COLS_EGRESOS),
                           "Base real ingresos": (1, TESORERIA_COLS_INGRESOS)})
    if errores:
        return errores
    tablero = wb["Tablero mes"]
    errores = _sin_recalcular(tablero, ["B8", "E8", "H8", "E14"], nombre)
    errores += _celdas_numericas(tablero, TESORERIA_CELDAS_TABLERO)
    if errores:
        return errores

    acc = _Acumulador()
    primera_col = lambda d: next(iter(d.values()), None) is not None  # noqa: E731  (igual que el lector)
    for hoja in ("Base real egresos", "Base real ingresos"):
        _revisar_tipos(acc, wb[hoja], hoja, 1, incluir=primera_col, numericas=["Valor"], fechas=["Fecha"])
    errores = acc.cerrar()

    # el tablero necesita saber la fecha de corte: de J4 o, si no, del último egreso
    hay_corte = formatos.parse_fecha_corte(tablero["J4"].value) is not None
    hay_egreso_fechado = any(_es_fecha(d.get("Fecha")) for _, d in _filas(wb["Base real egresos"], 1, primera_col))
    if not hay_corte and not hay_egreso_fechado:
        errores.append("No se encuentra la fecha de corte: la celda J4 de 'Tablero mes' debe decir algo como "
                       "'Último registro: 21 sep 2026' o debe haber egresos con fecha.")
    return errores


# ---------------------------------------------------------------- RRHH

RRHH_COLS_NOMINA_NUM = ["Total devengado", "NETO LEGAL a pagar", "Brecha vs. legal", "COSTO TOTAL EMPRESA/MES"]
RRHH_COLS_VACACIONES_NUM = ["Días pendientes", "Provisión pendiente estimada"]


def validar_rrhh(wb):
    nombre = "archivo de RRHH"
    errores = _estructura(wb, nombre, ["Empleados", "NominaMensual", "Vacaciones"], {
        "Empleados": (3, ["Nombre completo", "Salario básico"]),
        "NominaMensual": (3, ["Empleado"] + RRHH_COLS_NOMINA_NUM),
        "Vacaciones": (3, ["Empleado"] + RRHH_COLS_VACACIONES_NUM),
    })
    if errores:
        return errores

    es_persona = lambda d: d.get("Empleado") not in (None, "TOTAL")  # noqa: E731  (igual que el lector)
    nomina = [d for _, d in _filas(wb["NominaMensual"], 3, es_persona)]
    if nomina and all(d.get("COSTO TOTAL EMPRESA/MES") is None for d in nomina):
        return ["La columna 'COSTO TOTAL EMPRESA/MES' de 'NominaMensual' está vacía: el archivo no está "
                "recalculado. Ábrelo en Excel, guárdalo (Ctrl+S) y vuelve a subirlo."]

    acc = _Acumulador()
    _revisar_tipos(acc, wb["NominaMensual"], "NominaMensual", 3, incluir=es_persona, numericas=RRHH_COLS_NOMINA_NUM)
    _revisar_tipos(acc, wb["Vacaciones"], "Vacaciones", 3, incluir=es_persona, numericas=RRHH_COLS_VACACIONES_NUM)
    return acc.cerrar()


# ---------------------------------------------------------------- Embudo

CANALES_VALIDOS = {"Meta Ads", "Google Ads", "Referido", "Walk-in / punto fisico", "WhatsApp organico", "TikTok"}
DECISIONES_VALIDAS = {"Aprobado", "Rechazado", None}
ESTADOS_AGENDA_VALIDOS = {"Pendiente", "Cumplida", "No cumplida", "No aplica", None}
RESULTADO_VISITA_VALIDOS = {"Compró", "No compró", "Pendiente", None}
EMBUDO_COLS_REQUERIDAS = ["Fecha lead", "Canal", "Nombre", "Etapa actual", "Fecha formulario",
                          "Fecha decision", "Decision", "Fecha agenda visita", "Estado agenda"]
EMBUDO_COLS_FECHA = ["Fecha lead", "Fecha formulario", "Fecha decision", "Fecha agenda visita"]


def validar_embudo(wb):
    if "Embudo_Diario" not in wb.sheetnames:
        return ["A este archivo le falta la hoja 'Embudo_Diario'. ¿Es la Plantilla_Embudo_Comercial correcta?"]

    ws = wb["Embudo_Diario"]
    headers = _encabezados(ws, 1)
    faltan_cols = [c for c in EMBUDO_COLS_REQUERIDAS if c not in headers]
    if faltan_cols:
        return [f"En la hoja 'Embudo_Diario' faltan la(s) columna(s) {faltan_cols}. "
                "Usa la Plantilla_Embudo_Comercial sin borrar columnas."]

    idx = {h: i for i, h in enumerate(headers)}
    hoy = formatos.hoy_colombia()
    acc = _Acumulador()

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        fecha_lead = row[idx["Fecha lead"]]
        if fecha_lead is None:
            continue  # fila en blanco del formato, se ignora

        notas_idx = idx.get("Notas")
        if notas_idx is not None and isinstance(row[notas_idx], str) and "fila de ejemplo" in row[notas_idx].lower():
            continue  # la fila de ejemplo de la plantilla, se ignora
        if formatos.fila_embudo_vacia(dict(zip(headers, row))):
            continue  # solo tiene la fecha (p. ej. fechas pre-llenadas): fila vacía, se ignora

        for col in EMBUDO_COLS_FECHA:
            v = row[idx[col]]
            if v is not None and formatos.parse_fecha_texto(v) is None:
                acc.agregar(("Embudo_Diario", col, "fecha"),
                            f"Fila {i}: '{col}' no es una fecha válida (hoy dice {v!r}). "
                            "Usa una fecha de Excel o el formato día/mes/año, por ejemplo 27/07/2026.")

        canal = row[idx["Canal"]]
        if canal is not None and canal not in CANALES_VALIDOS:
            acc.agregar(("Embudo_Diario", "Canal", "lista"),
                        f"Fila {i}: el canal '{canal}' no está en la lista — usa el desplegable de la columna Canal.")

        if not row[idx["Nombre"]]:
            acc.agregar(("Embudo_Diario", "Nombre", "vacio"), f"Fila {i}: falta el nombre del cliente.")

        fecha_lead = formatos.parse_fecha_texto(fecha_lead)
        if fecha_lead is not None and fecha_lead.date() > hoy:
            acc.agregar(("Embudo_Diario", "Fecha lead", "futura"),
                        f"Fila {i}: la fecha del lead ({fecha_lead.date()}) es una fecha futura — "
                        "revisa si hay un error de tecleo.")

        decision = row[idx["Decision"]]
        if decision not in DECISIONES_VALIDAS:
            acc.agregar(("Embudo_Diario", "Decision", "lista"),
                        f"Fila {i}: la decisión '{decision}' no es válida — debe ser 'Aprobado', "
                        "'Rechazado' o quedar vacía.")

        estado_agenda = row[idx["Estado agenda"]]
        if estado_agenda not in ESTADOS_AGENDA_VALIDOS:
            acc.agregar(("Embudo_Diario", "Estado agenda", "lista"),
                        f"Fila {i}: el estado de agenda '{estado_agenda}' no es válido — usa el desplegable de la columna.")

        # 'Estado agenda' vacío con fecha de agenda NO es error: la Agenda la muestra como
        # "Pendiente" y las métricas solo cuentan Cumplida / No cumplida.

        if "Resultado visita" in idx:
            resultado = row[idx["Resultado visita"]]
            if resultado not in RESULTADO_VISITA_VALIDOS:
                acc.agregar(("Embudo_Diario", "Resultado visita", "lista"),
                            f"Fila {i}: el resultado de visita '{resultado}' no es válido — usa el desplegable "
                            "(Compró / No compró / Pendiente).")

    return acc.cerrar()


# ---------------------------------------------------------------- Metas

METAS_COLS = ["Mes", "Meta ventas (unidades)", "Meta % aprobación crédito", "Meta % cumplimiento agendas",
              "Meta % mora tope", "Meta ingreso cuotas iniciales ($)", "Gasto fijo mensual ($)"]


def validar_metas(wb):
    if "Metas" not in wb.sheetnames:
        return ["A este archivo le falta la hoja 'Metas'. ¿Es la plantilla correcta?"]
    ws = wb["Metas"]
    fila_h = formatos.fila_encabezado(ws, "Mes", por_defecto=None)  # la plantilla: fila 4, pero no se asume
    if fila_h is None:  # sin columna "Mes": mostrar la primera fila con contenido para orientar
        fila_h = next((r for r in range(1, 11) if any(c.value is not None for c in ws[r])), 4)
    headers = _encabezados(ws, fila_h)
    faltan = [c for c in METAS_COLS if c not in headers]
    if faltan:
        encontrados = [h for h in headers if h]
        return [f"En la hoja 'Metas' faltan la(s) columna(s) {faltan}. "
                f"Encabezados encontrados en la fila {fila_h}: {encontrados or '(ninguno)'}."]

    idx = {h: i for i, h in enumerate(headers)}
    errores = []
    numericas = ["Meta ventas (unidades)", "Meta ingreso cuotas iniciales ($)", "Gasto fijo mensual ($)"]
    porcentajes = ["Meta % aprobación crédito", "Meta % cumplimiento agendas", "Meta % mora tope"]
    meses_vistos = {}
    for i, row in enumerate(ws.iter_rows(min_row=fila_h + 1, values_only=True), start=fila_h + 1):
        mes = row[idx["Mes"]]
        if mes is None:
            continue
        if not _es_fecha(mes):
            errores.append(f"Fila {i}: 'Mes' debe ser una fecha de Excel (por ejemplo 01/10/2026), "
                           f"no texto (hoy dice {mes!r}).")
            continue
        clave_mes = (mes.year, mes.month)
        if clave_mes in meses_vistos:
            errores.append(f"Fila {i}: el mes {mes.month:02d}/{mes.year} ya está en la fila "
                           f"{meses_vistos[clave_mes]}. Deja una sola fila por mes.")
        meses_vistos.setdefault(clave_mes, i)
        for col in numericas:
            v = row[idx[col]]
            if not _es_numero(v) or v < 0:
                errores.append(f"Fila {i}: '{col}' debe ser un número mayor o igual a 0 (hoy: {v!r}).")
        for col in porcentajes:
            v = row[idx[col]]
            if not _es_numero(v) or not (0 <= v <= 1):
                errores.append(f"Fila {i}: '{col}' debe ser un porcentaje entre 0% y 100% (hoy: {v!r}).")
    if not meses_vistos and not errores:
        errores.append(f"La hoja 'Metas' no tiene ninguna fila de mes diligenciada (debajo de la fila {fila_h}).")
    return errores


# ---------------------------------------------------------------- Cobranza semanal

def validar_cobranza_semanal(wb):
    hojas = ["Dashboard", "Cuotas de la semana", "Cuotas vencidas"]
    faltan = _hojas_faltantes(wb, hojas)
    if faltan:
        return [f"A este archivo le faltan la(s) hoja(s) {faltan}. Usa la plantilla de cobranza semanal "
                "(hojas: Dashboard, Cuotas de la semana, Cuotas vencidas)."]
    errores = _estructura(wb, "archivo de Cobranza semanal", hojas, {
        "Cuotas de la semana": (1, ["Valor cuota a pagar esta semana", "Fecha de pago", "Pagada"]),
        "Cuotas vencidas": (1, ["Valor cuota vencida", "Pagada"]),
    })
    if errores:
        return errores
    errores = _celdas_numericas(wb["Dashboard"], ["B4", "C4", "D4", "E4", "F4", "G4", "H4", "J4", "K4"])

    acc = _Acumulador()
    for hoja, col_valor in (("Cuotas de la semana", "Valor cuota a pagar esta semana"),
                            ("Cuotas vencidas", "Valor cuota vencida")):
        con_valor = lambda d, c=col_valor: d.get(c) is not None  # noqa: E731  (igual que el lector)
        _revisar_tipos(acc, wb[hoja], hoja, 1, incluir=con_valor, numericas=[col_valor],
                       fechas=["Fecha de pago"] if hoja == "Cuotas de la semana" else [])
        for n, d in _filas(wb[hoja], 1, con_valor):
            if not formatos.valor_si_no_valido(d.get("Pagada")):
                acc.agregar((hoja, "Pagada", "lista"),
                            f"Hoja '{hoja}', fila {n}: 'Pagada' dice {d.get('Pagada')!r} — usa 'Sí', 'No' "
                            "o déjala vacía.")
    return errores + acc.cerrar()


VALIDADORES = {
    "recaudo": validar_recaudo,
    "inventario": validar_inventario,
    "conciliacion": validar_conciliacion,
    "tesoreria": validar_tesoreria,
    "rrhh": validar_rrhh,
    "embudo": validar_embudo,
    "metas": validar_metas,
    "cobranza": validar_cobranza_semanal,
}
