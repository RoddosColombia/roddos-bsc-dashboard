# FASE 1 — Auditoría y diseño del dato · Dashboard BSC RODDOS

Entregable único de la Fase 1, según el prompt maestro ROMA del 2026-09-23.
No hay código nuevo en esta fase. Esto se detiene aquí a esperar aprobación
antes de pasar a Fase 2 (permisos y gobierno del dato).

Regla seguida en todo el documento: **nada inventado**. Donde falta un dato
real (una cifra, un dueño, una regla de proceso), se marca `[FALTA: ...]`
en vez de suponerlo.

---

## 1. Diccionario de indicadores

23 indicadores (21 ya definidos + 2 nuevos de la Parte 1: % de aprobación,
días de inventario), organizados por las 7 etapas del embudo + 2 módulos de
soporte. `H` = en qué horizonte aplica (A=ayer, S=semana, M=mes).

### Etapa 1 — Demanda

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| 1 | Leads recibidos | Contactos nuevos que entran por cualquier canal | Conteo de filas con `fecha_lead` en el rango | # | Plantilla Leads y Agendas (nueva, hoy vacía) | `[FALTA: quién es dueño de Demanda]` | Cada lead, el mismo día que entra | A·S·M |

### Etapa 2 — Crédito

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| 2 | Formularios diligenciados | Leads que completaron el formulario de crédito | Conteo de filas con `fecha_formulario` en el rango | # | Plantilla Leads y Agendas | `[FALTA]` | Al momento de diligenciar | A·S·M |
| 3 | Aprobados y rechazados | Decisiones de crédito tomadas | Conteo de filas con `fecha_decision` en el rango | # | Plantilla Leads y Agendas | `[FALTA]` | Al momento de decidir | A·S·M |
| 3b | % de aprobación *(nuevo, Parte 1)* | De las decisiones tomadas en el mes, cuántas fueron "Aprobado" | `aprobados_mes / (aprobados_mes + rechazados_mes)` | % | Calculado de indicador 3 | `[FALTA]` | Se recalcula solo | M |

### Etapa 3 — Agenda

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| 4 | # agendas de visita de cliente | Visitas programadas con fecha en el rango | Conteo de filas con `fecha_agenda_visita` en el rango | # | Plantilla Leads y Agendas | `[FALTA]` | Al programar la visita | A·S·M |
| 5 | Agendas de visita para hoy | Visitas programadas exactamente para hoy | Conteo con `fecha_agenda_visita` = hoy | # | Plantilla Leads y Agendas | `[FALTA]` | Snapshot del día | — (solo "hoy", no encaja en A/S/M puro) |
| 6 | Agendas cumplidas ayer | De las programadas ayer, cuántas con `estado_agenda`="Cumplida" | `cumplidas_ayer / programadas_ayer` | # (con razón "X de Y") | Plantilla Leads y Agendas | `[FALTA]` | Se marca al final del día | A |
| 7 | Incumplimientos de agenda (acumulado) | Agendas marcadas "No cumplida" en el mes | Conteo con `estado_agenda`="No cumplida" y `fecha_agenda_visita` en el mes | # | Plantilla Leads y Agendas | `[FALTA]` | Se marca al final del día | M (acumulado) |

### Etapa 4 — Venta (cuota inicial)

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| 8 | Ventas (cuota inicial completa + parcial) | Negocios cerrados con algún pago de cuota inicial | Snapshot `vendidas_mes` del Dashboard de Inventario | # | `Inventario_2026.xlsx` → Dashboard | `[FALTA]` | Diario (quien actualiza el archivo) | M (snapshot, sin histórico ayer/semana hoy) |
| 10 | Cuotas iniciales completas | Negocios con cuota inicial 100% pagada | Snapshot `ci_completa_hoy` (hoja Plan separe) | # | `Inventario_2026.xlsx` | `[FALTA]` | Diario | M |
| 11 | Cuotas iniciales parciales | Negocios con cuota inicial pagada solo en parte | Snapshot `ci_parcial_hoy` | # | `Inventario_2026.xlsx` | `[FALTA]` | Diario | M |
| 12 | $ total de cuotas iniciales | Suma en pesos de lo recaudado por cuota inicial en el mes | Snapshot `ci_mes` | $ COP | `Inventario_2026.xlsx` | `[FALTA]` | Diario | M |

