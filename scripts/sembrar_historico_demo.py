"""Llena el histórico LOCAL (data/historico.sqlite) con 6 meses de datos inventados,
para probar la página 📈 Histórico sin datos reales y sin tocar MongoDB.

Uso (desde la raíz del proyecto):
    python scripts/sembrar_historico_demo.py          # agrega los meses de prueba
    python scripts/sembrar_historico_demo.py --borrar # borra TODO el histórico local

Ojo: escribe en el mismo archivo local que usa la app. Bórralo antes de trabajar con datos reales.
"""
import datetime
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import historico  # noqa: E402

if "--borrar" in sys.argv:
    if os.path.exists(historico.RUTA_SQLITE):
        os.remove(historico.RUTA_SQLITE)
    print("Histórico local borrado.")
    sys.exit(0)

random.seed(7)
alm = historico.AlmacenLocal()
hoy = datetime.date.today().replace(day=1)
for atras in range(6, 0, -1):
    mes = (hoy - datetime.timedelta(days=30 * atras)).replace(day=1)
    fin = (mes.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
    datos = {
        "pagos_dinero": random.uniform(48e6, 70e6),
        "ventas": random.randint(18, 35),
        "activaciones": random.randint(15, 32),
        "ci_dinero": random.uniform(25e6, 45e6),
        "vencidas_dinero": random.uniform(5e6, 12e6),
        "mora_total": random.uniform(3e6, 9e6),
        "inventario_disponible": random.randint(8, 30),
        "leads": random.randint(120, 260),
        "pct_aprobacion": random.uniform(0.45, 0.7),
        "_metas": {"pagos_dinero": 60e6, "ventas": 28, "ci_dinero": 38e6, "pct_aprobacion": 0.6},
    }
    alm.guardar(dict(periodo=mes.strftime("%Y-%m"), corte=str(fin),
                     guardado_en=datetime.datetime.now().isoformat(timespec="seconds"), datos=datos))
    print(f"  {mes:%Y-%m} guardado")
print(f"Listo: {historico.RUTA_SQLITE}")
