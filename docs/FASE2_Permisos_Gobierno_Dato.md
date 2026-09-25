# FASE 2 — Permisos y gobierno del dato · Dashboard BSC RODDOS

Entregable único de la Fase 2, según el prompt maestro ROMA del
2026-09-23. Sin código todavía — se detiene aquí a esperar aprobación
antes de Fase 3 (base técnica).

Parte de lo ya decidido en Fase 1: Andrés es dueño de las 7 etapas y
quien carga los datos **por ahora**; RRHH y Tesorería son privados para
los 3 directores; el resto (Recaudo, Inventario, Marketing) lo ve todo
el equipo.

---

## 1. Matriz de rol por módulo

La "escritura" acá significa **puede subir/reemplazar el archivo de esa
área** en la página "Actualizar datos" (no edición directa en el
dashboard — todo se actualiza por carga de Excel). "Lectura" significa
**puede ver esa página del dashboard**.

Roles que ya existen hoy en RODDOS (según RRHH, no inventados):
Directores (Andrés Sanjuan, Iván Echeverri, Fabián Enrique Carlos),
Analista de Cobranza (Loren Borraiz), Analista de Ventas (Yency Aya).

| Módulo | Directores | Analista de Cobranza | Analista de Ventas | Resto del equipo |
|---|---|---|---|---|
| Página principal (Demanda→Cartera→Inventario) | Lectura + Escritura | Lectura + Escritura (Recaudo) · Lectura (resto) | Lectura + Escritura (Ventas/Inventario, Marketing) · Lectura (resto) | Lectura |
| Tesorería | Lectura + Escritura | — sin acceso | — sin acceso | — sin acceso |
| RRHH | Lectura + Escritura | — sin acceso | — sin acceso | — sin acceso |
| Actualizar datos (subir archivos) | Todos los archivos | Solo Recaudo | Solo Inventario/Ventas y Marketing | — sin acceso |

**Importante — estado real hoy vs. objetivo**: Fase 1 ya estableció que
"por ahora" Andrés es el único dueño y el único que carga datos. Esta
matriz es el **objetivo** para cuando Loren y Yency empiecen a
interactuar directamente con el sistema — hoy, en la práctica, solo el
rol "Directores" está activo. La tabla queda lista para activarse por
persona sin tener que rediseñarla después.

`[FALTA confirmar]`: ¿Loren y Yency deben tener acceso YA (aunque sea de
lectura), o el acceso de ellas se activa después, cuando el proceso
madure — igual que se decidió para la captura de datos en Fase 1?

---

## 2. RRHH y Tesorería — tratamiento restringido

Ya decidido en Fase 1/handshake: solo los 3 directores. Técnicamente
esto significa que `pages/1_Tesoreria.py` y `pages/2_RRHH.py` deben
quedar **ocultas y bloqueadas** para cualquiera que no haya iniciado
sesión como director — no basta con no mostrar el link en el menú (eso
es solo estética; alguien podría escribir la URL directamente). El
bloqueo real se construye en Fase 3/4 con la librería de autenticación
que se elija abajo.

---

## 3. Opciones de autenticación en Streamlit — de más simple a más robusta

| Nivel | Qué es | Esfuerzo | Qué resuelve | Qué NO resuelve |
|---|---|---|---|---|
| **0 — Ninguna** (estado actual) | Cualquiera con el link ve todo | Cero | Nada — solo sirve para desarrollo local | Todo lo de permisos |
| **1 — App privada de Streamlit Community Cloud** | Lista de correos autorizados; Streamlit pide iniciar sesión con Google/email antes de mostrar la app | Bajo — se configura en el panel de Streamlit Cloud, sin escribir código | Que solo el equipo de RODDOS (nadie externo) vea la app | No separa RRHH/Tesorería del resto — es todo o nada |
| **2 — Contraseña compartida para el módulo restringido** | `st.secrets` guarda una contraseña; un `st.text_input(type="password")` la pide antes de mostrar Tesorería/RRHH | Bajo — decenas de líneas de código | Separar RRHH/Tesorería del resto sin gestionar usuarios individuales | No sabe quién entró (una sola contraseña para los 3 directores); si se comparte la contraseña, se pierde el control |
| **3 — Usuario y contraseña por persona** (`streamlit-authenticator`) | Cada persona tiene su propio usuario; contraseñas guardadas con hash; controla qué páginas ve cada quien según su rol | Medio — es la matriz de roles de arriba hecha realidad, pieza por pieza | Todo lo de la matriz de roles, con registro de quién entra | Hay que mantener la lista de usuarios/contraseñas en algún archivo — mismo riesgo de persistencia que el resto de los datos si se guarda solo en el servidor |
| **4 — Login con cuenta de Microsoft 365** (SSO/OAuth) | Cada persona entra con su cuenta corporativa ya existente (la misma de OneDrive/correo) | Alto — requiere registrar una app en Azure AD, similar a lo que se necesitaría para conectar OneDrive directamente | No gestionar contraseñas propias del dashboard en absoluto | Configuración inicial más compleja; no es necesario para un equipo de 5 personas |