### Etapa 5 — Facturación y entrega

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| 9 | Facturación a cliente | Motos facturadas en el año a la fecha, + cuántas cuotas parciales faltan por convertir en factura | `motos_facturadas_anio`, `pendientes_factura` | # | `Inventario_2026.xlsx` → Dashboard | `[FALTA]` | Diario | M |
| 13 | Activaciones (entrega de motos) | Motos entregadas al cliente en el mes | Snapshot `activadas_mes` | # | `Inventario_2026.xlsx` | `[FALTA]` | Diario | M |

### Etapa 6 — Cartera y mora

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| 14 | Cuotas totales del mes a hoy | Cuotas programadas con vencimiento ≤ hoy, de créditos activos | `COUNTIFS(fecha_prog<=hoy, clasificacion_meta="En meta")` | # | `Proyeccion_Recaudo.xlsx` → Detalle Cuotas | `[FALTA]` | Se recalcula solo | A·S·M |
| 15 | Pagos de cuotas (#) | Cuotas pagadas con fecha de pago en el rango | `COUNTIFS(fecha_pago en rango)` | # | Detalle Cuotas | `[FALTA]` | Se recalcula solo (SISMO) | A·S·M |
| 16 | Pagos de cuotas ($) | Suma pagada con fecha de pago en el rango | `SUMIFS(pagado, fecha_pago en rango)` | $ COP | Detalle Cuotas | `[FALTA]` | Se recalcula solo | A·S·M |
| 17 | Cuotas vencidas (#) | Cuotas con vencimiento ≤ hoy, no pagadas por completo, de créditos activos | `COUNTIFS(fecha_prog<=hoy, estado<>"OK", clasificacion_meta="En meta")` | # | Detalle Cuotas | `[FALTA]` | Se recalcula solo | A·S·M (saldo acumulado, no diario) |
| 18 | Cuotas vencidas ($) | Saldo pendiente de esas cuotas | `SUMIFS(saldo_a_cobrar, ...)` | $ COP | Detalle Cuotas | `[FALTA]` | Se recalcula solo | A·S·M |
| 19 | $ de mora total | Saldo vencido de créditos activos (ver Fase 1 §2 — hoy roto) | Ver hoja "Cartera Vencida" propuesta | $ COP | Detalle Cuotas (nuevo cálculo) | `[FALTA]` | Se recalcula solo | M |

### Etapa 7 — Inventario

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| 20 | Motos en bodega | Motos con `Ubicación`="Site" | `COUNTIF(ubicacion="Site")` | # | `Inventario_2026.xlsx` → Inventario motos | `[FALTA]` | Se recalcula solo | M |
| 21 | Motos disponibles | De las de bodega, cuántas sin compromiso (venta/plan separe) | Snapshot `disp_total` | # | `Inventario_2026.xlsx` → Dashboard | `[FALTA]` | Diario | M |
| 21b | Días de inventario *(nuevo, Parte 1)* | A cuántos días de venta equivale lo que hay hoy en bodega | `motos_disponibles / (ventas_mes / dia_del_mes)` — ritmo de venta actual | días | Calculado (Inventario + Ventas) | `[FALTA]` | Se recalcula solo | M |

### Módulo de soporte (a) — Tesorería

| # | Indicador | Definición | Fórmula | Unidad | Fuente | Dueño | Frecuencia captura | H |
|---|---|---|---|---|---|---|---|---|
| T1 | Caja disponible total | Suma de saldos de todas las cuentas | Celda `E14` hoja Tablero mes | $ COP | `Flujo_Pagos_Deudas.xlsx` | `[FALTA]` | Según último extracto bancario cargado | M (snapshot) |
| T2 | Ingresos / egresos / resultado neto | Movimientos reales de banco, limpios de duplicados/traslados | `SUMIFS` sobre Base real ingresos/egresos | $ COP | `Flujo_Pagos_Deudas.xlsx` | `[FALTA]` | Según extractos cargados | A·S·M |
| T3 | Proyección de caja | Ver Fase 1 §2 — dos modelos sin integrar hoy | — | $ COP | Doble fuente, sin resolver | `[FALTA]` | — | M (proyectado) |

### Módulo de soporte (b) — Personas (privado, solo directores)

Nómina, vacaciones, brecha legal de retención — ya construido y validado
esta sesión (`pages/2_RRHH.py`). No sigue el esquema A/S/M porque la
nómina es mensual. Queda **fuera del dashboard operativo** por decisión ya
tomada (ver `handshake_bsc_dashboard.md` → Control de acceso).

---

## 2. Diagnóstico de cada archivo actual

| Archivo | Veredicto | Razón | Riesgo de dejarlo igual |
|---|---|---|---|
| **`Proyeccion_Recaudo.xlsx`** (Recaudo) | **Sirve con cambios** | `Detalle Cuotas` y `Creditos SISMO` son sólidas, en vivo, bien normalizadas — se quedan tal cual. Pero: (1) la hoja `Mora SISMO` **parece viva pero no lo es** — su columna DPD está pegada como número fijo (96, 97, 61...) en vez de fórmula, y la fecha "vencida más antigua" se calcula restando ese número fijo a `DATE(2026,9,14)` escrito a mano en la fórmula. (2) No existe ninguna hoja con el total crudo de "cuotas a cobrar del mes" que pediste. (3) Las 5 hojas `Cobro Sem 36` a `Sem 40` son casi idénticas entre sí, con una columna "Confirmado" manual — propósito real sin confirmar contigo todavía. | **Alto en Mora SISMO**: cualquier decisión basada en esa hoja usa datos congelados el 14-sep sin que nadie lo note — se ve como si estuviera actualizada. |
| **`Inventario_2026.xlsx`** (Inventario/Ventas) | **Sirve como está** | Se leyó en vivo toda la sesión (Dashboard, Inventario motos, Plan separe) sin encontrar inconsistencias estructurales. Tiene además `Daily Ventas`, `Facturación`, `Auditoría total`, `Presupuesto Compra Sep`, `Planeación Ventas` — hojas que no se han auditado todavía a fondo. | Bajo. Único faltante: no tiene el dato para calcular "días de inventario" (nuevo indicador) directamente — hay que construir la fórmula, no cambiar el archivo. |
| **`Flujo_Pagos_Deudas.xlsx`** (Tesorería) | **Sirve con cambios** | Archivo real, completo y bien construido (10 hojas, miles de filas de transacciones limpias con banderas de duplicado/reversado/traslado). El problema no es la calidad del dato — es que **conviven dos modelos de proyección de caja sin integrar**: la hoja propia `Proyección 18M` (supuesto: 10% crecimiento mensual de unidades) y el modelo del informe financiero ya entregado aparte (escenarios de piso de supervivencia, distinto supuesto de gasto). | Medio-alto: si alguien mira un número de "caja proyectada" sin saber cuál modelo es, puede tomar una decisión sobre una cifra que no es la oficial. |
| **`Control_RRHH_Nomina_RODDOS_2026.xlsx`** (RRHH) | **Sirve como está** | Fórmulas en cascada completas y correctas (regla del 40%, retefuente, aportes patronales, provisiones, vacaciones) — validado formula por fórmula esta sesión, incluida la incorporación de un empleado nuevo. | Bajo. |
| **Marketing / leads** | **Se reemplaza — no existe** | No hay ningún archivo hoy. Ya se diseñó una plantilla (`Plantilla_Embudo_Comercial.xlsx`) que cubre leads → formulario → decisión → agenda en una sola fila por lead, pero **nadie del equipo la ha usado todavía** — no está validada contra el proceso real, y el prompt maestro sugiere separar "Leads y agendas" de "Crédito" como plantillas distintas, cosa que la actual no hace (las mezcla en una hoja). Necesita revisión de diseño antes de darla por buena. | Alto si se asume que ya está resuelta: hoy los indicadores 1-7 muestran "sin dato" en el tablero porque nadie ha empezado a diligenciar. |

---

## 3. Modelo de datos objetivo

Principio: separar **dato crudo** (se pega o se digita, nunca se calcula)
de **vistas calculadas** (100% fórmula) de **decisiones de dirección**
(metas — las escribe una persona, no se calculan).

### Llaves de cruce entre archivos

| Llave | ¿Existe hoy? | Dónde vive | Riesgo si no se estandariza |
|---|---|---|---|
| `id_credito` | Sí, como "Cód. crédito" (ej. `LB-2026-0204`) | Recaudo (Detalle Cuotas, Creditos SISMO) | Ninguno — ya es consistente. |
| `id_cliente` | **No existe como ID estable** | Recaudo usa "Cliente" (texto libre, nombre) | **Riesgo real**: nombres se pueden escribir distinto entre archivos (con/sin tilde, apellidos en otro orden), duplicados no se detectan. Cruzar Recaudo↔Marketing↔Inventario por nombre es frágil. |
| `id_moto` / VIN | Parcial — "Placa" existe en Creditos SISMO e Inventario motos, "Chasis" (=VIN) existe en Inventario motos | Recaudo (Placa), Inventario (Placa + Chasis) | Placa es más natural que VIN para el equipo — se puede usar como llave si se estandariza el formato (mayúsculas, sin espacios). |
| `id_lead` | No existe — se crearía con la plantilla nueva | Plantilla Leads y Agendas (nueva) | Ninguno si se diseña bien desde el inicio. |
| `id_factura` | No confirmado — Inventario tiene hoja "Facturación" sin auditar a fondo | `[FALTA: revisar hoja Facturación de Inventario_2026.xlsx]` | — |
| `id_cuota` | Implícito (Cód. crédito + N° cuota) | Recaudo (Detalle Cuotas) | Ninguno — ya es reconstruible. |

**Recomendación**: no es necesario crear un `id_cliente` nuevo ahora mismo
(sería un cambio grande y sensible en un archivo que el equipo usa a
diario) — pero si el objetivo es cruzar Marketing→Ventas→Cartera de un
lead concreto, sí hace falta al menos un campo puente. Candidato: usar
"Cédula" cuando esté disponible (ya se usa en Empleados/contratos de
RRHH); si no está disponible en el momento del lead, usar el
`id_credito` una vez el lead se convierte en crédito — se apunta como
brecha, no se resuelve en esta fase.

### Archivos, hoja por hoja

**`Proyeccion_Recaudo.xlsx`** (sin cambio de nombre, cambios de contenido):
| Hoja | Tipo | Cambio propuesto |
|---|---|---|
| Dashboard | Calculada | Mantener |
| Detalle Cuotas | Cruda | Mantener sin cambios |
| Creditos SISMO | Cruda | Mantener sin cambios |
| Resumen Semanal | Mixta (meta=dirección, cumplimiento=calculado) | Mantener, documentar cómo se define la "meta pactada" |
| **Mora SISMO** | Calculada | **Reconstruir**: DPD en vivo (`hoy - fecha_prog`), no fijo |
| **Cuotas a Cobrar del Mes** | Calculada | **Nueva** (ver especificación ya acordada) |
| **Cartera Vencida** | Calculada | **Nueva**, reemplaza a Mora SISMO cuota por cuota |
| Cobro Sem 36-40 | `[FALTA: definir tras entender su uso real]` | — |
| Auditoria | Cruda/auditoría | `[FALTA: resolver duplicidad con Cruce_SISMO_Wava.xlsx]` |

**`Inventario_2026.xlsx`**: mantener estructura, agregar cálculo de "días
de inventario" (no requiere nueva hoja, es una fórmula sobre datos ya
existentes).

**`Flujo_Pagos_Deudas.xlsx`**: mantener estructura. Pendiente decisión de
dirección: ¿cuál modelo de proyección de caja es el oficial?

**`Control_RRHH_Nomina_RODDOS_2026.xlsx`**: sin cambios.

**Plantilla de Marketing** — ver §4.

**Hoja "Metas"** (nueva, no existe en ningún archivo hoy): un solo lugar
donde la dirección escribe, cada mes, la meta de ventas, la meta de
recaudo, la meta de % de aprobación, la meta de cumplimiento de agendas y
el tope de mora aceptable. Hoy esto vive parcialmente en
`data/objetivos.json` (un archivo técnico que edita el dashboard, no un
Excel que la dirección controle directamente) — **decisión pendiente**:
¿la meta se sigue editando desde el dashboard (como hoy, vía formulario
web), o pasa a ser una hoja de Excel que alguien diligencia? El prompt
maestro pide explícitamente una "hoja de Metas" en Excel — lo marco como
punto a decidir en Fase 2, no lo cambio unilateralmente.

---

## 4. Plantillas de Excel propuestas

| Plantilla | Estado | Columnas que se digitan | Columnas que se calculan |
|---|---|---|---|
| **Leads y agendas** | Existe (`Plantilla_Embudo_Comercial.xlsx`), sin usar todavía, mezclada con Crédito | Fecha lead, Canal, Nombre, Teléfono, Fecha agenda visita, Estado agenda | Etapa actual (fórmula opcional) |
| **Crédito** | `[FALTA decidir]` — el prompt maestro sugiere separarla de Leads y agendas; hoy está fusionada en una sola hoja | Fecha formulario, Fecha decisión, Decisión, Motivo rechazo | % de aprobación (se calcula solo) |
| **Ventas y facturación** | Ya cubierta por `Inventario_2026.xlsx` (hojas Dashboard/Plan separe/Facturación) — no se propone una nueva, se valida la que existe | (las que ya tiene el archivo) | (las que ya tiene el archivo) |
| **Cartera y recaudo** | = `Proyeccion_Recaudo.xlsx`, con las 2 hojas nuevas ya especificadas | Detalle Cuotas se pega de SISMO; Meta se digita a mano | Cuotas a Cobrar del Mes, Cartera Vencida — 100% fórmula |
| **Inventario** | = `Inventario_2026.xlsx`, sin cambios | (las que ya tiene el archivo) | Días de inventario (nueva fórmula) |
| **Metas** | No existe como Excel — ver §3 | Meta ventas, meta recaudo, meta % aprobación, meta cumplimiento agendas, tope mora | — |

**Pregunta abierta**: ¿separamos "Leads y agendas" de "Crédito" en dos
plantillas (como sugiere el prompt maestro), o mantenemos una sola fila
por lead que avanza por todas las etapas (como está diseñada hoy)? La
plantilla actual ya sigue la filosofía "una fila por lead, se actualiza,
no se duplica" — separar en dos archivos obligaría a cruzar por
`id_lead` entre ambos. Mi lectura: mantenerlo en una sola plantilla es
más simple para un equipo que no programa (menos archivos que
sincronizar), pero es tu decisión.

---

## 5. Reglas de captura

`[FALTA información real del equipo para completar esta sección con
precisión — lo que sigue son valores por defecto razonables a confirmar,
no hechos verificados]`:

- **Quién llena cada plantilla**: hoy solo sé que Loren Borraiz es
  "Analista de Cobranza" y Yency Aya es "Analista de Ventas" (por sus
  contratos, ya cargados en RRHH). No sé quién sería responsable de
  Leads/Agendas, ni quién carga Inventario o Tesorería cada día.
- **A qué hora del día**: `[FALTA]` — el prompt menciona "carga manual
  cada mañana"; falta confirmar si aplica igual a los 5 archivos o solo
  a algunos.
- **Cómo se evita el doble registro**: hoy no hay mecanismo — la
  plantilla de Leads y agendas ya sigue "una fila por lead, se
  actualiza" (no se duplica), pero no hay una regla equivalente para
  quién actualiza Inventario o Recaudo si dos personas lo abren a la vez.
- **Qué pasa si alguien no carga su archivo**: no hay política definida
  hoy. Candidato: el tablero ya marca cada fuente con su propia fecha de
  corte (no fuerza una sola fecha "hoy") — así se nota de inmediato si
  algo quedó desactualizado, pero eso es una señal pasiva, no una regla
  de proceso.

---

## 6. Brechas — qué no se puede medir hoy

| Qué falta medir | Por qué no se puede hoy | Qué hay que empezar a hacer |
|---|---|---|
| Indicadores 1-7 (todo Demanda, Crédito, Agenda) | Nadie ha diligenciado la plantilla de Leads y agendas todavía | Empezar a registrar cada lead desde el primer día que se decida arrancar |
| % de aprobación, incumplimientos de agenda | Dependen de los indicadores 1-7 | Igual que arriba |
| Mora total confiable | La hoja que hoy la calcula (`Mora SISMO`) está congelada desde el 14-sep sin que se note | Reconstruir con fórmula viva (ya especificado, en pausa) |
| Cuotas a cobrar del mes (total crudo) | No existe ninguna hoja que lo calcule hoy | Construir la hoja ya especificada |
| Días de inventario | No hay fórmula construida todavía (dato sí existe) | Construir la fórmula sobre Inventario_2026.xlsx |
| Proyección de caja única y confiable | Dos modelos compitiendo sin resolver cuál es el oficial | Decisión de dirección: cuál modelo se adopta |
| Metas vigentes (ventas, recaudo, % aprobación, cumplimiento agendas, tope mora) | No se llenaron en el prompt maestro | `[FALTA: los cinco números, aunque sean aproximados]` |
| Dueño de cada etapa | No asignado | `[FALTA: quién es responsable de cada una de las 7 etapas]` |
| `id_cliente` estable entre archivos | No existe, se cruza por nombre (frágil) | Decisión: usar cédula como puente, o aceptar el riesgo |

---

## Decisiones — resueltas 2026-09-23

1. **Leads y Crédito: una sola plantilla.** El usuario delegó a mi
   recomendación (§4) — se mantiene el diseño actual, una fila por lead
   que avanza por todas las etapas, no se separa en dos archivos.

2. **Metas: hoja de Excel, no formulario web.** Recomendación dada y
   aceptada. Razón de fondo: el formulario web actual guarda en
   `data/objetivos.json`, que vive en el disco local del servidor de
   Streamlit — **el mismo problema de persistencia ya detectado para
   las cargas de datos** (Streamlit Community Cloud borra el disco
   local en cada reinicio/redespliegue). Si las metas solo viven ahí,
   se pierden igual que se perdería cualquier archivo subido. Pasan a
   vivir en la hoja "Metas" del Excel correspondiente, consistente con
   el resto de la arquitectura (todo persiste en los archivos que el
   usuario controla, la app no guarda nada propio).

3. **Cobro Sem 36-40: se reemplazan.** El usuario pidió optimizar por
   "orden y estructura sin ambigüedad ni redundancia" — 5 hojas casi
   idénticas repetidas cada mes es la definición de redundancia frente
   a las 2 hojas nuevas ya especificadas. **Pendiente de verificar**: si
   la columna "Confirmado" resulta tener un propósito operativo real (un
   paso de verificación manual que el equipo sí usa), se incorpora como
   columna dentro de "Cuotas a Cobrar del Mes" en vez de mantenerla en
   hojas aparte — se validará al construir, no se pierde silenciosamente.

4. **Proyección de caja — reemplazada por una fórmula propia, más
   simple que los dos modelos que competían.** Ninguno de los dos
   modelos existentes (`Proyección 18M` ni el del informe financiero) es
   el oficial — el usuario define una tercera fórmula, más directa:

   ```
   Resultado objetivo del mes =
       Ingreso objetivo por recaudo de cuotas semanales
     + Ingreso objetivo por cuotas iniciales
     − Gasto fijo $220.000.000
     − Pago a Auteco del mes
   ```

   De este resultado objetivo se deriva, hacia atrás, cuántas motos hay
   que tener garantizadas en inventario para cumplirlo — conecta
   directamente Tesorería con Etapa 4 (Venta) y Etapa 7 (Inventario).
   Esto **reemplaza** la sección "Proyección de caja" que hoy vive en
   la página de Tesorería (los dos modelos viejos) — se marcan para
   retirar cuando se construya.
   **Sin resolver todavía**: la fórmula exacta para pasar de "resultado
   objetivo del mes" a "# de motos garantizadas" — se construye en la
   siguiente fase, sobre esta base.

5. **Metas vigentes — confirmadas 2026-09-23**:
   - Meta de **ventas**: 100 unidades/mes.
   - Meta de **% de aprobación** de crédito: 60%.
   - Meta de **cumplimiento de agendas**: 80%.
   - **Tope de mora** aceptable: 7% de la cartera.
   - La **meta de recaudo** en pesos sale de la fórmula del punto 4
     (cuotas semanales + cuotas iniciales − gastos − Auteco), no es un
     número independiente.

6. **Dueño de todas las etapas**: Andrés (el usuario), por ahora. Se
   revisa cuando el proceso madure y haya más personas involucradas.

7. **Reglas de captura**: Andrés carga los datos por ahora, por las
   mismas razones del punto 6.

## Fase 1 — cerrada

Las 7 decisiones están resueltas. Fase 1 completa, sin código escrito,
tal como exige el prompt maestro. Queda a la espera de aprobación para
pasar a Fase 2 (permisos y gobierno del dato).
