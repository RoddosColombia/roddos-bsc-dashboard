import os
import shutil
import datetime
import openpyxl
import streamlit as st

from pymongo.errors import PyMongoError

import acceso
import data_sources as ds
import respaldo
import validators as val

st.set_page_config(page_title="Actualizar datos — RODDOS BSC", layout="wide", page_icon="📤")

st.title("📤 Actualizar datos")
st.caption(
    "RODDOS BSC vive en Streamlit Community Cloud, que no tiene acceso a OneDrive/SharePoint. "
    "Por eso cada tablero se alimenta de la última versión que se suba aquí — no hay conexión en vivo. "
    "Sube el archivo real (el mismo que ya manejas), no una versión reducida; cada carga reemplaza "
    "por completo los datos anteriores. Antes de reemplazar, se guarda una copia de la versión "
    "anterior (solo 1, no se acumula historial) por si hay que deshacer una carga equivocada."
)

if ds.db_respaldo() is None:
    st.warning("Respaldo en la nube: **no configurado**. Lo que subas se pierde si el servidor se reinicia.")
else:
    st.info("Respaldo en la nube: **activo**. Cada carga queda guardada y se recupera sola tras un reinicio.")

VERSIONES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_raw", "versiones")
os.makedirs(VERSIONES_DIR, exist_ok=True)

FUENTES = [
    dict(nombre="Recaudo", archivo=ds.F_RECAUDO, validador=val.validar_recaudo,
         cache=ds.leer_recaudo, descripcion="Proyeccion_Recaudo.xlsx — usado en la página principal (rubros 14 a 19)."),
    dict(nombre="Inventario / Ventas", archivo=ds.F_INVENTARIO, validador=val.validar_inventario,
         cache=ds.leer_inventario, descripcion="Inventario_2026.xlsx — usado en la página principal (rubros 8 a 13, 20, 21)."),
    dict(nombre="Conciliación SISMO ↔ Wava", archivo=ds.F_CONCILIACION, validador=val.validar_conciliacion,
         cache=ds.leer_conciliacion, solo_directores=True, descripcion="Cruce_SISMO_Wava.xlsx — panel de conciliación en la página principal."),
    dict(nombre="Tesorería", archivo=ds.F_TESORERIA, validador=val.validar_tesoreria,
         cache=ds.leer_tesoreria, solo_directores=True, descripcion="Flujo_Pagos_Deudas.xlsx — página Tesorería."),
    dict(nombre="RRHH / Nómina", archivo=ds.F_RRHH, validador=val.validar_rrhh,
         cache=ds.leer_rrhh, solo_directores=True, descripcion="Control_RRHH_Nomina_RODDOS_2026.xlsx — página RRHH."),
    dict(nombre="Embudo comercial (Marketing / leads)", archivo=ds.F_EMBUDO, validador=val.validar_embudo,
         cache=ds.leer_embudo, descripcion="Embudo_Comercial_RODDOS.xlsx — rubros 1 a 7 de la página principal. "
                                            "Este es el único que empieza vacío: descarga la plantilla en la "
                                            "página principal si aún no la tienes."),
    dict(nombre="Metas del mes", archivo=ds.F_METAS, validador=val.validar_metas,
         cache=ds.leer_metas, solo_directores=True, descripcion="Metas_RODDOS.xlsx — objetivos que fija la dirección cada mes "
                                           "(ventas, % aprobación, % agendas, tope de mora, gasto fijo). "
                                           "Agrega una fila nueva cada mes, no borres las anteriores."),
]


def _ultima_actualizacion(path):
    if not os.path.exists(path):
        return "Nunca se ha cargado"
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    return ts.strftime("%d/%m/%Y %H:%M")


es_director = acceso.formulario_director(
    "Tesorería, RRHH, Metas y Conciliación solo los suben los directores. "
    "Recaudo, Inventario y Embudo no necesitan contraseña."
)

for fuente in FUENTES:
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader(fuente["nombre"])
            st.caption(fuente["descripcion"])
            st.caption(f"Última carga: **{_ultima_actualizacion(fuente['archivo'])}**")
        with c2:
            if fuente.get("solo_directores") and not es_director:
                st.caption("🔒 Solo directores — ingresa la contraseña arriba.")
                continue
            subido = st.file_uploader(
                f"Subir {os.path.basename(fuente['archivo'])}",
                type="xlsx", key=f"up_{fuente['nombre']}", label_visibility="collapsed",
            )
            if subido is not None:
                try:
                    wb_check = openpyxl.load_workbook(subido)
                    errores = fuente["validador"](wb_check)
                    if errores:
                        st.error(f"No se cargó — {len(errores)} problema(s) encontrado(s):")
                        for e in errores[:20]:
                            st.caption(f"• {e}")
                        if len(errores) > 20:
                            st.caption(f"... y {len(errores) - 20} más. Corrige y vuelve a subir.")
                    else:
                        if os.path.exists(fuente["archivo"]):
                            respaldo = os.path.join(VERSIONES_DIR, os.path.basename(fuente["archivo"]) + ".anterior.xlsx")
                            shutil.copy2(fuente["archivo"], respaldo)
                        subido.seek(0)
                        contenido = subido.read()
                        with open(fuente["archivo"], "wb") as f:
                            f.write(contenido)
                        fuente["cache"].clear()
                        db = ds.db_respaldo()
                        if db is None:
                            st.rerun()
                        try:
                            respaldo.guardar(db, os.path.basename(fuente["archivo"]), contenido)
                            st.rerun()
                        except PyMongoError as e:
                            st.error(f"Se cargó, pero NO quedó respaldado en la nube: {e}. "
                                     "Vuelve a subirlo en unos minutos.")
                except Exception as e:
                    st.error(f"No se pudo leer el archivo: {e}")
