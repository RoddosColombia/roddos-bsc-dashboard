"""Arma los 17 rubros en el formato ayer / esta semana / este mes.

Cada rubro declara su propia fecha de corte (no todos los archivos se
actualizan el mismo día) para no fingir una sola fecha "hoy" común.
"""
import datetime
import pandas as pd
import data_sources as ds

ETAPAS = [
    ("1 · Demanda", ["leads"]),
    ("2 · Crédito", ["formularios", "aprobados_rechazados", "pct_aprobacion"]),
    ("3 · Agenda", ["agendas_totales", "agendas_hoy", "agendas_cumplidas_ayer", "agendas_incumplidas"]),
    ("4 · Venta", ["ventas", "ci_completas", "ci_parciales", "ci_dinero"]),
    ("5 · Facturación y entrega", ["facturacion", "activaciones"]),
    ("6 · Cartera y mora", ["cuotas_mes", "pagos_num", "pagos_dinero", "vencidas_num", "vencidas_dinero", "mora_total"]),
    ("7 · Inventario", ["inventario_bodega", "inventario_disponible", "dias_inventario"]),
]

RUBROS_ORDEN = [
    "leads", "formularios", "aprobados_rechazados", "pct_aprobacion",
    "agendas_totales", "agendas_hoy", "agendas_cumplidas_ayer", "agendas_incumplidas",
    "ventas", "facturacion",
    "ci_completas", "ci_parciales", "ci_dinero", "activaciones",
    "cuotas_mes", "pagos_num", "pagos_dinero", "vencidas_num", "vencidas_dinero",
    "mora_total", "inventario_bodega", "inventario_disponible", "dias_inventario",
]

RUBRO_LABEL = {
    "leads": "1 · Recepción de leads",
    "formularios": "2 · Diligenciamiento de formularios de crédito",
    "aprobados_rechazados": "3 · Aprobados y rechazados",
    "pct_aprobacion": "3b · % de aprobación de crédito",
    "agendas_totales": "4 · # agendas de visita de cliente",
    "agendas_hoy": "5 · Agendas de visita para hoy",
    "agendas_cumplidas_ayer": "6 · Agendas cumplidas ayer (de todas las que había)",
    "agendas_incumplidas": "7 · No cumplimientos de agenda (mes)",
    "ventas": "8 · Ventas (cuota inicial completa + parcial)",
    "facturacion": "9 · Facturación a cliente",
    "ci_completas": "10 · Cuotas iniciales completas (#)",
    "ci_parciales": "11 · Cuotas iniciales parciales (#)",
    "ci_dinero": "12 · Cuotas iniciales ($)",
    "activaciones": "13 · Activaciones (entrega de motos)",
    "cuotas_mes": "14 · Cuotas totales del mes a hoy",
    "pagos_num": "15 · Pagos de cuotas (#)",
    "pagos_dinero": "16 · Pagos de cuotas ($)",
    "vencidas_num": "17 · Cuotas vencidas (#)",
    "vencidas_dinero": "18 · Cuotas vencidas ($)",
    "mora_total": "19 · Mora total ($)",
    "inventario_bodega": "20 · Motos en bodega (#)",
    "inventario_disponible": "21 · Motos disponibles (#)",
    "dias_inventario": "21b · Días de inventario",
}

RUBROS_SIN_DATO = {
    "leads", "formularios", "aprobados_rechazados", "pct_aprobacion",
    "agendas_totales", "agendas_hoy", "agendas_cumplidas_ayer", "agendas_incumplidas",
}


def _semana_iso(fecha):
    if not isinstance(fecha, (datetime.date, datetime.datetime)):
        return None
    return fecha.isocalendar()[1]


