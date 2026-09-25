# Handshake · Dashboard BSC de RODDOS

Status: draft, interview in progress

> **2026-09-23 — el usuario formalizó un prompt maestro (metodología
> ROMA) que adopta este proyecto y lo organiza en 5 fases.** Ver
> [`FASE1_Auditoria_Diseno_Dato.md`](FASE1_Auditoria_Diseno_Dato.md) —
> ya cerrada, con las 7 decisiones resueltas. Ese documento **supera**
> el "Orden de trabajo" descrito más abajo en este archivo (recaudo →
> probar carga → diseño → publicación) — el orden vigente ahora es el
> de las 5 fases del prompt maestro (dato → permisos → base técnica →
> dashboard → publicación). Este archivo se mantiene como bitácora de
> contexto general; el detalle vivo de cada fase vive en su propio
> documento (`FASE1_...md`, `FASE2_...md`, etc.).

## The idea in plain words
TODO — se completa cuando pase el read-back.

## Por qué importa
RODDOS controla su operación en varios Excel sueltos (recaudo, inventario,
tesorería, nómina). Nadie tiene, hoy, un solo lugar donde ver rápido "¿cómo
nos fue ayer, cómo vamos esta semana, cómo vamos este mes?" en cada frente
del negocio. Recaudo en particular es "un dolor de cabeza": no hay forma
fácil de ver, a inicio de mes, el total de cuotas por cobrar para armar la
meta del mes y de la semana.

## Para quién es
El equipo operativo y gerencial de RODDOS (Andrés, Iván, y quien haga
seguimiento de cobranza/ventas/inventario/tesorería/nómina día a día).
TODO: ¿lo va a mirar alguien más además de los 3 socios? ¿cobranza tiene
acceso directo o se lo muestran en reunión?

## Qué existe hoy
Repo local (sin control de versiones todavía) en
`C:\Users\AndresSanJuan\roddos-workspace\DASHBOARDS\bsc-streamlit\`, app
Streamlit multipágina:

- **`app.py`** — página principal. 21 rubros del embudo comercial + cartera
  (leads → formularios → aprobados/rechazados → agendas de visita → ventas →
  facturación → cuotas iniciales → activaciones → cuotas/pagos/vencidas →
  mora → inventario), organizados en 3 secciones (ayer / esta semana / este
  mes), con objetivos mensuales editables y proyección de cierre de mes.
  Probado end-to-end con los datos reales de Recaudo e Inventario.
- **`pages/1_Tesoreria.py`** — caja hoy/semana/mes desde el archivo real de
  flujo de caja, más un modelo de proyección estático (piso de
  supervivencia, tomado del informe financiero ya entregado aparte). El
  archivo real tiene su propia hoja "Proyección 18M" con otros supuestos —
  **no está integrada**, quedó como nota pendiente.
- **`pages/2_RRHH.py`** — nómina completa de los 8 empleados (incluida
  Yency Aya, agregada esta sesión con datos de su contrato real),
  vacaciones, brecha legal de retención. No sigue el esquema
  ayer/semana/mes (la nómina es mensual).
- **`pages/0_Actualizar_Datos.py`** — página centralizada para subir los 5
  archivos fuente. **Escrita en esta sesión, sin probar todavía.**
- **`plantillas/Plantilla_Embudo_Comercial.xlsx`** — plantilla diseñada
  para capturar leads/formularios/decisiones/agendas (Marketing no tenía
  ningún Excel). Su lectura y cálculo se probó con filas de prueba; el
  archivo real sigue vacío, nadie ha empezado a diligenciarlo.
- **Sin control de versiones**: no hay `git init`, no hay repo remoto. Para
  publicar en Streamlit Community Cloud hace falta un repo en GitHub — no
  existe todavía.
- Quedan dos archivos sueltos de depuración (`data_raw/headers_repr.txt`,
  `data_raw/out.txt`) sin limpiar.

## Cómo se ve el éxito
TODO — depende de la decisión de "norte" (ver Decisiones abiertas #1).

## Decisiones ya tomadas
- **Metodología**: para cada frente del negocio (excepto RRHH), responder 3
  preguntas — cómo nos fue ayer, cómo vamos esta semana, cómo vamos este
  mes — sobre 21 rubros concretos, del lead hasta la mora. RRHH no sigue
  este esquema porque la nómina es mensual, no diaria.
- **Destino de publicación**: Streamlit Community Cloud (decidido de
  entrada, confirmado de nuevo en esta sesión).
- **Arquitectura de datos**: como Streamlit Community Cloud no tiene acceso
  a OneDrive/SharePoint, **no hay lectura en vivo** de ningún archivo.
  Los 5 archivos fuente (Recaudo, Inventario, Conciliación SISMO↔Wava,
  Tesorería, RRHH) y el de Marketing se actualizan por **carga manual**:
  alguien sube el Excel real a la página "Actualizar datos", cada carga
  reemplaza por completo los datos anteriores (no se acumulan fragmentos).
- **Marketing/leads**: no existía ningún archivo. Se diseñó una plantilla
  de Excel propia (no una conexión a nada) porque es un proceso nuevo, no
  uno que ya exista en el equipo.
- **Diseño visual — dirección confirmada**: dark mode con la paleta oficial
  RODDOS (`#121212` fondo, `#00E5FF` cian, `#00C853` verde), tipografía
  Montserrat/Raleway. Referencia de estilo: el "después" de
  `datacreativa-academy.com` (tarjetas dark-mode, acento verde-turquesa).
  Confirmado por el usuario 2026-09-23.
