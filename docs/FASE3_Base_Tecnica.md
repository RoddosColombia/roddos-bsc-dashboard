# FASE 3 — Base técnica del dashboard · Dashboard BSC RODDOS

Entregable de la Fase 3, según el prompt maestro ROMA. A diferencia de
Fase 1 y 2, esta sí incluye código — el propio prompt maestro pide
`requirements.txt` y "un validador" como entregables, no solo diseño.
Ya construido y probado; se detiene aquí a esperar aprobación antes de
Fase 4 (diseño y código del dashboard completo).

---

## 1. Arquitectura en 4 pasos

```
Ingesta → Validación → Cálculo → Visualización
```

| Paso | Dónde vive | Qué hace |
|---|---|---|
| **Ingesta** | `pages/0_Actualizar_Datos.py` | 6 cargadores de archivo (uno por fuente). Recibe el Excel subido en memoria. |
| **Validación** | `validators.py` (nuevo) | Revisa estructura (hojas y columnas esperadas) en los 5 archivos que vienen de un sistema externo; revisa fila por fila el Embudo Comercial, que se diligencia a mano. Si hay errores, **no se guarda nada** — se le muestra al usuario en español, con el número de fila exacto. |
| **Cálculo** | `data_sources.py` (lectura de Excel) + `metricas.py` (agregación ayer/semana/mes) + `objetivos.py` (metas vs. resultado) | Solo corre sobre un archivo que ya pasó la validación. |
| **Visualización** | `app.py` + `pages/*.py` | Streamlit renderiza tarjetas, semáforos y gráficas a partir de lo que devuelve `metricas.py`. |

La regla de oro: **un archivo que no pasa el paso 2 nunca llega al paso
3**. Así el dashboard nunca muestra un número calculado sobre datos mal
diligenciados sin que alguien se entere.

---

## 2. Carga manual vs. lectura automática desde OneDrive/SharePoint

Ya resuelto en la Parte 3 del prompt maestro: **empezar manual, migrar
después**. Se documenta la comparación completa para que quede en el
registro del proyecto:

| | Carga manual (plantillas) | Lectura automática OneDrive/SharePoint |
|---|---|---|
| Esfuerzo inicial | Bajo — ya construido | Alto — requiere registrar una app en Azure AD, manejar tokens OAuth, credenciales en `st.secrets` |
| Costo | $0 | $0 en licencias (ya tienen Microsoft 365), pero tiempo real de desarrollo |
| Control de calidad | Alto — el validador obliga a corregir antes de que el dato entre | Bajo — si el archivo real está mal diligenciado, el error entra directo, sin aviso |
| Fricción diaria | Alguien debe recordar subir cada archivo | Ninguna — se actualiza solo |
| Detecta quién no cargó su archivo | Sí, de inmediato (aparece "última carga" desactualizada) | No necesariamente — puede pasar desapercibido |
| Funciona igual en Streamlit Cloud | Sí, sin restricciones | Sí, pero depende de que las credenciales sigan vigentes |
| Cuándo conviene | Mientras las plantillas maduran | Una vez las plantillas llevan 3-4 semanas estables |

**Recomendación (ya confirmada)**: manual con validador estricto ahora;
conectar OneDrive cuando el proceso lleve 3-4 semanas de uso estable.

---

## 3. Estructura de carpetas del proyecto

