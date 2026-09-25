# FASE 5 — Publicación · Dashboard BSC RODDOS

Entregable final del prompt maestro ROMA. Sin código — es una decisión de
la dirección, con la recomendación del asistente. Basado en lo ya
adelantado en la Parte 3 del prompt maestro original (dashboard.roddos.com
no es posible con el plan gratuito de Streamlit tal cual) y en las
decisiones ya tomadas en Fase 1 y 2 (carga manual, login con contraseña
compartida para RRHH/Tesorería).

---

## 3 caminos reales

### (a) Streamlit Community Cloud gratis + redirección de dominio

| | |
|---|---|
| **Costo** | $0/mes. La redirección de `dashboard.roddos.com` hacia la URL de Streamlit normalmente también es gratis (un registro DNS de redirección en el proveedor donde ya tienen registrado `roddos.com`, o un servicio gratuito de redirección). |
| **Dificultad** | Baja. Se conecta el repo de GitHub, unos clics, y queda publicado. |
| **Seguridad** | Soporta el Nivel 1 (app privada, lista de correos autorizados) nativo, sin código. El Nivel 2 (contraseña compartida para RRHH/Tesorería, ya diseñado en Fase 2) se agrega con `st.secrets`, sin costo extra. HTTPS automático. |
| **Limitación real** | El usuario **nunca ve `dashboard.roddos.com` en la barra de direcciones** — la redirección lo lleva a la URL real de Streamlit (`algo.streamlit.app`). Es como un acortador de link, no un dominio propio de verdad. Además: recursos compartidos con otras apps gratuitas (puede ir más lento en momentos de carga), y la app "duerme" si nadie la usa por varios días — tarda unos segundos en despertar la primera vez. |

### (b) Streamlit Cloud, plan de pago — DESCARTADA (verificado 2026-09-23)

No existe. Desde que Snowflake compró Streamlit, el único Streamlit de pago
es "Streamlit in Snowflake", que exige una cuenta de Snowflake (una bodega de
datos empresarial) — desproporcionado para este tablero. Community Cloud no
tiene plan de pago ni dominio propio. Para tener `dashboard.roddos.com` real
hay que ir a (c).

### (c) Hosting propio (servidor o servicio tipo Azure App Service/Railway/Render)

| | |
|---|---|
| **Costo** | Estimado orientativo (no verificado con un proveedor específico): servidores pequeños de este tipo suelen rondar entre $5 y $25 USD/mes, según el proveedor. `[FALTA cotizar con un proveedor concreto antes de decidir]`. |
| **Dificultad** | Alta. Hay que configurar el servidor, el dominio propio (DNS apuntando ahí), el certificado SSL (Let's Encrypt lo automatiza, pero hay que configurarlo), y mantenerlo actualizado en el tiempo. |
| **Seguridad** | Control total — se puede restringir por IP, poner cualquier tipo de login, firewall propio. Pero **la responsabilidad de mantenerlo seguro y actualizado es 100% de RODDOS** — más superficie de riesgo si nadie le hace mantenimiento. |
| **Nota** | Esto también recuperaría acceso directo a OneDrive/SharePoint en vivo — pero esa puerta ya se cerró explícitamente cuando se decidió carga manual para todo (Fase 1). No lo cuento como ventaja real de este camino, porque no vamos a reabrir esa decisión solo por esto. |

---

## Recomendación

**Empezar con (a) — Streamlit Community Cloud gratis + redirección.**
Razones:
- Ya está todo el código listo (Fases 1 a 4 completas) — se puede publicar
  hoy mismo sin gastar nada.
- Para 3 directores y un equipo pequeño, el Nivel 1 + Nivel 2 de
  autenticación ya diseñado cubre lo que se pidió (todos ven Recaudo/
  Inventario/Marketing, solo directores entran a RRHH/Tesorería) sin
  pagar nada extra.
- La limitación de "no ver el dominio en la barra de direcciones" es
  real pero menor para un uso interno diario — la redirección funciona
  igual, solo es un detalle visual.

**Migrar a (b)** el día que:
- El equipo crezca y valga la pena tener SSO real con las cuentas de
  Microsoft 365 que ya usan.
- La barra de direcciones con `dashboard.roddos.com` de verdad importe
  (por ejemplo, para presentarlo a alguien externo — inversionistas,
  banco, etc.).

**No recomiendo (c)** por ahora — el esfuerzo de mantenimiento no se
justifica ya que la razón que lo haría valioso (acceso directo a
OneDrive) ya se descartó.

---

## Requisitos de seguridad, sin importar el camino elegido

1. **Nivel 1** (app privada, correos autorizados) — se configura en el
   panel de Streamlit Cloud al momento de publicar. Se necesita la lista
   de correos: directores, Loren, Yency (ya definida en Fase 2 §1).
2. **Nivel 2** (contraseña compartida para RRHH/Tesorería) — hay que
   construirlo antes de publicar (no se hizo en Fase 4, quedó marcado
   como pendiente). Es código simple, `st.secrets` + `st.text_input`.
3. **Repo de GitHub** — Streamlit Cloud (gratis o pago) exige desplegar
   desde un repo de GitHub. Hoy este proyecto **no tiene control de
   versiones** (no hay `git init`). Encontré un archivo
   `TOKEN GITHUB - CLARA CODE.docx` en `BP 26\Tecnologia\` que sugiere
   que ya existe algo configurado — no lo abrí (podría tener
   credenciales) — `[FALTA confirmar contigo si esa cuenta/token ya
   sirve para este proyecto, o si se crea una nueva]`. Por política, no
   creo cuentas — esto lo defines y ejecutas tú, yo preparo el repo
   local y las instrucciones.

---

## Decisiones que necesito que tomes

1. ¿Empezamos con el camino (a) recomendado, o prefieres ir directo a
   (b) o (c)?
2. ¿La cuenta/token de GitHub que ya existe en `BP 26\Tecnologia\`
   sirve para este proyecto, o creas una nueva?
3. ¿Construyo ya el Nivel 2 de autenticación (contraseña para RRHH/
   Tesorería) antes de publicar, o publicamos primero sin eso y lo
   agregamos después?

## Decisiones — resueltas 2026-09-23

1. **Camino (a)**, Streamlit Community Cloud gratis. (b) no existe; se pasa
   a Render (donde corre COMPAS, desde $7 USD/mes) si se necesita
   `dashboard.roddos.com` real para mostrar a externos.
2. **GitHub: la misma cuenta de COMPAS**, repositorio privado aparte.
3. **Nivel 2 construido antes de publicar** (`acceso.py`): una clave de
   directores en `secrets.toml` → `[acceso] clave_directores`. Protege
   Tesorería, RRHH, la caja en Vista Reunión y la carga de Tesorería,
   RRHH, Metas y Conciliación. Sin clave configurada, todo queda cerrado.
   Limitación: no distingue a Loren de Yency en la carga (eso es Nivel 3).
4. **Respaldo en MongoDB** (`respaldo.py`), base `bsc_dashboard` del
   clúster de COMPAS con usuario propio — los archivos sobreviven a los
   reinicios de Streamlit Cloud.

## Fase 5 — historial

Con las 5 fases del prompt maestro completas (o en pausa donde
corresponde), este es el punto natural para revisar todo el recorrido
antes de tocar el paso final de publicar de verdad.
