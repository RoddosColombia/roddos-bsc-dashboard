"""Genera los 8 Excel de RODDOS con datos INVENTADOS (anonimizados) para los tests.

Imitan la estructura que esperan data_sources.py y validators.py: mismas hojas,
mismas filas de encabezado y mismas celdas del Dashboard. Ningún dato es real.

Cada `wb_*()` devuelve un Workbook de openpyxl para que un test pueda dañarlo a
propósito (borrar una columna, poner una fecha futura...) antes de guardarlo.
`generar_todos(directorio)` guarda los 8 con los nombres que usa la app.

Los números son fijos y fáciles de verificar a mano. Con HOY = 9 oct 2026:
  - Recaudo: cada día del 1 al 9 de octubre hay una cuota PAGADA de $500.000 y una
    PENDIENTE de $500.000  ->  pagos del mes = $4.500.000, vencidas = $4.500.000.
  - Inventario: 12 vendidas, 10 activadas, 12 disponibles, 14 motos en Site.
"""
import datetime
import os

import openpyxl

HOY = datetime.date(2026, 10, 9)
CUOTA = 500_000


def _dt(d):
    return datetime.datetime(d.year, d.month, d.day)


# ---------------------------------------------------------------- Recaudo

def wb_recaudo(hoy=HOY):
    wb = openpyxl.Workbook()
    d = wb.active
    d.title = "Dashboard"
    d["A1"] = "PROYECCIÓN DE RECAUDO — datos de prueba"
    for celda, valor in {"B5": 62, "D5": 31_000_000, "F5": 26_500_000, "H5": 60_000_000,
                         "B8": 4_500_000, "D8": 55_500_000, "F8": 0.075,
                         "B11": 4_200_000, "D11": 7, "F11": 1_260_000}.items():
        d[celda] = valor
    d["P9"], d["Q9"], d["R9"] = "Fecha", "Ingreso del día", "Acumulado"
    for i in range(hoy.day):
        dia = hoy.replace(day=1) + datetime.timedelta(days=i)
        d[f"P{10 + i}"] = _dt(dia)
        d[f"Q{10 + i}"] = CUOTA
        d[f"R{10 + i}"] = CUOTA * (i + 1)

    s = wb.create_sheet("Resumen Semanal")
    for j, h in enumerate(["Semana", "Rango", "Cuotas", "Meta", "Ingreso real", "Pagado en su semana",
                           "% oportuno", "Diferencia", "Pendiente por cobrar"], start=1):
        s.cell(10, j, h)
    for i, sem in enumerate(range(36, 42)):
        s.cell(11 + i, 1, f"Sem {sem}")
        s.cell(11 + i, 2, f"rango {sem}")
        s.cell(11 + i, 3, 14)
        s.cell(11 + i, 4, 14_000_000)
        s.cell(11 + i, 5, 12_500_000)
        s.cell(11 + i, 6, 11_000_000)
        s.cell(11 + i, 7, 0.8)
        s.cell(11 + i, 9, 1_500_000)

    c = wb.create_sheet("Detalle Cuotas")
    c["A1"] = "DETALLE DE CUOTAS"
    encabezados = ["Fecha prog.", "Semana", "Día", "Rango semana", "Cód. crédito", "Cliente", "Monto cuota",
                   "Estado", "Clasificación meta", "Fecha pago SISMO", "Pagado SISMO", "Saldo a cobrar"]
    for j, h in enumerate(encabezados, start=1):
        c.cell(2, j, h)
    n = 0

    def cuota(fecha, estado, pagada_el=None):
        nonlocal n
        n += 1
        pagado = CUOTA if estado == "PAGADA" else None
        c.append([_dt(fecha), fecha.isocalendar()[1], fecha.day, None, f"CR-{n:04d}", f"Cliente {n:03d}",
                  CUOTA, estado, "En meta", _dt(pagada_el) if pagada_el else None, pagado,
                  0 if estado == "PAGADA" else CUOTA])

    # mes anterior: todo pagado a tiempo
    fin_mes_anterior = hoy.replace(day=1) - datetime.timedelta(days=1)
    for dia in range(1, fin_mes_anterior.day + 1):
        f = fin_mes_anterior.replace(day=dia)
        cuota(f, "PAGADA", f)
    # mes en curso hasta hoy: una pagada y una pendiente por día
    for i in range(hoy.day):
        f = hoy.replace(day=1) + datetime.timedelta(days=i)
        cuota(f, "PAGADA", f)
        cuota(f, "PENDIENTE")
    # resto del mes: programadas, aún no vencen
    f = hoy + datetime.timedelta(days=1)
    while f.month == hoy.month:
        cuota(f, "PENDIENTE")
        f += datetime.timedelta(days=1)

    cs = wb.create_sheet("Creditos SISMO")
    cs.append(["Cód. crédito", "Cliente", "Estado"])
    cs.append(["CR-0001", "Cliente 001", "Activo"])
    return wb


