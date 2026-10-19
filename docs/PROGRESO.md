# Progreso del desarrollo — rama `mejoras/arranque-local`

Documento vivo: se actualiza con cada entrega. Si retomas el trabajo, empieza aquí.

Última actualización: 19 de octubre de 2026.

## Estado del plan

| # | Bloque | Estado |
|---|--------|--------|
| 0 | Configuración base (`.gitignore`, `.gitattributes`, `secrets.toml.example`) | ✅ Hecho |
| — | La app arranca sin datos y dice qué archivo subir | ✅ Hecho |
| — | Lectura dinámica de semanas, días y meses (ya no se congela en septiembre) | ✅ Hecho |
| — | Histórico mensual (foto por mes, página 📈 Histórico) | ✅ Hecho |
| 1 | Errores reales: validadores, proyección, Metas, secciones aisladas | ✅ Hecho |
| 2 | Tests confiables: Excel de prueba, CI, versiones fijas | ✅ Hecho |
| — | Verificar los validadores contra los Excel REALES (`scripts/verificar_archivos.py`) | ✅ Hecho: los 8 archivos reales pasan (19 oct) |
| — | Revisar el tablero con los datos reales en local (números con sentido para el negocio) | ⏳ Siguiente |
| 3a | Aviso de datos desactualizados (página principal, Vista de reunión, Tesorería) | ✅ Hecho |
| 3b | Respaldo GridFS en Mongo, reconstruir histórico hacia atrás | ⏳ Pendiente |
| — | Conectar SharePoint (lectura automática de los Excel) | ⏳ Esperando autorización de Andrés |
| 4 | Calidad de código: refactor de `app.py`, formatos únicos, leer por etiquetas | ⏳ Pendiente |
| 5 | Publicar la rama como app de pruebas en Streamlit Cloud, PR y merge | ⏳ Pendiente |
| — | Actualizar el instructivo (menú, página Histórico, 7 vs 8 archivos) | ⏳ Después del merge |
| — | Agenda: días clicables en la vista Mes | ✅ Hecho |
| — | Modo oscuro (temas claro/oscuro nativos + colores adaptables, ~94 colores fijos) | 🅿️ Mejora para después |
| — | Agenda: botón "Hoy" en las vistas Semana y Mes | ✅ Hecho |
| — | Agenda: estado al pasar el mouse en la vista Semana; "+N más" con clic si un día tiene muchas visitas | 🅿️ Mejora para después |
| — | Login por roles y decisiones de producto de `docs/` | 🅿️ Depende de los socios |

## Qué garantiza hoy el tablero

1. **Un archivo malo nunca reemplaza al bueno.** Al subir un Excel, la página "Actualizar datos":
   - lo valida con los VALORES (`data_only=True`), igual que los ve el tablero;
   - si pasa, hace una **prueba de lectura** con el mismo lector del tablero sobre una copia temporal;
   - solo si ambas pasan, reemplaza el archivo anterior.
2. **Todo lo que el código lee sin protección está verificado en `validators.py`.**
   `tests/test_validadores.py` lo comprueba caso por caso, y su sección 3 demuestra que esas
   reglas protegen contra caídas reales.
3. **Un archivo opcional dañado solo apaga su sección** (Conciliación, Embudo, Metas, Cobranza):
   aparece un aviso amarillo y el resto sigue. Si falla Recaudo o Inventario, sale un mensaje claro
   en vez del error de Python.
4. **Ningún test toca datos reales**: `tests/conftest.py` redirige todo a carpetas temporales.

## Cómo trabajar

```bash
pip install -r requirements-dev.txt          # una vez, dentro del entorno virtual
python -m pytest -q                          # todos los tests (~15 s)
python scripts/verificar_archivos.py         # revisa los Excel reales de data_raw/ con las reglas de la app
python tests/fixtures_excel.py otra_carpeta  # genera los 8 Excel de mentira (no pisa archivos existentes)
python scripts/sembrar_historico_demo.py     # llena el histórico local con 6 meses de mentira
streamlit run app.py
```

