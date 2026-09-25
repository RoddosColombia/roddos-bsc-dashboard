# FASE 4 — Diseño y código del dashboard · Dashboard BSC RODDOS

Entregable de la Fase 4, según el prompt maestro ROMA. Todo probado en
vivo contra los datos reales (no solo revisado en el código).

## Lo que se construyó

1. **Metas en Excel** (`plantillas/Metas_RODDOS.xlsx`, cargado como
   cualquier otro archivo en 📤 Actualizar datos). Reemplaza el
   formulario web y `data/objetivos.json` — ese sistema se retiró por el
   problema de persistencia de Streamlit Cloud ya documentado.
   `objetivos.py` quedó solo con la lógica de cálculo, sin nada que
   dependa de dónde vive el dato.

2. **2 indicadores nuevos** (de la Parte 1 del prompt maestro):
   - **% de aprobación de crédito** — calculado desde el embudo comercial.
   - **Días de inventario** — motos disponibles ÷ ritmo de venta del mes.
     Probado: con 18 disponibles y 26 vendidas en 22 días, da 15,2 días.

3. **Resultado objetivo del mes** (Tesorería) — reemplaza los dos
   modelos de proyección que competían. Fórmula de la dirección:
   ```
   Ingreso objetivo recaudo semanal (Recaudo · Resumen Semanal, vivo)
   + Ingreso objetivo cuotas iniciales (Metas_RODDOS.xlsx)
   − Gasto fijo mensual (Metas_RODDOS.xlsx)
   − Pago a Auteco del mes (Tesorería · Facturas Auteco, calculado en vivo)
   = Resultado objetivo del mes
   ```
   Probado con datos reales de septiembre: $180.748.983 + $175.000.000
   − $220.000.000 − $123.392.031 = **$12.356.952**. El pago a Auteco no
   se le preguntó a nadie — ya estaba calculable en el archivo real
   (saldo pendiente de facturas con "Mes de pago" = mes en curso).

4. **`pages/3_Vista_Reunion.py`** — cubre a la vez "una vista por cada
   etapa del embudo" y "vista de reunión de 15 minutos": las 7 etapas
   (`metricas.ETAPAS`, nueva constante compartida) más Tesorería, un
   renglón por indicador con semáforo, pensada para proyectar en
   pantalla.

5. **`README.md`** — instrucciones paso a paso para correr la app en
   local sin saber programar (instalar Python, instalar dependencias,
   `streamlit run app.py`, cómo actualizar datos, qué hacer si algo
   sale mal).

## Probado end-to-end (no solo revisado)

- Página principal: ventas ahora compara contra meta 100 (antes 90),
  activaciones reusa la misma meta, pagos de cuotas usa la meta pactada
  en vivo de Recaudo (ya no un número fijo en el código).
- Expander "🎯 Metas del mes": muestra 100 / 60% / 80% / 7%, coincide con
  lo cargado en `Metas_RODDOS.xlsx`.
- Tesorería: "Resultado objetivo del mes" verificado cifra por cifra.
- Vista de reunión: las 7 etapas + Tesorería renderizan sin errores,
  semáforos correctos (Rezagado en ventas/cuotas iniciales/activaciones,
  igual que en la página principal).
- RRHH: confirmado que sigue funcionando sin cambios después de tocar
  `data_sources.py`.

## Lo que se dejó fuera de esta fase (para no improvisar)

- **Login con roles** (Fase 2, Nivel 1+2) — no se construyó todavía.
  Sigue siendo tarea de la fase de publicación, no bloquea el uso local.
- **Layout exacto de las 2 hojas nuevas de recaudo** (Cuotas a Cobrar
  del Mes, Cartera Vencida) — quedó en pausa desde antes de este
  reinicio de orden (ver `handshake_bsc_dashboard.md`). No se retomó en
  esta fase porque no era parte explícita del alcance de Fase 4.
- **Vista de reunión**: no tiene todavía botón de "imprimir/exportar" ni
  modo de pantalla completa — se puede agregar si hace falta en el uso
  real.

## Fase 4 — cerrada

Todo lo pedido en el alcance está construido, probado con datos reales,
y documentado. Queda a la espera de aprobación para pasar a Fase 5
(publicación: alternativas para `dashboard.roddos.com`, costo, nivel de
dificultad, requisitos de seguridad, recomendación).