# ---------------------------------------------------------------- Inventario

def wb_inventario(hoy=HOY):
    wb = openpyxl.Workbook()
    d = wb.active
    d.title = "Dashboard"
    d["K2"] = f"Actualizado: {hoy:%d/%m/%Y}"
    for celda, valor in {"B7": 12, "D7": 10, "F7": 18_000_000, "H7": 2, "J7": 3,
                         "B12": 1, "D12": 1, "F12": 0, "H12": 0, "J12": 2,
                         "B18": 3, "D18": 4, "F18": 5, "H18": 12, "J18": 1,
                         "B23": 950_000_000, "D23": 80, "F23": 140_000_000}.items():
        d[celda] = valor
    meses = ["Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"]
    for i, mes in enumerate(meses):
        r = 27 + i
        d[f"N{r}"], d[f"O{r}"], d[f"R{r}"] = mes, 90_000_000, 15_000_000
        d[f"U{r}"], d[f"V{r}"], d[f"W{r}"] = 11, 10, 10
    d[f"N{27 + len(meses)}"] = "TOTAL"
    d[f"V{27 + len(meses)}"] = 80

    m = wb.create_sheet("Inventario motos")
    m.append(["Placa", "Modelo", "Ubicación", "Estado"])
    modelos = ["Raider"] * 5 + ["Sport"] * 5 + ["Apache"] * 5
    for i, modelo in enumerate(modelos):
        m.append([f"AAA{i:02d}F", modelo, "Site" if i < 14 else "Taller",
                  "Disponible" if i < 12 else "Separada"])

    p = wb.create_sheet("Plan separe")
    p["B1"] = "PLAN SEPARE — clientes con cuota inicial en curso"
    for j, h in enumerate(["Cliente", "Crédito", "Valor separado", "Estado"], start=2):
        p.cell(3, j, h)
    p.cell(4, 2, "Cliente 101"); p.cell(4, 3, "CR-9001"); p.cell(4, 4, 1_500_000); p.cell(4, 5, "Parcial")
    p.cell(5, 2, "Cliente 102"); p.cell(5, 3, "CR-9002"); p.cell(5, 4, 3_000_000); p.cell(5, 5, "Completa")
    return wb


# ---------------------------------------------------------------- Conciliación

def wb_conciliacion():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Problemas y solución"
    ws.append(["#", "Problema", "Casos", "Monto", "Solución"])
    ws.append([1, "Pagos en Wava sin registrar en SISMO", "3 casos", 1_500_000, "Registrar en SISMO"])
    ws.append([2, "Créditos duplicados", "1 caso", 500_000, "Anular el duplicado"])
    ps = wb.create_sheet("Pagos sin registrar SISMO")
    ps.append(["Fecha", "Cliente", "Valor"])
    for i in range(3):
        ps.append([_dt(HOY), f"Cliente {i:03d}", 500_000])
    return wb


# ---------------------------------------------------------------- Tesorería

def wb_tesoreria(hoy=HOY):
    wb = openpyxl.Workbook()
    t = wb.active
    t.title = "Tablero mes"
    t["C4"] = _dt(hoy.replace(day=1))
    t["J4"] = f"Último registro: {hoy.day} oct {hoy.year}  ·  AL DÍA"
    for celda, valor in {"B8": 200_000_000, "E8": 120_000_000, "H8": 150_000_000, "K8": 0.8,
                         "B14": 30_000_000, "E14": 85_000_000, "H14": 12_000_000, "K14": 0}.items():
        t[celda] = valor

    e = wb.create_sheet("Base real egresos")
    e.append(["Fecha", "Descripción", "Valor", "Categoría normalizada", "Es duplicado", "Es reversado", "Es traslado"])
    for i in range(hoy.day):
        f = _dt(hoy.replace(day=1) + datetime.timedelta(days=i))
        e.append([f, "Nómina", 2_000_000, "Nómina", "No", "No", "No"])
        e.append([f, "Arriendo", 1_000_000, "Arriendo", "No", "No", "No"])
    e.append([_dt(hoy), "Traslado a otra cuenta", 9_999_999, "Traslado", "No", "No", "Sí"])

    i_ = wb.create_sheet("Base real ingresos")
    i_.append(["Fecha", "Descripción", "Valor", "Es traslado", "Es reverso de egreso"])
    for k in range(hoy.day):
        i_.append([_dt(hoy.replace(day=1) + datetime.timedelta(days=k)), "Recaudo", 4_000_000, "No", "No"])

    a = wb.create_sheet("Facturas Auteco")
    a["A1"] = "FACTURAS AUTECO"
    a.append(["Factura", "Mes de pago", "Saldo pendiente ($)"])
    a.append(["F-1", _dt(hoy.replace(day=1)), 20_000_000])
    a.append(["F-2", _dt(hoy.replace(day=1)), 5_000_000])
    return wb


