"""Cada página se abre como lo haría un navegador (streamlit.testing.AppTest) en tres
escenarios: sin datos, con los 8 Excel de prueba, y con un archivo opcional dañado.
En ninguno puede aparecer un error de Python en pantalla."""
import os

import pytest
from streamlit.testing.v1 import AppTest

import fixtures_excel as fx

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLAVE = "clave-de-prueba"
PAGINAS = ["app.py", "pages/0_Actualizar_Datos.py", "pages/1_Tesoreria.py", "pages/2_RRHH.py",
           "pages/3_Vista_Reunion.py", "pages/4_Agenda.py", "pages/5_Historico.py"]


def abrir(pagina, como_director=True):
    at = AppTest.from_file(os.path.join(RAIZ, pagina), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": CLAVE}
    at.run()
    hay_formulario = any(t.key == "clave_directores" for t in at.text_input)
    if como_director and hay_formulario:
        at.text_input(key="clave_directores").input(CLAVE)
        at.button[0].click()
        at.run()
    return at


def texto(at):
    partes = []
    for tipo in ("title", "subheader", "markdown", "caption", "info", "warning", "error", "success"):
        partes += [str(e.value) for e in getattr(at, tipo)]
    return "\n".join(partes)


def sin_errores(at):
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize("pagina", PAGINAS)
def test_sin_datos_ninguna_pagina_se_cae(pagina):
    sin_errores(abrir(pagina))


@pytest.mark.parametrize("pagina", PAGINAS)
def test_con_datos_ninguna_pagina_se_cae(datos_prueba, pagina):
    at = abrir(pagina)
    sin_errores(at)
    # st.error se usa también para alertas de negocio (p. ej. vacaciones vencidas en RRHH);
    # lo que no puede aparecer es el mensaje de "no se pudieron leer los datos"
    assert not any("No se pudieron leer" in str(e.value) for e in at.error), [e.value for e in at.error]


def test_pagina_principal_muestra_los_numeros(datos_prueba):
    t = texto(abrir("app.py"))
    assert "Recaudo del mes" in t
    assert "Cobranza de la semana" in t
    assert "1 · Demanda" in t


def test_pagina_principal_guarda_la_foto_del_historico(datos_prueba):
    import historico

    abrir("app.py")
    fotos = historico.AlmacenLocal().listar()
    assert fotos[-1]["periodo"] == fx.HOY.strftime("%Y-%m")          # la foto en vivo del mes de trabajo
    assert not historico.es_reconstruida(fotos[-1])
    assert set(fotos[-1]["datos"]["_cortes"]) == {"recaudo", "inventario", "embudo"}
    assert all(historico.es_reconstruida(f) for f in fotos[:-1])     # los anteriores, reconstruidos


@pytest.mark.parametrize("nombre, dañar", [
    ("Metas_RODDOS.xlsx", lambda wb: setattr(wb["Metas"], "title", "Hoja1")),
    ("Cruce_SISMO_Wava.xlsx", lambda wb: wb.remove(wb["Pagos sin registrar SISMO"])),
    ("Embudo_Comercial_RODDOS.xlsx", lambda wb: wb["Embudo_Diario"].delete_cols(8)),
])
def test_archivo_opcional_dañado_solo_apaga_su_seccion(datos_prueba, reemplazar, nombre, dañar):
    """Simula un archivo que llegó a data_raw sin pasar por el validador (por ejemplo,
    restaurado de un respaldo viejo). La página muestra un aviso y lo demás sigue."""
    wb = fx.ARCHIVOS[nombre]()
    dañar(wb)
    reemplazar(nombre, wb)
    at = abrir("app.py")
    sin_errores(at)
    assert any(nombre in str(w.value) for w in at.warning), [w.value for w in at.warning]
    assert "Recaudo del mes" in texto(at)


def test_archivo_principal_dañado_muestra_mensaje_claro(datos_prueba, reemplazar):
    wb = fx.wb_recaudo()
    wb.remove(wb["Detalle Cuotas"])
    reemplazar("Proyeccion_Recaudo.xlsx", wb)
    at = abrir("app.py")
    sin_errores(at)
    assert at.error and "Proyeccion_Recaudo.xlsx" in at.error[0].value


def test_cobranza_tolera_hojas_de_detalle_faltantes(datos_prueba, reemplazar):
    """La cobranza calcula desde el detalle cuando el Dashboard no está recalculado;
    si además falta una hoja de detalle, muestra lo que hay en vez de caerse."""
    wb = fx.wb_cobranza()
    wb.remove(wb["Cuotas de la semana"])
    reemplazar("Cobranza_Semanal.xlsx", wb)
    at = abrir("app.py")
    sin_errores(at)
    assert "Cobranza de la semana" in texto(at)


# ---------------------------------------------------------------- Agenda: días clicables en la vista Mes

def _agenda_en_mes_de_prueba():
    """Abre la Agenda en vista Mes, en el mes de los datos de prueba (octubre 2026)."""
    import datetime

    hoy = datetime.date.today()
    at = AppTest.from_file(os.path.join(RAIZ, "pages/4_Agenda.py"), default_timeout=60)
    at.session_state["ag_vista"] = "Mes"
    at.session_state["ag_mes"] = (fx.HOY.year - hoy.year) * 12 + (fx.HOY.month - hoy.month)
    return at.run()


def _seleccionado(at):
    return at.session_state["ag_dia_sel"]


def _detalle(at):
    """Texto de la tarjeta de detalle del día (la que va debajo del calendario)."""
    return " ".join(m.value for m in at.markdown if "cliente(s)" in m.value or "0 clientes" in m.value)


def test_agenda_mes_cada_dia_es_clicable_y_muestra_colores(datos_prueba):
    at = _agenda_en_mes_de_prueba()
    sin_errores(at)
    assert len([b for b in at.button if b.key.startswith("agdia_")]) == 31      # octubre: un botón por día
    celdas = [m.value for m in at.markdown if "class='ag-celda'" in m.value]
    assert len(celdas) == 31
    # Lead 003 (4 oct) "No vino": su punto va en rojo dentro de la celda del día
    import utils
    celda_4 = next(c for c in celdas if "Lead 003" in c)
    assert f"background:{utils.ROJO}" in celda_4


def test_agenda_mes_clic_en_un_dia_muestra_sus_clientes(datos_prueba):
    import datetime

    at = _agenda_en_mes_de_prueba()
    at.button(key="agdia_20261004").click().run()
    sin_errores(at)
    assert _seleccionado(at) == datetime.date(2026, 10, 4)
    assert "Lead 003" in _detalle(at) and "No vino" in _detalle(at)
    assert at.selectbox(key="ag_dia_lista").value == datetime.date(2026, 10, 4)   # la lista se sincroniza

    at.button(key="agdia_20261020").click().run()               # un día sin visitas
    assert _seleccionado(at) == datetime.date(2026, 10, 20)
    assert "Sin visitas agendadas este día" in _detalle(at)
    assert at.selectbox(key="ag_dia_lista").value is None       # no está en la lista: queda vacía


def test_agenda_mes_lista_desplegable_consolidada(datos_prueba):
    import datetime

    at = _agenda_en_mes_de_prueba()
    lista = at.selectbox(key="ag_dia_lista")
    assert lista.label == "Ver clientes de un día"
    assert len(lista.options) == 4                              # solo los días con visitas
    lista.select(datetime.date(2026, 10, 9)).run()
    sin_errores(at)
    assert _seleccionado(at) == datetime.date(2026, 10, 9)      # elegir en la lista también marca el día
    assert "Lead 009" in _detalle(at)


def test_agenda_mes_cambiar_de_mes_no_arrastra_el_dia(datos_prueba):
    at = _agenda_en_mes_de_prueba()
    at.button(key="agdia_20261004").click().run()
    at.button(key="mes_prev").click().run()                     # septiembre: sin visitas de prueba
    sin_errores(at)
    assert _seleccionado(at) is None                            # el 4 de octubre no se arrastra
    assert "Este mes no tiene visitas agendadas" in texto(at)


# ---------------------------------------------------------------- Agenda: botón Hoy

def test_agenda_boton_hoy_en_semana(datos_prueba):
    import datetime

    at = AppTest.from_file(os.path.join(RAIZ, "pages/4_Agenda.py"), default_timeout=60)
    at.session_state["ag_vista"] = "Semana"                     # la vista por defecto ahora es Mes
    at.run()
    assert at.button(key="sem_hoy").disabled                    # ya estás en la semana actual
    at.button(key="sem_prev").click().run()
    at.button(key="sem_prev").click().run()
    assert at.session_state["ag_sem"] == -2 and not at.button(key="sem_hoy").disabled
    at.button(key="sem_hoy").click().run()
    sin_errores(at)
    assert at.session_state["ag_sem"] == 0
    hoy = datetime.date.today()
    lunes = hoy - datetime.timedelta(days=hoy.weekday())
    assert f"{lunes:%d/%m}" in texto(at)


def test_agenda_boton_hoy_en_mes(datos_prueba):
    import datetime

    at = _agenda_en_mes_de_prueba()
    at.button(key="mes_prev").click().run()
    at.button(key="mes_hoy").click().run()
    sin_errores(at)
    assert at.session_state["ag_mes"] == 0
    assert at.session_state["ag_dia_sel"] == datetime.date.today()   # queda marcado el día de hoy
    assert at.button(key="mes_hoy").disabled


def test_agenda_abre_en_la_vista_mes(datos_prueba):
    at = AppTest.from_file(os.path.join(RAIZ, "pages/4_Agenda.py"), default_timeout=60).run()
    sin_errores(at)
    assert any(b.key == "mes_hoy" for b in at.button)          # la navegación del mes
    assert sum(1 for b in at.button if b.key.startswith("agdia_")) >= 28
