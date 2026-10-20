"""Conexión con SharePoint, probada sin credenciales reales.

- ClienteGraph contra un Microsoft Graph simulado (sesión HTTP falsa).
- sincronizar() contra una carpeta de SharePoint simulada con los Excel de prueba.
"""
import datetime as dt
import io
import os

import pytest
from streamlit.testing.v1 import AppTest

import data_sources as ds
import fixtures_excel as fx
import sharepoint as sp

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AHORA = dt.datetime(2026, 10, 20, 15, 0, tzinfo=dt.timezone.utc)
HACE_UNA_HORA = dt.datetime(2026, 1, 15, 12, 0, tzinfo=dt.timezone.utc)  # fecha fija en el pasado (también para el reloj real)


def _bytes(wb):
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


# ---------------------------------------------------------------- carpeta simulada

class CarpetaFalsa:
    """Imita ClienteGraph: los 8 Excel de prueba con los nombres que tienen en SharePoint."""

    def __init__(self):
        self.archivos = {}
        self.descargas = []
        for nombre, fabrica in fx.ARCHIVOS.items():
            nombre_sp = "Flujo de pagos deudas.xlsx" if nombre == "Flujo_Pagos_Deudas.xlsx" else nombre
            self.poner(nombre_sp, _bytes(fabrica()), HACE_UNA_HORA)

    def poner(self, nombre, contenido, modificado, etag=None):
        version = self.archivos.get(nombre, {}).get("version", 0) + 1
        self.archivos[nombre] = dict(contenido=contenido, modificado=modificado, version=version,
                                     etag=etag or f'"{nombre}-{version}"')

    def listar(self):
        return [dict(id=n, nombre=n, etag=a["etag"], modificado=a["modificado"], tamano=len(a["contenido"]))
                for n, a in self.archivos.items()]

    def descargar(self, item_id):
        self.descargas.append(item_id)
        return self.archivos[item_id]["contenido"]


def test_primera_sincronizacion_carga_los_8(_aislar):
    carpeta = CarpetaFalsa()
    estado = sp.sincronizar(carpeta, ahora=AHORA)
    assert len(carpeta.descargas) == 8
    assert all(estado[f["nombre"]]["resultado"] == sp.OK for f in sp.carga.fuentes())
    assert estado["Tesorería"]["archivo_sharepoint"] == "Flujo de pagos deudas.xlsx"   # nombre de SharePoint
    assert ds.leer_tesoreria()["dashboard"]["corte_fecha"] == fx.HOY


def test_sin_cambios_no_descarga_nada(_aislar):
    carpeta = CarpetaFalsa()
    sp.sincronizar(carpeta, ahora=AHORA)
    carpeta.descargas.clear()
    sp.sincronizar(carpeta, ahora=AHORA + dt.timedelta(minutes=10))
    assert carpeta.descargas == []


def test_solo_descarga_lo_que_cambio(_aislar):
    carpeta = CarpetaFalsa()
    sp.sincronizar(carpeta, ahora=AHORA)
    carpeta.descargas.clear()
    carpeta.poner("Metas_RODDOS.xlsx", _bytes(fx.wb_metas()), AHORA)
    sp.sincronizar(carpeta, ahora=AHORA + dt.timedelta(minutes=10))
    assert carpeta.descargas == ["Metas_RODDOS.xlsx"]


def test_archivo_con_errores_se_rechaza_y_queda_el_anterior(_aislar):
    carpeta = CarpetaFalsa()
    sp.sincronizar(carpeta, ahora=AHORA)
    bueno = open(ds.F_RECAUDO, "rb").read()
    malo = fx.wb_recaudo()
    malo.remove(malo["Detalle Cuotas"])
    carpeta.poner("Proyeccion_Recaudo.xlsx", _bytes(malo), AHORA)
    estado = sp.sincronizar(carpeta, ahora=AHORA + dt.timedelta(minutes=10))
    assert estado["Recaudo"]["resultado"] == sp.RECHAZADO and estado["Recaudo"]["errores"]
    assert open(ds.F_RECAUDO, "rb").read() == bueno
    assert sp.rechazados(estado)[0][1] == "Proyeccion_Recaudo.xlsx"
    # no se vuelve a descargar mientras no cambie
    carpeta.descargas.clear()
    sp.sincronizar(carpeta, ahora=AHORA + dt.timedelta(minutes=20))
    assert carpeta.descargas == []