- **Orden de trabajo — REVISADO 2026-09-23 (reemplaza el orden anterior)**:
  > "No partamos de interpretar que los excels que tenemos hoy son los
  > correctos, si hay que plantear nuevos, hagámoslo" (usuario, 2026-09-23)
  1. **Estructuración de los Excel** — para cada una de las 5 áreas
     (Recaudo, Inventario, Tesorería, RRHH, Marketing), decidir explícitamente
     si el archivo actual es la base correcta o si hay que replantearlo
     desde cero, **antes** de agregarle hojas o construir nada encima. No
     se asume que ninguno está bien solo porque ya existe.
  2. **Permisos** — quién lee qué (ver "Control de acceso" abajo).
  3. **Base del dashboard** — el contenido/lógica funcionando en local.
  4. **Diseño del dashboard** — visual, al final.
  Publicación en Streamlit Cloud y repo de GitHub siguen sin bloquear nada
  de esto — se resuelven después del paso 4.

## Identidad visual (investigado)
Del `Brandbook RODDOS.pptx` oficial (`OneDrive - RODDOS SAS\BP 26\Versión 2\`):

- **Paleta oficial — "Dark Mode"**:
  - RODDOS Black `#121212` — base principal.
  - Cyber Cyan `#00E5FF` — tecnología/datos precisos, "el color del Radar".
  - Growth Green `#00C853` — dinero, aprobación, "Siga", crecimiento.
- **Tipografía**: Montserrat Extra Bold (titulares), Raleway (cuerpo de texto).
- **Tono de marca**: "Financing Motion" — héroe/facilitador, velocidad,
  transparencia radical, tecnología con empatía. Semáforo en verde como
  símbolo.
- El logo confirma esto: versión sobre fondo negro con ícono en
  verde/cian concéntrico es la aplicación "nativa" de la marca, no una
  variante secundaria.

Dos referencias externas revisadas (pedidas por el usuario, de cuentas que
venden prompts/cursos para generar dashboards con IA):

1. `ricardomonsalve.com` — ejemplo "Pipeline Comercial Q1 2026": tarjeta
   blanca, un KPI "héroe" con relleno de color sólido, los demás KPI en
   blanco con número grande y delta en verde, gráficas a color, banner de
   "Análisis IA" a todo el ancho. Estilo claro, cálido (naranja) — **no
   coincide con la marca RODDOS** (que es dark mode), pero el patrón de
   composición (jerarquía de tarjetas, KPI héroe, banner de análisis) es
   reutilizable con otra paleta.
2. `datacreativa-academy.com` (Método IMPACT) — comparación antes/después:
   el "después" es un dashboard dark-mode con acento verde-turquesa, muy
   cercano a la paleta oficial de RODDOS. **Es la referencia de estilo más
   alineada con la marca.**

El mismo sitio de ricardomonsalve.com lista sus 45 prompts en 9 categorías
— útil no como producto a comprar, sino como catálogo de qué KPIs/vistas
son estándar por tipo de reporte. Dos calzan directo con problemas ya
identificados en este proyecto:
- **"Financiero y operación → Cuentas por cobrar (aging + DSO)"** — es
  literalmente el problema de Recaudo que el usuario señaló (ver decisión
  abierta #2). "Aging" (antigüedad de cartera por rangos de días) y DSO
  (Days Sales Outstanding) son vocabulario financiero estándar para esto
  — vale la pena revisar si reestructurar la vista de recaudo alrededor de
  ese concepto, en vez de la estructura semanal actual.
- **"Comercial y ventas → Funnel de conversión con drop-off"** y
  **"Análisis de fuentes de leads (CAC por canal)"** — coinciden con el
  embudo comercial (rubros 1-7) ya diseñado para Marketing.

## Recaudo — especificación (definida 2026-09-23, EN PAUSA)

> **Estado**: el contenido de esta sección (2 hojas nuevas) se definió
> antes de que el usuario pidiera el reinicio de orden (ver "Orden de
> trabajo — REVISADO"). Se intentó empezar a construirlas sobre
> `Proyeccion_Recaudo.xlsx` tal como existe hoy — **eso quedó en pausa**.
> Antes de retomarlo hay que resolver el paso 1 del nuevo orden: ¿es
> `Proyeccion_Recaudo.xlsx` la base correcta, o hay que replantearlo? El
> contenido de abajo sigue siendo válido como especificación de qué
> información se necesita — lo que no está decidido es en qué archivo va.

**Sigue el mismo método de control** (ayer / esta semana / este mes) que el
resto del tablero. Lo que falta es la base para armar la meta del mes.

1. **"Cuotas a Cobrar del Mes"** — el total crudo, antes de negociar la
   meta. Una fila por semana de cobro (usando el mismo calendario de
   cobro ya establecido — semana ISO lunes-domingo, arranca en el
   parámetro "primer día del calendario de cobro", no el mes calendario),

1. **"Cuotas a Cobrar del Mes"** — el total crudo, antes de negociar la
   meta. Una fila por semana de cobro (usando el mismo calendario de
   cobro ya establecido — semana ISO lunes-domingo, arranca en el
   parámetro "primer día del calendario de cobro", no el mes calendario),
   con # de cuotas y valor total de esa semana, más una fila TOTAL al
   final. Es distinta de la "Meta de la semana" que ya existe en la hoja
   `Resumen Semanal` — esa ya viene negociada/ajustada (ej. 85% del
   total); esta hoja nueva es el 100% crudo que sirve de punto de partida
   antes de negociar.
2. **"Cartera Vencida" (aging)** — una fila por cada cuota vencida (no
   agrupada), con su valor individual, ordenada de más antigua a más
   reciente por edad de mora. Incluye fila(s) de resumen con el total en
   pesos y el número total de cuotas vencidas.
   - **Edad de mora**: se calcula (fecha de corte − fecha de vencimiento
     de la cuota), **no** con el campo "Días Retraso" de SISMO (solo se
     llena cuando la cuota ya se pagó — trampa ya documentada en
     `DASHBOARDS/CLAUDE.md`).

**Sin resolver todavía**: layout exacto de columnas de cada hoja, si debe
ser fórmula-viva (recalcula solo al pegar la descarga de SISMO, como el
resto del archivo — "Excel puro") — se asume que sí, matching el patrón
existente del archivo, y si "Cuotas a Cobrar del Mes" debe excluir
cuotas de créditos cerrados/anulados (la regla ya existente en el
proyecto dice que sí para todo lo que es "meta" — se asume que aplica
igual aquí salvo que se diga lo contrario).

## Control de acceso (decidido 2026-09-23, pendiente de construir)

**No todos ven todo.** Dos niveles:
- **Todo el equipo**: Recaudo/Cartera (incluye ingreso), Inventario,
  Marketing/leads.
- **Solo socios**: RRHH (nómina) y Tesorería (caja).

Streamlit Community Cloud gratis solo soporta privacidad a nivel de **app
completa** (lista de correos autorizados, todo o nada) — no separa página
por página. Para este esquema hace falta **login con roles construido a
mano** (ej. `streamlit-authenticator` u otra librería), que oculte/bloquee
`pages/1_Tesoreria.py` y `pages/2_RRHH.py` según quién inició sesión. Es
trabajo de ingeniería real, no una casilla que se marca.

**Sin resolver todavía**: quiénes exactamente son "socios" (¿Andrés, Iván,
Fabián — los 3 con contrato de dirección en RRHH?), y esto es una tarea
de la fase de publicación, no bloquea el trabajo local de ahora — se
construye cuando llegue el momento de publicar (ver "Decisiones ya
tomadas → Orden de trabajo").

## Decisiones todavía abiertas

1. **Layout exacto de las 2 hojas nuevas de recaudo** — ver "Recaudo —
   especificación" arriba, sección "Sin resolver todavía". Se puede
   avanzar con una propuesta de columnas concreta y corregir sobre eso.

2. **Repositorio y despliegue** — no hay repo Git ni cuenta de GitHub
   conectada todavía. Streamlit Community Cloud exige desplegar desde un
   repo de GitHub. Falta decidir: ¿cuenta de GitHub de RODDOS (nueva o
   existente), quién la crea (el usuario, no el asistente — política de
   nunca crear cuentas), y si el repo es privado o público.

3. **Proyección 18M vs. modelo del informe (Tesorería)** — dos modelos de
   proyección de caja conviven sin integrarse. Sigue sin resolverse si se
   reemplaza uno por otro, se muestran ambos, o se deja como está.

4. **Quiénes son "socios"** para el login con roles — ver "Control de
   acceso" arriba.

5. **Librería de autenticación** a usar para el login con roles (ej.
   `streamlit-authenticator`) — investigar antes de construirlo.

## Restricciones y límites
- Streamlit Community Cloud: sin acceso a OneDrive/SharePoint, sin
  persistencia de archivos entre reinicios del servidor, sin dominio
  propio (siempre `*.streamlit.app`).
- El asistente nunca crea cuentas (GitHub, Streamlit Cloud, etc.) — eso lo
  hace el usuario.
- Los datos son reales y sensibles (nómina, cuentas por cobrar, caja) —
  ya se tomaron precauciones (backups antes de editar Excel en vivo,
  validación de hoja antes de sobrescribir en las cargas).

## Fuera de alcance
TODO — no se ha hablado explícitamente de qué NO es parte de este
dashboard. Candidatos a confirmar: ¿RRHH avanzado (rotación, ausentismo)?
¿Integraciones con Alegra/SISMO más allá de lectura de Excel exportado?

## Preguntas abiertas para investigar
1. ¿Streamlit Community Cloud sigue siendo la mejor opción dado que
   "auto-hospedar" resolvía tanto el acceso a OneDrive como el dominio
   propio? (El usuario ya lo descartó explícitamente eligiendo carga
   manual — se documenta la razón, no se reabre solo, pero vale
   mencionarlo si el norte cambia).
2. Estado real de una cuenta de GitHub de RODDOS: ¿existe ya o hay que
   crearla?

## Notas para quien planifique después
- **Orden confirmado**: 1) recaudo (decisión abierta #1) → 2) probar
  `pages/0_Actualizar_Datos.py` (escrito, sin probar) y el resto del
  contenido local → 3) diseño visual (dirección ya decidida) → 4) login
  con roles (RRHH y Tesorería restringidos a socios) + repo GitHub +
  publicación. No saltar este orden sin volver a preguntar.
- El archivo de recaudo es trabajo sobre un Excel que usa el equipo a
  diario, no solo sobre el dashboard — tiene su propio riesgo operativo
  si se cambia mal.
- Ya existe un patrón de trabajo probado y aceptado por el usuario para
  estas conversaciones: brainstorm corto (problema en una frase, 2-3
  opciones, la más simple) antes de escribir código nuevo — no saltar a
  construir sin ese paso, es la causa raíz de la sensación de desorden de
  esta sesión.