```
bsc-streamlit/
├── app.py                      # página principal (embudo + cartera)
├── data_sources.py             # lectura de cada Excel real
├── metricas.py                 # cálculo ayer/semana/mes por rubro
├── objetivos.py                # metas del mes (hoy: JSON; ver Fase 1 §3 — pasa a Excel)
├── validators.py               # NUEVO — validación por archivo antes de aceptar una carga
├── utils.py                    # formato de pesos, paleta de colores
├── requirements.txt
├── pages/
│   ├── 0_Actualizar_Datos.py   # ingesta + validación + respaldo de 1 versión
│   ├── 1_Tesoreria.py
│   └── 2_RRHH.py
├── data/
│   └── objetivos.json          # se retira cuando Metas pase a ser hoja de Excel
├── data_raw/                   # última versión aceptada de cada archivo real
│   ├── Proyeccion_Recaudo.xlsx
│   ├── Inventario_2026.xlsx
│   ├── Cruce_SISMO_Wava.xlsx
│   ├── Flujo_Pagos_Deudas.xlsx
│   ├── Control_RRHH_Nomina_RODDOS_2026.xlsx
│   ├── Embudo_Comercial_RODDOS.xlsx
│   └── versiones/              # NUEVO — 1 respaldo por archivo (Fase 2 §4)
├── plantillas/
│   └── Plantilla_Embudo_Comercial.xlsx
└── docs/
    ├── handshake_bsc_dashboard.md
    ├── FASE1_Auditoria_Diseno_Dato.md
    ├── FASE2_Permisos_Gobierno_Dato.md
    └── FASE3_Base_Tecnica.md   # este documento
```

Sin cambios grandes de estructura — se agregaron `validators.py` y
`data_raw/versiones/`, el resto ya existía y se mantiene.

---

## 4. `requirements.txt`

Sin cambios — el validador solo usa `openpyxl` (ya incluido) y la
librería estándar de Python (`datetime`). No hace falta ninguna
dependencia nueva para esta fase:

```
streamlit>=1.60
pandas>=2.0
plotly>=5.20
openpyxl>=3.1
```

`[FALTA en Fase 4]`: si se construye el Nivel 2 de autenticación
(contraseña compartida vía `st.secrets`), tampoco necesita librería
nueva — es `st.text_input` + `st.secrets`, ya incluido en Streamlit.

---

## 5. El validador

Construido en `validators.py`, uno por archivo:

- `validar_recaudo`, `validar_inventario`, `validar_conciliacion`,
  `validar_tesoreria`, `validar_rrhh` — revisan que existan las hojas y
  columnas esperadas. Como estos 5 archivos vienen de un sistema
  (SISMO, contabilidad), el riesgo real no es el error de tecleo sino
  que cambie el formato de exportación — por eso la validación es
  estructural.
- `validar_embudo` — el único que diligencia una persona a mano, así
  que valida fila por fila: canal debe estar en la lista, no puede
  faltar el nombre, la fecha del lead no puede ser futura, la decisión
  debe ser "Aprobado"/"Rechazado"/vacía, el estado de agenda debe ser
  válido, y si hay fecha de agenda debe tener estado (si no, nunca se
  va a poder contar como cumplida o no).

**Probado** contra los 6 archivos reales actuales (los 6 pasan limpio,
cero falsos positivos) y contra un archivo de prueba con 5 errores
deliberados (canal inventado, nombre faltante, fecha futura, decisión
inválida, agenda sin estado) — los 5 se detectaron con el número de
fila correcto.

**Bug encontrado y corregido en el proceso**: el validador de
decisiones usaba `"Decisión"` (con tilde) para buscar la columna, pero
la plantilla real la tiene como `"Decision"` (sin tilde) — es el mismo
tipo de error de tildes que ya había aparecido antes en `metricas.py`.
Sin la prueba con datos falsos, este validador habría dejado pasar
decisiones inválidas en silencio.

**Integrado** en `pages/0_Actualizar_Datos.py`: si el archivo subido
tiene errores, no se guarda nada y se listan los problemas (máximo 20
en pantalla, con contador si hay más). Si pasa, se guarda primero una
copia de la versión anterior en `data_raw/versiones/` (sobreescribiendo
la anterior, no se acumula) y luego se reemplaza el archivo.

---

## Fase 3 — cerrada

Todo lo pedido está construido y probado: arquitectura documentada,
comparación con recomendación ya confirmada, estructura de carpetas,
`requirements.txt` sin cambios, y el validador funcionando de punta a
punta. Queda a la espera de aprobación para pasar a Fase 4 (diseño y
código completo del dashboard: vista principal, proyección de cierre,
vista por etapa, vista de reunión de 15 minutos).