def test_recien_guardado_espera_salvo_que_se_fuerce(_aislar):
    carpeta = CarpetaFalsa()
    carpeta.poner("Metas_RODDOS.xlsx", _bytes(fx.wb_metas()), AHORA - dt.timedelta(minutes=2))
    estado = sp.sincronizar(carpeta, espera_minutos=5, ahora=AHORA)
    assert estado["Metas del mes"]["resultado"] == sp.EN_EDICION
    assert "Metas_RODDOS.xlsx" not in carpeta.descargas
    estado = sp.sincronizar(carpeta, espera_minutos=5, forzar=True, ahora=AHORA)
    assert estado["Metas del mes"]["resultado"] == sp.OK


def test_archivo_que_no_esta_en_la_carpeta(_aislar):
    carpeta = CarpetaFalsa()
    del carpeta.archivos["Cobranza_Semanal.xlsx"]
    assert sp.sincronizar(carpeta, ahora=AHORA)["Cobranza semanal"]["resultado"] == sp.NO_ENCONTRADO


def test_si_se_pierden_los_archivos_locales_se_vuelven_a_bajar(_aislar):
    """Reinicio del servidor sin respaldo: el disco queda vacío aunque el estado diga OK."""
    carpeta = CarpetaFalsa()
    sp.sincronizar(carpeta, ahora=AHORA)
    os.remove(ds.F_RECAUDO)
    carpeta.descargas.clear()
    sp.sincronizar(carpeta, ahora=AHORA + dt.timedelta(minutes=10))
    assert carpeta.descargas == ["Proyeccion_Recaudo.xlsx"]


def test_sin_conexion_no_tumba_nada(_aislar):
    class SinRed:
        def listar(self):
            raise sp.ErrorSharePoint("No se pudo iniciar sesión en Microsoft (401).")
    estado = sp.sincronizar(SinRed(), ahora=AHORA)
    assert "401" in estado["_error"]


# ---------------------------------------------------------------- Microsoft Graph simulado

class Respuesta:
    def __init__(self, status, datos=None, contenido=b""):
        self.status_code, self._datos, self.content = status, datos, contenido

    def json(self):
        return self._datos


class GraphFalso:
    def __init__(self, token_status=200, listado_status=200):
        self.peticiones = []
        self.token_status, self.listado_status = token_status, listado_status

    def post(self, url, data=None, timeout=None):
        self.peticiones.append(("POST", url, data))
        return Respuesta(self.token_status, {"access_token": "TOKEN", "expires_in": 3600})

    def get(self, url, headers=None, timeout=None, stream=False):
        self.peticiones.append(("GET", url, headers))
        if url.endswith("/sites/roddossas.sharepoint.com:/sites/RODDOSSAS"):
            return Respuesta(200, {"id": "SITIO-1"})
        if ":/children" in url and "pagina2" not in url:
            return Respuesta(self.listado_status, {"value": [
                {"id": "A", "name": "Metas_RODDOS.xlsx", "eTag": '"e1"', "size": 10,
                 "lastModifiedDateTime": "2026-10-20T13:00:00Z", "file": {}},
                {"id": "D", "name": "Subcarpeta", "eTag": '"e2"', "lastModifiedDateTime": "2026-10-20T13:00:00Z",
                 "folder": {}},
            ], "@odata.nextLink": "https://graph.microsoft.com/v1.0/pagina2"})
        if "pagina2" in url:
            return Respuesta(200, {"value": [{"id": "B", "name": "Cobranza_Semanal.xlsx", "eTag": '"e3"', "size": 5,
                                              "lastModifiedDateTime": "2026-10-19T20:00:00Z", "file": {}}]})
        if url.endswith("/drive/items/A/content"):
            return Respuesta(200, contenido=b"EXCEL")
        return Respuesta(404)


def _cliente(graph):
    return sp.ClienteGraph("TENANT", "CLIENTE", "SECRETO", "roddossas.sharepoint.com:/sites/RODDOSSAS",
                           "RODDOS/8. DASHBOARD BSC RODDOS/1 Fuentes al día", sesion=graph)


def test_cliente_inicia_sesion_lista_y_descarga():
    graph = GraphFalso()
    c = _cliente(graph)
    items = c.listar()
    assert [i["nombre"] for i in items] == ["Metas_RODDOS.xlsx", "Cobranza_Semanal.xlsx"]   # sin la subcarpeta, con página 2
    assert items[0]["modificado"] == dt.datetime(2026, 10, 20, 13, 0, tzinfo=dt.timezone.utc)
    assert c.descargar("A") == b"EXCEL"
    post = [p for p in graph.peticiones if p[0] == "POST"]
    assert len(post) == 1                                                       # el token se reutiliza
    assert post[0][1] == "https://login.microsoftonline.com/TENANT/oauth2/v2.0/token"
    assert post[0][2]["grant_type"] == "client_credentials"
    assert post[0][2]["scope"] == "https://graph.microsoft.com/.default"
    listado = next(p for p in graph.peticiones if ":/children" in p[1])
    assert "/sites/SITIO-1/drive/root:/RODDOS/8.%20DASHBOARD%20BSC%20RODDOS/1%20Fuentes%20al%20d%C3%ADa:/children" in listado[1]
    assert listado[2]["Authorization"] == "Bearer TOKEN"


