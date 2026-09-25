import os
import sys

import pytest
from streamlit.testing.v1 import AppTest

RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, RAIZ)
import acceso

CLAVE = "clave-de-prueba"


def _pagina(nombre, clave_configurada=CLAVE):
    at = AppTest.from_file(os.path.join(RAIZ, "pages", nombre), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": clave_configurada}
    return at


def _texto(at):
    partes = []
    for tipo in ("title", "subheader", "markdown", "caption", "info", "warning", "error", "success"):
        partes += [str(e.value) for e in getattr(at, tipo)]
    return "\n".join(partes)


def _entrar(at, clave):
    at.text_input(key="clave_directores").input(clave)
    at.button[0].click()
    at.run()


def test_clave_correcta():
    assert acceso.clave_correcta("abc", "abc")
    assert not acceso.clave_correcta("abd", "abc")
    assert not acceso.clave_correcta("", "abc")
    assert not acceso.clave_correcta("", "")


@pytest.mark.parametrize("pagina, marca", [
    ("1_Tesoreria.py", "Tesorería y flujo de caja"),
    ("2_RRHH.py", "RRHH — Nómina y equipo"),
])
def test_pagina_restringida_sin_clave_no_muestra_nada(pagina, marca):
    at = _pagina(pagina)
    at.run()
    assert not at.exception
    assert marca not in _texto(at)


@pytest.mark.parametrize("pagina, marca", [
    ("1_Tesoreria.py", "Tesorería y flujo de caja"),
    ("2_RRHH.py", "RRHH — Nómina y equipo"),
])
def test_pagina_restringida_clave_equivocada(pagina, marca):
    at = _pagina(pagina)
    at.run()
    _entrar(at, "otra")
    assert marca not in _texto(at)
    assert "incorrecta" in _texto(at)


@pytest.mark.parametrize("pagina, marca", [
    ("1_Tesoreria.py", "Tesorería y flujo de caja"),
    ("2_RRHH.py", "RRHH — Nómina y equipo"),
])
def test_pagina_restringida_clave_correcta(pagina, marca):
    at = _pagina(pagina)
    at.run()
    _entrar(at, CLAVE)
    assert not at.exception
    assert marca in _texto(at)


def test_sin_clave_configurada_queda_cerrado():
    at = _pagina("1_Tesoreria.py", clave_configurada="")
    at.run()
    assert "Tesorería y flujo de caja" not in _texto(at)
    assert "no está configurada" in _texto(at)


def test_vista_reunion_oculta_caja_sin_clave():
    at = _pagina("3_Vista_Reunion.py")
    at.run()
    assert not at.exception
    assert "1 · Demanda" in _texto(at)
    assert "Caja disponible total" not in _texto(at)


def test_vista_reunion_muestra_caja_con_clave():
    at = _pagina("3_Vista_Reunion.py")
    at.run()
    _entrar(at, CLAVE)
    assert "Caja disponible total" in _texto(at)


def test_actualizar_datos_bloquea_archivos_de_directores():
    at = _pagina("0_Actualizar_Datos.py")
    at.run()
    assert not at.exception
    assert _texto(at).count("Solo directores") == 4


def test_actualizar_datos_desbloquea_con_clave():
    at = _pagina("0_Actualizar_Datos.py")
    at.run()
    _entrar(at, CLAVE)
    assert _texto(at).count("Solo directores") == 0