# ---------------------------------------------------------------- RRHH

def wb_rrhh():
    wb = openpyxl.Workbook()
    emp = wb.active
    emp.title = "Empleados"
    emp["A1"] = "EMPLEADOS"
    for j, h in enumerate(["Nombre completo", "Cargo", "Salario básico", "Fecha ingreso"], start=1):
        emp.cell(3, j, h)
    for i in range(4):
        emp.cell(4 + i, 1, f"Empleado {i + 1}")
        emp.cell(4 + i, 2, "Asesor")
        emp.cell(4 + i, 3, 1_800_000)
        emp.cell(4 + i, 4, datetime.datetime(2025, 1 + i, 1))

    nom = wb.create_sheet("NominaMensual")
    nom["A1"] = "NÓMINA"
    cols = ["Empleado", "Salario", "Total devengado", "NETO LEGAL a pagar", "Brecha vs. legal",
            "COSTO TOTAL EMPRESA/MES"]
    for j, h in enumerate(cols, start=1):
        nom.cell(3, j, h)
    for i in range(4):
        for j, v in enumerate([f"Empleado {i + 1}", 1_800_000, 2_000_000, 1_850_000, 0, 2_700_000], start=1):
            nom.cell(4 + i, j, v)
    for j, v in enumerate(["TOTAL", 7_200_000, 8_000_000, 7_400_000, 0, 10_800_000], start=1):
        nom.cell(8, j, v)

    vac = wb.create_sheet("Vacaciones")
    vac["A1"] = "VACACIONES"
    for j, h in enumerate(["Empleado", "Fecha ingreso", "Días pendientes", "Provisión pendiente estimada",
                           "Alerta"], start=1):
        vac.cell(3, j, h)
    for i in range(4):
        for j, v in enumerate([f"Empleado {i + 1}", datetime.datetime(2025, 1 + i, 1), 10, 600_000,
                               "OK" if i else "Por vencer"], start=1):
            vac.cell(4 + i, j, v)
    return wb


# ---------------------------------------------------------------- Embudo

EMBUDO_COLUMNAS = ["Fecha lead", "Canal", "Nombre", "Telefono", "Etapa actual", "Fecha formulario",
                   "Fecha decision", "Decision", "Motivo rechazo", "Fecha agenda visita", "Estado agenda",
                   "Codigo de credito (si aprobado)", "Notas", "Resultado visita"]


def wb_embudo(hoy=HOY):
    wb = openpyxl.Workbook()
    wb.active.title = "Instrucciones"
    wb["Instrucciones"]["A1"] = "Plantilla — Embudo comercial RODDOS (datos de prueba)"
    ws = wb.create_sheet("Embudo_Diario")
    ws.append(EMBUDO_COLUMNAS)
    ws.append([None, "Meta Ads", "Juan Perez ejemplo", "300", "1. Lead recibido", None, None, None, None,
               None, "Pendiente", None, "Fila de ejemplo — borrala antes de usar", None])
    canales = ["Meta Ads", "Google Ads", "Referido", "WhatsApp organico"]
    for i in range(12):
        f_lead = hoy.replace(day=1) + datetime.timedelta(days=i % hoy.day)
        aprobado = i % 3 != 0
        agendado = aprobado and i % 2 == 0
        f_agenda = f_lead + datetime.timedelta(days=1) if agendado else None
        if f_agenda and f_agenda > hoy:
            f_agenda = hoy
        estado = ("Cumplida" if i % 4 == 0 else "No cumplida") if agendado else None
        ws.append([
            _dt(f_lead), canales[i % 4], f"Lead {i + 1:03d}", "3000000000", "5. Decision tomada",
            _dt(f_lead), _dt(f_lead), "Aprobado" if aprobado else "Rechazado",
            None if aprobado else "Score insuficiente",
            _dt(f_agenda) if f_agenda else None, estado, None, None,
            ("Compró" if estado == "Cumplida" else None),
        ])
    return wb