La prueba de conexión contra el Mongo REAL (`test_conexion_real_atlas`) no corre por defecto,
porque escribe un documento de prueba en la base. Para correrla a propósito (con `[mongo]` en
`secrets.toml`): en PowerShell `$env:RODDOS_PROBAR_MONGO="1"; python -m pytest tests/test_respaldo.py`.

GitHub Actions corre los tests en cada push y en cada Pull Request (`.github/workflows/tests.yml`).

## Decisiones tomadas (y por qué)

- **Histórico en SQLite local por defecto**; Mongo solo con `[historico] destino = "mongo"`.
  Así se prueba sin tocar la base ni el cobro. En el servidor publicado DEBE ser `"mongo"`:
  Streamlit Cloud borra el disco en cada reinicio.
- **Nunca poner `[mongo]` en el `secrets.toml` local**: activa el respaldo de Excel y lo que subas
  reemplazaría los archivos de producción.
- **Versiones fijas** en `requirements.txt`, elegidas con al menos 14 días de publicadas
  (Streamlit 1.64.0, pymongo 4.18.2). Para actualizar: subir la versión, correr los tests y, si pasan, commit.
- **Requiere Python 3.11 o superior** (pandas 3 y `tomllib` en los tests). El servidor de Streamlit
  Cloud usa **Python 3.14**; el desarrollo local, 3.12. GitHub Actions prueba en ambas versiones.
- **Accesos confirmados:** la app publicada está en Streamlit Cloud, espacio `roddoscolombia`
  (repo `RoddosColombia/roddos-bsc-dashboard`, rama `main`). Sus Secrets ya tienen `[acceso]` y
  `[mongo]`. Pendiente: confirmar el plan de MongoDB Atlas y la autorización de Microsoft 365
  para conectar SharePoint.
- **Los nombres internos de archivo con "2026" se mantienen**: cambiarlos rompería la
  recuperación desde el respaldo en Mongo. No afectan a los usuarios: cada casilla guarda el
  archivo con su nombre interno, se llame como se llame el que se sube.
- **Modo oscuro sin interruptor propio**: Streamlit no permite cambiar su tema desde el código.
  El camino es configurar `[theme.light]` y `[theme.dark]` en `config.toml` (cada usuario elige en
  ⋮ → Settings) y quitar los colores fijos de las tarjetas para que se adapten.
- **Calendario del mes: celda HTML + botón invisible encima.** El HTML permite los puntos de
  color por estado pero no puede recibir clics; el botón de Streamlit (transparente, del tamaño
  de la celda) sí. El CSS usa la clase `st-key-<clave>` que Streamlit pone a cada elemento con `key`.
- **La casilla "Pagada" de Cobranza acepta casilla de verificación, "Sí", "No", "X" o vacío**,
  porque el instructivo pide marcar "Pagada = Sí".

## Mapa de archivos

| Archivo | Para qué |
|---------|----------|
| `data_sources.py` | Lee cada Excel. Cada lector acepta `ruta=` para la prueba de lectura. |
| `validators.py` | Reglas de cada archivo. Si el lector lo usa, aquí se valida. |
| `formatos.py` | Fechas escritas como texto y casillas Sí/No; lo comparten lector y validador. |
| `metricas.py` | Arma los rubros. Conciliación y Embudo aislados (devuelve `avisos`). |
| `objetivos.py` | Metas prorrateadas y proyección de cierre (por fuente de cada rubro). |
| `historico.py` | Fotos mensuales; almacén local (SQLite) o Mongo. |
| `utils.py` | Estilos y ayudas: `pedir_archivos`, `leer_seguro`, `cargar_o_detener`, `mostrar_avisos`. |
| `tests/fixtures_excel.py` | Los 8 Excel de mentira. Si cambia un formato real, se actualiza aquí. |
| `scripts/verificar_archivos.py` | Revisa Excel reales sin subirlos. |

