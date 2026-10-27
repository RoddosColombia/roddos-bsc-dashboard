import datetime
import os

import streamlit as st

import acceso
import carga
import formatos
import data_sources as ds
from utils import estilo_roddos, encabezado

st.set_page_config(page_title="Actualizar datos — RODDOS BSC", layout="wide", page_icon="📤")
estilo_roddos()
encabezado("Actualizar datos")

import sharepoint  # noqa: E402

_cfg_sp = sharepoint.config()
if _cfg_sp is None:
    st.caption(
        "Cada tablero se alimenta de la última versión que se suba aquí. "
        "Sube el archivo real (el mismo que ya manejas), no una versión reducida; cada carga reemplaza "
        "por completo los datos anteriores. Antes de reemplazar, se guarda una copia de la versión "
        "anterior (solo 1, no se acumula historial) por si hay que deshacer una carga equivocada."
    )
else:
    _ZONA = datetime.timezone(datetime.timedelta(hours=-5))  # Colombia, sin horario de verano

    def _hora(iso):
        try:
            return datetime.datetime.fromisoformat(iso).astimezone(_ZONA).strftime("%d/%m %H:%M")
        except (TypeError, ValueError):
            return "—"

    with st.container(border=True, key="vidrio_sharepoint"):
        st.subheader("🔄 Conexión con SharePoint")
        if "_error" in _cfg_sp:
            st.error(_cfg_sp["_error"])
        else:
            st.caption(f"El tablero revisa la carpeta **{_cfg_sp['carpeta']}** cada "
                       f"{int(float(_cfg_sp.get('intervalo_minutos', 10)))} minutos y carga solo los archivos que "
                       "cambiaron, con las mismas validaciones de la carga manual. Si un archivo trae errores, se "
                       "sigue mostrando la última versión buena. La carga manual de abajo queda como plan B.")
            if st.button("🔄 Actualizar ahora desde SharePoint", key="sp_ahora"):
                with st.spinner("Revisando SharePoint…"):
                    _estado = sharepoint.sincronizar_si_toca(forzar=True)
            else:
                _estado = sharepoint.sincronizar_si_toca()
            _estado = _estado or {}
            if _estado.get("_error"):
                st.error(f"No se pudo revisar SharePoint: {_estado['_error']}")
            st.caption(f"Última revisión: {_hora(_estado.get('_revisado_en'))}")
            for _f in carga.fuentes():
                _v = _estado.get(_f["nombre"], {})
                _r = _v.get("resultado")
                if _r == sharepoint.OK:
                    _txt = f"✅ Al día · guardado en SharePoint el {_hora(_v.get('modificado'))}"
                elif _r == sharepoint.RECHAZADO:
                    _txt = (f"⛔ Con errores (guardado el {_hora(_v.get('modificado'))}) — "
                            "se sigue mostrando la versión anterior")
                elif _r == sharepoint.EN_EDICION:
                    _txt = (f"✏️ Recién guardado ({_hora(_v.get('modificado'))}) — se toma en unos minutos, "
                            "o usa el botón para tomarlo ya")
                elif _r == sharepoint.NO_ENCONTRADO:
                    _txt = "❓ No está en la carpeta de SharePoint"
                else:
                    _txt = "— Sin revisar todavía"
                st.markdown(f"**{_f['nombre']}** · {_txt}")
                if _r == sharepoint.RECHAZADO and _v.get("errores"):
                    with st.expander(f"Ver los {len(_v['errores'])} problema(s) de {_v.get('archivo_sharepoint')}"):
                        for _e in _v["errores"]:
                            st.caption(f"• {_e}")

if ds.db_respaldo() is None:
    st.warning("Respaldo en la nube: **no configurado**. Lo que subas se pierde si el servidor se reinicia.")
else:
    st.info("Respaldo en la nube: **activo**. Cada carga queda guardada y se recupera sola tras un reinicio.")

FUENTES = carga.fuentes()


def _ultima_actualizacion(path):
    """Fecha y hora (de Colombia) de la última carga. Con respaldo en Mongo se usa la fecha real de
    la carga: la del archivo en disco cambia cada vez que el servidor se reinicia y lo restaura."""
    if not os.path.exists(path):
        return "Nunca se ha cargado"
    momento = None
    db = ds.db_respaldo()
    if db is not None:
        try:
            doc = db.archivos.find_one({"_id": os.path.basename(path)}, {"subido_en": 1})
            momento = doc.get("subido_en") if doc else None
        except Exception:
            momento = None
    if momento is None:
        momento = datetime.datetime.fromtimestamp(os.path.getmtime(path), datetime.timezone.utc)
    return formatos.a_hora_colombia(momento).strftime("%d/%m/%Y %H:%M")


es_director = acceso.formulario_director(
    "Tesorería, RRHH, Metas y Conciliación solo los suben los directores. "
    "Recaudo, Inventario y Embudo no necesitan contraseña."
)

for fuente in FUENTES:
    with st.container(border=True, key=f"vidrio_fuente_{fuente['clave']}"):
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
            # El cargador conserva el archivo entre recargas de la página: sin esta marca,
            # cada recarga lo volvería a procesar (y st.rerun() lo haría en bucle).
            clave_hecho = f"cargado_{fuente['nombre']}"
            id_subido = (getattr(subido, "file_id", None) or (subido.name, subido.size)) if subido else None
            if subido is not None and st.session_state.get(clave_hecho) == id_subido:
                st.success("✅ Cargado. El tablero ya muestra estos datos.")
            elif subido is not None:
                try:
                    subido.seek(0)
                    resultado = carga.procesar(fuente, subido.read())  # mismo camino que SharePoint
                    if not resultado["ok"]:
                        errores = resultado["errores"]
                        st.error(f"No se cargó — {len(errores)} problema(s) encontrado(s):")
                        for e in errores[:20]:
                            st.caption(f"• {e}")
                        if len(errores) > 20:
                            st.caption(f"... y {len(errores) - 20} más. Corrige y vuelve a subir.")
                    else:
                        st.session_state[clave_hecho] = id_subido
                        if resultado["aviso"]:
                            st.error(resultado["aviso"] + " Vuelve a subirlo en unos minutos.")
                        else:
                            st.rerun()
                except Exception as e:
                    st.error(f"No se pudo leer el archivo: {e}")
