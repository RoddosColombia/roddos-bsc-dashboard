"""Contraseña compartida de directores (Nivel 2, Fase 2) para Tesorería, RRHH y cargas restringidas."""
import hmac

import streamlit as st


def clave_correcta(ingresada, esperada):
    return bool(esperada) and hmac.compare_digest(ingresada.encode(), esperada.encode())


def _clave_configurada():
    try:
        return st.secrets["acceso"]["clave_directores"]
    except (FileNotFoundError, KeyError):
        return ""


def formulario_director(motivo="Esta sección es solo para directores."):
    """Devuelve True si la sesión ya está desbloqueada; si no, muestra el formulario."""
    if st.session_state.get("es_director"):
        return True
    esperada = _clave_configurada()
    if not esperada:
        st.error("🔒 La contraseña de directores no está configurada en secrets.toml — sección cerrada.")
        return False
    with st.form("form_clave_directores"):
        st.markdown(f"🔒 {motivo}")
        ingresada = st.text_input("Contraseña de directores", type="password", key="clave_directores")
        enviado = st.form_submit_button("Entrar")
    if enviado:
        if clave_correcta(ingresada, esperada):
            st.session_state["es_director"] = True
            st.rerun()
        st.error("Contraseña incorrecta.")
    return False


def exigir_director():
    if not formulario_director():
        st.stop()