def construir_metricas():
    inv = ds.leer_inventario()
    rec = ds.leer_recaudo()
    conc = ds.leer_conciliacion()

    cuotas = rec["cuotas"].copy()
    cuotas["Fecha prog."] = pd.to_datetime(cuotas["Fecha prog."], errors="coerce")
    cuotas["Fecha pago SISMO"] = pd.to_datetime(cuotas["Fecha pago SISMO"], errors="coerce")

    hoy_recaudo = cuotas["Fecha pago SISMO"].max()
    if pd.isna(hoy_recaudo):
        hoy_recaudo = cuotas["Fecha prog."].max()
    hoy_recaudo = hoy_recaudo.date() if not pd.isna(hoy_recaudo) else datetime.date.today()
    ayer_recaudo = hoy_recaudo - datetime.timedelta(days=1)
    semana_ini = hoy_recaudo - datetime.timedelta(days=hoy_recaudo.weekday())
    mes_ini = hoy_recaudo.replace(day=1)

    pagos = cuotas.dropna(subset=["Fecha pago SISMO"])

    def pagos_en(desde, hasta):
        m = pagos[(pagos["Fecha pago SISMO"].dt.date >= desde) & (pagos["Fecha pago SISMO"].dt.date <= hasta)]
        return len(m), float(m["Pagado SISMO"].fillna(0).sum())

    def vencidas_en(hasta):
        # "vencida" = ya paso su fecha programada y no quedo totalmente pagada (Estado real: PENDIENTE o PARCIAL)
        m = cuotas[(cuotas["Fecha prog."].dt.date <= hasta) & (cuotas["Estado"].isin(["PENDIENTE", "PARCIAL"]))]
        return len(m), float(m["Saldo a cobrar"].fillna(0).sum())

    def cuotas_prog_a(hasta):
        m = cuotas[cuotas["Fecha prog."].dt.date <= hasta]
        return len(m)

    p_ayer = pagos_en(ayer_recaudo, ayer_recaudo)
    p_sem = pagos_en(semana_ini, hoy_recaudo)
    p_mes = pagos_en(mes_ini, hoy_recaudo)
    v_ayer = vencidas_en(ayer_recaudo)
    v_sem = vencidas_en(hoy_recaudo)  # vencidas es un saldo acumulado, no se "resetea" por semana
    v_mes = vencidas_en(hoy_recaudo)
    c_mes_ayer = cuotas_prog_a(ayer_recaudo)
    c_mes_sem = cuotas_prog_a(hoy_recaudo)
    c_mes_mes = cuotas_prog_a(hoy_recaudo)

    hoy_inv_txt = inv["hoy"]["actualizado"]
    hoy_inv = inv["hoy"]["actualizado_fecha"] or hoy_recaudo

    M = {}
    M["cuotas_mes"] = dict(ayer=c_mes_ayer, semana=c_mes_sem, mes=c_mes_mes,
                            fuente="Proyeccion_Recaudo.xlsx · Detalle Cuotas", corte=str(hoy_recaudo))
    M["pagos_num"] = dict(ayer=p_ayer[0], semana=p_sem[0], mes=p_mes[0],
                           fuente="Proyeccion_Recaudo.xlsx · Detalle Cuotas", corte=str(hoy_recaudo))
    M["pagos_dinero"] = dict(ayer=p_ayer[1], semana=p_sem[1], mes=p_mes[1],
                              fuente="Proyeccion_Recaudo.xlsx · Detalle Cuotas", corte=str(hoy_recaudo))
    M["vencidas_num"] = dict(ayer=v_ayer[0], semana=v_sem[0], mes=v_mes[0],
                              fuente="Proyeccion_Recaudo.xlsx · Detalle Cuotas (saldo vencido acumulado, no diario)", corte=str(hoy_recaudo))
    M["vencidas_dinero"] = dict(ayer=v_ayer[1], semana=v_sem[1], mes=v_mes[1],
                                 fuente="Proyeccion_Recaudo.xlsx · Detalle Cuotas (saldo vencido acumulado, no diario)", corte=str(hoy_recaudo))
    M["mora_total"] = dict(ayer=None, semana=None, mes=rec["dashboard"]["mora_vencida_activos"],
                            fuente="Proyeccion_Recaudo.xlsx · Dashboard (créditos activos en mora)", corte=str(hoy_recaudo))

    # inventario / ventas / activaciones / facturacion / ci -- snapshot del Dashboard de Inventario
    h = inv["hoy"]
    M["ventas"] = dict(ayer=None, semana=None, mes=h["vendidas_mes"],
                        fuente="Inventario_2026.xlsx · Dashboard", corte=str(hoy_inv))
    M["facturacion"] = dict(ayer=None, semana=None, mes=h["motos_facturadas_anio"],
                             extra=f"Pendientes de facturar: {h['pendientes_factura']}",
                             fuente="Inventario_2026.xlsx · Dashboard", corte=str(hoy_inv))
    M["ci_completas"] = dict(ayer=None, semana=None, mes=h["ci_completa_hoy"],
                              fuente="Inventario_2026.xlsx · Dashboard (Plan separe, snapshot de hoy)", corte=str(hoy_inv))
    M["ci_parciales"] = dict(ayer=None, semana=None, mes=h["ci_parcial_hoy"],
                              fuente="Inventario_2026.xlsx · Dashboard (Plan separe, snapshot de hoy)", corte=str(hoy_inv))
    M["ci_dinero"] = dict(ayer=None, semana=None, mes=h["ci_mes"],
                           fuente="Inventario_2026.xlsx · Dashboard", corte=str(hoy_inv))
    M["activaciones"] = dict(ayer=None, semana=None, mes=h["activadas_mes"],
                              extra=f"Acumulado 2026: {sum(m['activadas'] or 0 for m in inv['mensual'].to_dict('records'))} activadas",
                              fuente="Inventario_2026.xlsx · Dashboard", corte=str(hoy_inv))
    M["inventario_disponible"] = dict(ayer=None, semana=None, mes=h["disp_total"],
                                       extra=f"Raider {h['disp_raider']} · Sport {h['disp_sport']} · Apache {h['disp_apache']}",
                                       fuente="Inventario_2026.xlsx · Dashboard", corte=str(hoy_inv))
    M["inventario_bodega"] = dict(ayer=None, semana=None, mes=inv["motos_en_site"],
                                   extra=f"De esas, {h['disp_total']} están realmente disponibles para vender (el resto ya está comprometido)",
                                   fuente="Inventario_2026.xlsx · Inventario motos (Ubicación = Site)", corte=str(hoy_inv))

    # días de inventario: a cuántos días de venta equivale lo disponible, al ritmo actual del mes
    ritmo_venta_diario = (h["vendidas_mes"] or 0) / hoy_inv.day if hoy_inv.day else 0
    dias_inv = round((h["disp_total"] or 0) / ritmo_venta_diario, 1) if ritmo_venta_diario > 0 else None
    M["dias_inventario"] = dict(
        ayer=None, semana=None, mes=dias_inv,
        extra=(f"Al ritmo de {ritmo_venta_diario:.1f} ventas/día de este mes" if dias_inv is not None
               else "Sin ventas registradas este mes — no se puede proyectar"),
        fuente="Calculado: motos disponibles ÷ ritmo de venta del mes", corte=str(hoy_inv),
    )

    # ---------- embudo comercial (leads, formularios, decisiones, agendas) ----------
    embudo = ds.leer_embudo()
    FUENTE_EMBUDO = "Embudo_Comercial_RODDOS.xlsx · Embudo_Diario"
    if embudo.empty:
        for r in RUBROS_SIN_DATO:
            M[r] = dict(ayer=None, semana=None, mes=None,
                        fuente="Sin dato aún — se activa al llenar Plantilla_Embudo_Comercial.xlsx", corte=None)
    else:
        hoy_emb = hoy_recaudo
        ayer_emb = hoy_emb - datetime.timedelta(days=1)
        semana_ini_emb = hoy_emb - datetime.timedelta(days=hoy_emb.weekday())
        mes_ini_emb = hoy_emb.replace(day=1)

        def _contar(col, desde, hasta, filtro=None):
            # dropna primero: una serie de fecha totalmente vacia (NaT) puede
            # quedar con un dtype que .dt.date compara mal contra un date de Python
            con_fecha = embudo[embudo[col].notna()]
            s = con_fecha[col]
            m = con_fecha[(s.dt.date >= desde) & (s.dt.date <= hasta)]
            if filtro is not None:
                m = filtro(m)
            return len(m)

        M["leads"] = dict(
            ayer=_contar("Fecha lead", ayer_emb, ayer_emb),
            semana=_contar("Fecha lead", semana_ini_emb, hoy_emb),
            mes=_contar("Fecha lead", mes_ini_emb, hoy_emb),
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )
        M["formularios"] = dict(
            ayer=_contar("Fecha formulario", ayer_emb, ayer_emb),
            semana=_contar("Fecha formulario", semana_ini_emb, hoy_emb),
            mes=_contar("Fecha formulario", mes_ini_emb, hoy_emb),
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )
        aprob = lambda m: m[m["Decision"] == "Aprobado"]
        rech = lambda m: m[m["Decision"] == "Rechazado"]
        n_aprob_mes = _contar("Fecha decision", mes_ini_emb, hoy_emb, aprob)
        n_rech_mes = _contar("Fecha decision", mes_ini_emb, hoy_emb, rech)
        M["aprobados_rechazados"] = dict(
            ayer=_contar("Fecha decision", ayer_emb, ayer_emb),
            semana=_contar("Fecha decision", semana_ini_emb, hoy_emb),
            mes=n_aprob_mes + n_rech_mes,
            extra=f"Del mes: {n_aprob_mes} aprobados · {n_rech_mes} rechazados",
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )
        total_decididas_mes = n_aprob_mes + n_rech_mes
        pct_aprob_mes = round(n_aprob_mes / total_decididas_mes, 4) if total_decididas_mes else None
        M["pct_aprobacion"] = dict(
            ayer=None, semana=None, mes=pct_aprob_mes,
            extra=(f"{n_aprob_mes} de {total_decididas_mes} decisiones del mes"
                   if total_decididas_mes else "Sin decisiones registradas este mes"),
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )
        M["agendas_totales"] = dict(
            ayer=_contar("Fecha agenda visita", ayer_emb, ayer_emb),
            semana=_contar("Fecha agenda visita", semana_ini_emb, hoy_emb),
            mes=_contar("Fecha agenda visita", mes_ini_emb, hoy_emb),
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )
        M["agendas_hoy"] = dict(
            ayer=None, semana=None, mes=_contar("Fecha agenda visita", hoy_emb, hoy_emb),
            extra="Snapshot de hoy (no acumulado del mes)",
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )
        cumplida = lambda m: m[m["Estado agenda"] == "Cumplida"]
        n_agendas_ayer = _contar("Fecha agenda visita", ayer_emb, ayer_emb)
        n_cumplidas_ayer = _contar("Fecha agenda visita", ayer_emb, ayer_emb, cumplida)
        M["agendas_cumplidas_ayer"] = dict(
            ayer=n_cumplidas_ayer,
            semana=_contar("Fecha agenda visita", semana_ini_emb, hoy_emb, cumplida),
            mes=_contar("Fecha agenda visita", mes_ini_emb, hoy_emb, cumplida),
            extra=f"{n_cumplidas_ayer} de {n_agendas_ayer} programadas ayer",
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )
        no_cumplida = lambda m: m[m["Estado agenda"] == "No cumplida"]
        M["agendas_incumplidas"] = dict(
            ayer=_contar("Fecha agenda visita", ayer_emb, ayer_emb, no_cumplida),
            semana=_contar("Fecha agenda visita", semana_ini_emb, hoy_emb, no_cumplida),
            mes=_contar("Fecha agenda visita", mes_ini_emb, hoy_emb, no_cumplida),
            fuente=FUENTE_EMBUDO, corte=str(hoy_emb),
        )

    return dict(metricas=M, inv=inv, rec=rec, conc=conc, hoy_recaudo=hoy_recaudo,
                hoy_inv=hoy_inv, hoy_inv_txt=hoy_inv_txt)
