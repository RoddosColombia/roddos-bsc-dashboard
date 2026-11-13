"""Calcula el funnel y guarda los totales. Lo corre GitHub Actions cada día (.github/workflows/funnel.yml).

Variables de entorno (secretos del repositorio en GitHub):
  RODDOS_WEB_FUNNEL_URI   lectura de RODDOS-web (base roddos)
  CRM_FUNNEL_URI          lectura de CRM-RODDOS (base crm_roddos)
  BSC_FUNNEL_URI          escritura SOLO en bsc_dashboard (donde la página lee los totales)
  SHAREPOINT_TENANT_ID / SHAREPOINT_CLIENT_ID / SHAREPOINT_CLIENT_SECRET   (lectura del Inventario)
Opcionales: SHAREPOINT_SITIO, INVENTARIO_RUTA, RODDOS_WEB_DB, CRM_DB, BSC_DB.

Uso local (sin guardar nada, imprime los totales):
  python -m funnel.ejecutar --env-file ruta/.env --xlsx "ruta/Inventario 2026.xlsx" --no-guardar
"""
import argparse
import datetime as dt
import os
import sys

from pymongo import MongoClient

from funnel import almacen, calculo, fuentes, inventario

INICIO = dt.datetime(2026, 8, 1, 5, 0)  # 1-ago-2026 00:00 hora Colombia, en UTC
SITIO = "roddossas.sharepoint.com:/sites/RODDOSSAS"
# El Inventario vigente vive en la carpeta del dashboard (la copia de 2. OPERACIONES/MOTOS ya no existe).
RUTA_INVENTARIO = "RODDOS/8. DASHBOARD BSC RODDOS/1 Fuentes al día/Inventario 2026.xlsx"


def _cargar_env(ruta):
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            clave, sep, valor = linea.strip().partition("=")
            if sep and clave and not clave.startswith("#"):
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def _requerida(nombre):
    valor = os.environ.get(nombre)
    if not valor:
        sys.exit(f"Falta la variable {nombre} (secreto del repositorio en GitHub).")
    return valor


def _db(uri_var, db_var, por_defecto):
    return MongoClient(_requerida(uri_var), serverSelectionTimeoutMS=20000)[os.environ.get(db_var, por_defecto)]


def calcular_todo(xlsx=None):
    if xlsx:
        with open(xlsx, "rb") as f:
            contenido = f.read()
    else:
        contenido = fuentes.descargar_sharepoint(
            _requerida("SHAREPOINT_TENANT_ID"), _requerida("SHAREPOINT_CLIENT_ID"),
            _requerida("SHAREPOINT_CLIENT_SECRET"), os.environ.get("SHAREPOINT_SITIO", SITIO),
            os.environ.get("INVENTARIO_RUTA", RUTA_INVENTARIO))
    ventas = inventario.leer_ventas(contenido)
    sols = fuentes.solicitudes(_db("RODDOS_WEB_FUNNEL_URI", "RODDOS_WEB_DB", "roddos"))
    crm = _db("CRM_FUNNEL_URI", "CRM_DB", "crm_roddos")
    wa = fuentes.whatsapp_por_celular(crm, fuentes.celulares_de_interes(ventas, sols))
    lds = fuentes.leads(crm, INICIO)
    print("Fuentes leídas:", fuentes.resumen_fuentes(ventas, sols, wa, lds))
    return calculo.calcular(ventas, sols, wa, lds, INICIO)


def imprimir(resumen):
    import collections

    tot = collections.defaultdict(collections.Counter)
    for f in resumen["cohortes"]:
        if f["modelo"] == "primer":
            tot[f["canal"]].update({k: f[k] for k in ("solicitudes", "aprobados", "compras")})
    print(f"\nFunnel desde {resumen['desde']:%Y-%m-%d} (primer toque):")
    for canal, c in sorted(tot.items(), key=lambda x: -x[1]["solicitudes"]):
        print(f"  {canal:32} solicitudes {c['solicitudes']:4}  aprobados {c['aprobados']:4}  compras {c['compras']:4}"
              f"  ({100 * c['compras'] / max(c['solicitudes'], 1):.0f}% solicitud→compra)")
    lds = collections.defaultdict(collections.Counter)
    for f in resumen["leads"]:
        lds[f["fuente"]].update({k: f[k] for k in ("leads", "con_solicitud")})
    print("Leads:", {k: dict(v) for k, v in lds.items()})
    print("Calidad:", resumen["calidad"])
    print("Avisos:", resumen["avisos"])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--env-file")
    p.add_argument("--xlsx", help="Inventario local en vez de descargarlo de SharePoint")
    p.add_argument("--no-guardar", action="store_true", help="Solo imprimir los totales")
    a = p.parse_args(argv)
    if a.env_file:
        _cargar_env(a.env_file)
    resumen = calcular_todo(a.xlsx)
    imprimir(resumen)
    if not a.no_guardar:
        almacen.guardar(_db("BSC_FUNNEL_URI", "BSC_DB", "bsc_dashboard"), resumen)
        print("Totales guardados en bsc_dashboard.funnel_resumen.")


if __name__ == "__main__":
    main()