## Historial de entregas

1. Configuración base del repositorio y entorno local.
2. Arranque sin datos: aviso de archivos faltantes en vez de `FileNotFoundError`.
3. Lectura dinámica de tablas: semanas, días (meses de 31) y meses sin tope fijo.
4. Histórico mensual con almacén intercambiable (SQLite / Mongo) y página 📈 Histórico.
5. Blindaje de datos y tests:
   - Validadores alineados con los lectores (Recaudo, Conciliación, Tesorería, RRHH, Embudo, Metas, Cobranza).
   - Validación con valores (`data_only=True`) y prueba de lectura antes de reemplazar.
   - Corregido: la página de carga volvía a procesar el archivo en cada recarga.
   - Corregido: proyección de ventas y cuotas iniciales con el día de corte equivocado.
   - Corregido: Metas con "Mes" en texto tumbaba la página; Cobranza no contaba "Sí" como pagada;
     Recaudo dependía de la posición de la columna "Cód. crédito".
   - Secciones opcionales aisladas; mensajes claros cuando falla un archivo principal.
   - 119 tests con Excel anonimizados, CI en GitHub Actions, versiones fijas.
6. Ajuste: la prueba contra Mongo real ya no falla si `secrets.toml` no tiene `[mongo]` y solo
   corre si se pide con `RODDOS_PROBAR_MONGO=1` (nunca escribe en producción por accidente).
7. Agenda, vista Mes: clic en cualquier día para ver sus clientes; cada día muestra un punto de
   color por cliente según su estado; se conserva la lista desplegable "Ver clientes de un día"
   (consolidado), sincronizada con el clic. 4 tests nuevos.
8. Agenda: botón "Hoy" junto a "◀ Anterior" en las vistas Semana y Mes. Vuelve a la semana o al
   mes actual (en Mes, deja marcado el día de hoy); desactivado si ya estás ahí. 2 tests nuevos.
9. Verificado en Python 3.14.4 (la versión del servidor): 125 tests pasan. GitHub Actions ahora
   prueba en 3.12 y 3.14.
10. `scripts/verificar_archivos.py`: busca también en subcarpetas (zip descomprimido), acepta el
    nombre de SharePoint "Flujo de pagos deudas.xlsx", avisa si la carpeta no existe, lista los
    Excel que sí encontró y ya no dice "Todo en orden" cuando no revisó nada.
11. Primera verificación con los Excel reales (19 oct): Recaudo, Inventario, Conciliación, RRHH y
    Cobranza pasan. Embudo y Metas eran rechazados por reglas que YA existían en el código original
    (el tablero publicado tampoco los aceptaba). Ajustes:
    - Embudo: 'Estado agenda' vacío con fecha de agenda ya no es error (se muestra como Pendiente).
    - Embudo: fechas escritas a mano en formato día/mes/año se aceptan y se leen con el día primero.
      Corregido de paso: el lector original leía '05/09/2026' como 9 de mayo.
    - Embudo: filas que solo traen la fecha se ignoran (no son leads).
    - Metas: los encabezados se buscan en las primeras filas (no solo en la fila 4).
    - `tests/test_archivos_reales.py`: 15 tests que reproducen estos casos.
12. Segunda verificación con los Excel reales (19 oct): los 8 archivos pasan validación y prueba
    de lectura. Desbloqueado el camino a publicar.
13. Aviso de datos desactualizados (`frescura.py`). Compara la fecha de corte de cada archivo con
    hoy, en días hábiles: hasta 1 día = al día; 2-4 = aviso amarillo; 5 o más = aviso rojo. Se ve
    en la página principal y en la Vista de reunión (Recaudo e Inventario) y en Tesorería.
    Motivo: con los Excel reales se vio que los datos eran de finales de septiembre y el tablero
    lo mostraba como si fuera lo actual. 14 tests nuevos (154 en total).