### Recomendación

**Nivel 1 + Nivel 2 combinados** para empezar:
- Nivel 1 (app privada de Streamlit Cloud) para que nadie externo a
  RODDOS pueda siquiera abrir el link.
- Nivel 2 (contraseña compartida entre los 3 directores) específica
  para desbloquear Tesorería y RRHH dentro de la app.

Razón: con 5 personas conocidas hoy (3 directores + 2 analistas), el
Nivel 3 (usuario por persona) es más control del que hace falta
todavía, y el Nivel 4 es esfuerzo de configuración que no se justifica
a esta escala. Se migra a Nivel 3 cuando el equipo crezca o cuando
Loren/Yency necesiten roles distintos entre sí (hoy la matriz ya está
lista para eso, solo falta la librería).

`[FALTA confirmar]`: ¿una sola contraseña compartida entre los 3
directores es aceptable, o prefieres usuario+contraseña individual
desde ya (saltar directo a Nivel 3)?

---

## 4. Política de versiones y respaldo

Cada carga en "Actualizar datos" **reemplaza por completo** el archivo
anterior (decisión ya tomada). Eso tiene un riesgo real: si alguien
sube el archivo equivocado, o una versión a medio actualizar, se pierde
la buena sin poder deshacerlo.

**Propuesta**:
1. Antes de guardar el archivo nuevo, la app guarda automáticamente una
   copia con fecha y hora del archivo que está reemplazando (ej.
   `data_raw/versiones/Proyeccion_Recaudo_2026-09-24_1430.xlsx`).
2. Se mantienen las últimas `[FALTA: cuántas — propongo 10]` versiones
   de cada archivo, o las de los últimos `[FALTA: cuántos días —
   propongo 30]` días, lo que sea más simple de mantener.
3. Si algo sale mal, cualquier director puede descargar una versión
   anterior desde esa carpeta y volver a subirla.

**Límite honesto de esta política**: como ya se documentó, el
disco local del servidor de Streamlit Cloud se borra en cada
reinicio/redespliegue de la app — este historial de versiones
**tampoco sobrevive a eso**. Solo protege contra "subí el archivo
equivocado en esta sesión de trabajo", no es un respaldo a largo
plazo. El respaldo real de largo plazo sigue siendo que cada quien
mantenga su copia maestra en su OneDrive (como ya se hace hoy) — la
app nunca es la única copia de nada.

---

## Decisiones — resueltas 2026-09-23

1. **Loren y Yency: acceso desde ya**, con la matriz de roles de §1
   (Loren = lectura+escritura en Recaudo, lectura en el resto; Yency =
   lectura+escritura en Inventario/Ventas y Marketing, lectura en el
   resto). No se espera a que el proceso "madure" — se activa de una.
2. **Contraseña compartida entre los 3 directores (Nivel 2)** —
   confirmado, no se pasa a usuario individual todavía.
3. **Respaldo mínimo**: el usuario pidió explícitamente "las menos
   posibles por costo, lo que consuma menos". Se ajusta la propuesta:
   en vez de un historial de 10 versiones/30 días, se guarda **solo la
   última versión anterior** de cada archivo (se sobreescribe con cada
   carga nueva) — alcanza para deshacer el error más reciente sin
   acumular espacio con el tiempo.

## Fase 2 — cerrada

Las 3 decisiones están resueltas. Queda a la espera de aprobación para
pasar a Fase 3 (base técnica: arquitectura, comparación de carga
manual vs. OneDrive, estructura de carpetas, requirements.txt,
validador de archivos).