# ---------------------------------------------------------------- Metas

def wb_metas():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Metas"
    ws["A1"] = "METAS MENSUALES — RODDOS"
    ws["A2"] = "Una fila por mes."
    ws.append([])
    for j, h in enumerate(["Mes", "Meta ventas (unidades)", "Meta % aprobación crédito",
                           "Meta % cumplimiento agendas", "Meta % mora tope",
                           "Meta ingreso cuotas iniciales ($)", "Gasto fijo mensual ($)", "Notas"], start=1):
        ws.cell(4, j, h)
    for r, (mes, ventas) in enumerate([(9, 100), (10, 30)], start=5):
        for j, v in enumerate([datetime.datetime(2026, mes, 1), ventas, 0.6, 0.8, 0.07,
                               45_000_000, 40_000_000, "prueba"], start=1):
            ws.cell(r, j, v)
    return wb


# ---------------------------------------------------------------- Cobranza semanal

def wb_cobranza(hoy=HOY):
    """El Dashboard viene SIN recalcular (celdas vacías) para obligar a calcular desde el
    detalle, y 'Pagada' viene como 'Sí'/'No', que es como lo pide el instructivo."""
    wb = openpyxl.Workbook()
    d = wb.active
    d.title = "Dashboard"
    d["B1"] = "Cobranza de la semana — prueba"
    lunes = hoy - datetime.timedelta(days=hoy.weekday())
    s = wb.create_sheet("Cuotas de la semana")
    s.append(["Cliente", "Cód. crédito", "Fecha de pago", "Valor cuota a pagar esta semana", "Pagada"])
    for i in range(6):
        s.append([f"Cliente {i:03d}", f"CR-{i:04d}", _dt(lunes + datetime.timedelta(days=i % 5)),
                  CUOTA, "Sí" if i < 3 else "No"])
    v = wb.create_sheet("Cuotas vencidas")
    v.append(["Cliente", "Valor cuota vencida", "Pagada"])
    v.append(["Cliente 900", CUOTA, "Sí"])
    v.append(["Cliente 901", CUOTA, None])
    return wb


# ---------------------------------------------------------------- todo junto

ARCHIVOS = {
    "Proyeccion_Recaudo.xlsx": wb_recaudo,
    "Inventario_2026.xlsx": wb_inventario,
    "Cruce_SISMO_Wava.xlsx": wb_conciliacion,
    "Flujo_Pagos_Deudas.xlsx": wb_tesoreria,
    "Control_RRHH_Nomina_RODDOS_2026.xlsx": wb_rrhh,
    "Embudo_Comercial_RODDOS.xlsx": wb_embudo,
    "Metas_RODDOS.xlsx": wb_metas,
    "Cobranza_Semanal.xlsx": wb_cobranza,
}


def generar_todos(directorio):
    os.makedirs(directorio, exist_ok=True)
    rutas = {}
    for nombre, fabrica in ARCHIVOS.items():
        ruta = os.path.join(directorio, nombre)
        fabrica().save(ruta)
        rutas[nombre] = ruta
    return rutas


if __name__ == "__main__":
    # Uso: python tests/fixtures_excel.py [carpeta] [--forzar]
    # Sirve para ver la app con datos de mentira. NO pisa archivos existentes salvo con --forzar,
    # para no borrar por accidente tus Excel reales de data_raw/.
    import sys

    args = [a for a in sys.argv[1:] if a != "--forzar"]
    destino = args[0] if args else "data_raw"
    ya_hay = [n for n in ARCHIVOS if os.path.exists(os.path.join(destino, n))]
    if ya_hay and "--forzar" not in sys.argv:
        print(f"En {destino}/ ya existen {len(ya_hay)} archivo(s) ({', '.join(ya_hay)}).")
        print("No se sobrescribió nada. Usa otra carpeta, o agrega --forzar si estás seguro.")
        sys.exit(1)
    for nombre in generar_todos(destino):
        print(f"  {nombre}")
    print(f"Listo: archivos de prueba en {destino}/")