@pytest.mark.parametrize("token, listado, esperado", [(401, 200, "iniciar sesión"), (200, 403, "negó el acceso"),
                                                      (200, 404, "No se encontró")])
def test_cliente_explica_los_errores(token, listado, esperado):
    with pytest.raises(sp.ErrorSharePoint, match=esperado):
        _cliente(GraphFalso(token, listado)).listar()


# ---------------------------------------------------------------- en las páginas

SECRETS_SP = {"activo": True, "tenant_id": "T", "client_id": "C", "client_secret": "S",
              "sitio": "roddossas.sharepoint.com:/sites/RODDOSSAS", "carpeta": "RODDOS/x", "espera_minutos": 0}


def _abrir(pagina, monkeypatch, carpeta, secrets=True):
    monkeypatch.setattr(sp, "crear_cliente", lambda cfg: carpeta)
    at = AppTest.from_file(os.path.join(RAIZ, pagina), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    if secrets:
        at.secrets["sharepoint"] = SECRETS_SP
    return at.run()


def test_pagina_principal_se_llena_sola_desde_sharepoint(_aislar, monkeypatch):
    at = _abrir("app.py", monkeypatch, CarpetaFalsa())           # data_raw empieza vacía
    assert not at.exception
    assert not any("Todavía no hay datos" in i.value for i in at.info)
    assert os.path.exists(ds.F_RECAUDO) and os.path.exists(ds.F_TESORERIA)


def test_pagina_principal_avisa_archivo_rechazado(_aislar, monkeypatch):
    carpeta = CarpetaFalsa()
    malo = fx.wb_embudo()
    malo["Embudo_Diario"].delete_cols(fx.EMBUDO_COLUMNAS.index("Decision") + 1)
    carpeta.poner("Embudo_Comercial_RODDOS.xlsx", _bytes(malo), HACE_UNA_HORA)
    at = _abrir("app.py", monkeypatch, carpeta)
    assert not at.exception
    assert any("Embudo_Comercial_RODDOS.xlsx" in w.value and "tiene errores" in w.value for w in at.warning)


def test_panel_en_actualizar_datos(_aislar, monkeypatch):
    at = _abrir("pages/0_Actualizar_Datos.py", monkeypatch, CarpetaFalsa())
    assert not at.exception
    assert any("Conexión con SharePoint" in s.value for s in at.subheader)
    estados = " ".join(m.value for m in at.markdown)
    assert estados.count("✅ Al día") == 8
    assert any(b.key == "sp_ahora" for b in at.button)


def test_sin_configuracion_todo_sigue_como_antes(_aislar, monkeypatch):
    at = _abrir("pages/0_Actualizar_Datos.py", monkeypatch, CarpetaFalsa(), secrets=False)
    assert not at.exception
    assert not any("Conexión con SharePoint" in s.value for s in at.subheader)
    assert not os.path.exists(ds.F_RECAUDO)


def test_secrets_incompletos_se_explican(_aislar, monkeypatch):
    monkeypatch.setattr(sp, "crear_cliente", lambda cfg: CarpetaFalsa())
    at = AppTest.from_file(os.path.join(RAIZ, "pages/0_Actualizar_Datos.py"), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    at.secrets["sharepoint"] = {"activo": True, "tenant_id": "T"}
    at.run()
    assert not at.exception
    assert any("client_id" in e.value for e in at.error)


# ---------------------------------------------------------------- archivos en otra carpeta

MAESTRO = "RODDOS/2. OPERACIONES/MOTOS/Inventario 2026.xlsx"


class CarpetaConMaestro(CarpetaFalsa):
    """La carpeta del dashboard tiene una copia VIEJA del inventario; el maestro vive en Operaciones."""

    def __init__(self):
        super().__init__()
        viejo = fx.wb_inventario()
        viejo["Dashboard"]["B7"] = 1                        # copia desactualizada: 1 venta
        self.poner("Inventario_2026.xlsx", _bytes(viejo), HACE_UNA_HORA)
        self.otras = {MAESTRO: dict(id="MAESTRO", contenido=_bytes(fx.wb_inventario()), etag='"m1"')}  # 12 ventas

    def obtener(self, ruta):
        if ruta not in self.otras:
            raise sp.ErrorSharePoint(f"No se encontró en SharePoint: {ruta}")
        a = self.otras[ruta]
        return dict(id=a["id"], nombre=ruta.rsplit("/", 1)[-1], etag=a["etag"], modificado=HACE_UNA_HORA,
                    tamano=len(a["contenido"]))

    def descargar(self, item_id):
        if item_id == "MAESTRO":
            self.descargas.append(item_id)
            return self.otras[MAESTRO]["contenido"]
        return super().descargar(item_id)


def test_inventario_desde_su_carpeta_real_y_no_la_copia_vieja(_aislar):
    carpeta = CarpetaConMaestro()
    estado = sp.sincronizar(carpeta, ahora=AHORA, rutas={"inventario": MAESTRO})
    assert estado["Inventario / Ventas"]["resultado"] == sp.OK
    assert estado["Inventario / Ventas"]["archivo_sharepoint"] == MAESTRO
    assert "MAESTRO" in carpeta.descargas and "Inventario_2026.xlsx" not in carpeta.descargas
    assert ds.leer_inventario()["hoy"]["vendidas_mes"] == 12      # el maestro, no la copia (1)


def test_sin_ruta_propia_usa_la_carpeta(_aislar):
    estado = sp.sincronizar(CarpetaConMaestro(), ahora=AHORA)
    assert estado["Inventario / Ventas"]["archivo_sharepoint"] == "Inventario_2026.xlsx"


def test_ruta_propia_inexistente_se_explica(_aislar):
    estado = sp.sincronizar(CarpetaConMaestro(), ahora=AHORA, rutas={"inventario": "RODDOS/no/existe.xlsx"})
    assert estado["Inventario / Ventas"]["resultado"] == sp.NO_ENCONTRADO
    assert "RODDOS/no/existe.xlsx" in estado["Inventario / Ventas"]["errores"][0]


def test_cliente_obtiene_un_archivo_por_ruta():
    class Graph(GraphFalso):
        def get(self, url, headers=None, timeout=None, stream=False):
            if "/drive/root:/RODDOS/2.%20OPERACIONES/MOTOS/Inventario%202026.xlsx" in url:
                self.peticiones.append(("GET", url, headers))
                return Respuesta(200, {"id": "X", "name": "Inventario 2026.xlsx", "eTag": '"e9"', "size": 1,
                                       "lastModifiedDateTime": "2026-10-20T14:28:53Z", "file": {}})
            return super().get(url, headers, timeout, stream)
    item = _cliente(Graph()).obtener(MAESTRO)
    assert item["nombre"] == "Inventario 2026.xlsx" and item["etag"] == '"e9"'


def test_rutas_desde_los_secrets(_aislar, monkeypatch):
    carpeta = CarpetaConMaestro()
    monkeypatch.setattr(sp, "crear_cliente", lambda cfg: carpeta)
    at = AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=60)
    at.secrets["acceso"] = {"clave_directores": "x"}
    at.secrets["sharepoint"] = dict(SECRETS_SP, archivos={"inventario": MAESTRO})
    at.run()
    assert not at.exception
    assert ds.leer_inventario()["hoy"]["vendidas_mes"] == 12


@pytest.mark.parametrize("descripcion, esperado", [
    ("AADSTS700016: Application with identifier 'x' was not found in the directory 'y'.", "Id. de objeto"),
    ("AADSTS7000215: Invalid client secret provided.", "VALOR del secreto"),
    ("AADSTS90002: Tenant 'x' not found.", "tenant_id no existe"),
    ("AADSTS99999: Algo nuevo.\nTrace ID: 123", "Microsoft dice: AADSTS99999: Algo nuevo."),
])
def test_error_de_inicio_de_sesion_explicado(descripcion, esperado):
    class Graph(GraphFalso):
        def post(self, url, data=None, timeout=None):
            return Respuesta(400, {"error": "invalid_request", "error_description": descripcion})
    with pytest.raises(sp.ErrorSharePoint) as e:
        _cliente(Graph()).listar()
    assert esperado in str(e.value) and "Trace ID" not in str(e.value)


def test_los_tests_nunca_usan_el_secrets_toml_real(_aislar, monkeypatch):
    """Aunque el proyecto tenga un secrets.toml con [sharepoint], un AppTest sin secretos propios
    no lo ve (ver conftest._sin_secretos_reales)."""
    usados = []
    monkeypatch.setattr(sp, "crear_cliente", lambda cfg: usados.append(cfg) or CarpetaFalsa())
    at = AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=60).run()
    assert not at.exception
    assert usados == []
    assert "sharepoint" not in at.secrets and "mongo" not in at.secrets
