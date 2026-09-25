# RODDOS BSC — cómo correrlo en tu computador

Guía sin conocimientos técnicos. Solo la primera vez toma unos minutos;
después es un solo comando cada vez que quieras abrir el tablero.

## La primera vez

### 1. Instalar Python

1. Ve a [python.org/downloads](https://www.python.org/downloads/) y
   descarga la versión más reciente.
2. Al instalar, **marca la casilla "Add Python to PATH"** antes de darle
   a Instalar — es el paso que más gente se salta y después no funciona
   nada.

### 2. Abrir una terminal en esta carpeta

- En Windows: abre esta carpeta (`bsc-streamlit`) en el explorador de
  archivos, haz clic derecho dentro de ella y busca "Abrir en Terminal"
  (o "Abrir ventana de PowerShell aquí").
- En Mac: abre la app "Terminal", escribe `cd ` (con el espacio) y
  arrastra la carpeta `bsc-streamlit` a la ventana, luego Enter.

### 3. Instalar lo que la app necesita

Copia y pega esto en la terminal que abriste, y presiona Enter:

```
pip install -r requirements.txt
```

Espera a que termine (puede tardar 1-2 minutos la primera vez).

## Cada vez que quieras abrir el tablero

En la misma terminal (repite el paso 2 de arriba si la cerraste), pega:

```
streamlit run app.py
```

Se va a abrir solo una pestaña en tu navegador con el tablero. Si no se
abre sola, la terminal te muestra una dirección como
`http://localhost:8501` — cópiala y pégala en Chrome o el navegador que
uses.

Para cerrar el tablero: vuelve a la terminal y presiona `Ctrl + C`.

## Cómo se actualiza la información

El tablero **no lee tus archivos automáticamente** — hay que subirlos:

1. Con el tablero abierto, ve a **📤 Actualizar datos** en el menú de la
   izquierda.
2. Para cada archivo (Recaudo, Inventario, Tesorería, RRHH, Marketing,
   Metas), sube la versión más reciente que ya manejas.
3. Si algo está mal diligenciado, la app te lo dice en español y te dice
   en qué fila está el problema — corrígelo en tu Excel y vuelve a
   subirlo.
4. Si todo está bien, verás "Cargado y recalculado" y el tablero se
   actualiza solo.

## Qué archivos necesitas tener a mano

| Página del tablero | Archivo que subes |
|---|---|
| Recaudo/Inventario (página principal) | `Proyeccion_Recaudo...xlsx`, `Inventario_2026.xlsx`, `Cruce_SISMO_Wava...xlsx` |
| Tesorería | `Flujo de pagos deudas.xlsx` |
| RRHH | `Control_RRHH_Nomina_RODDOS_2026.xlsx` |
| Marketing / leads | `Embudo_Comercial_RODDOS.xlsx` (si no lo tienes, descárgalo desde la página principal) |
| Metas de todas las páginas | `Metas_RODDOS.xlsx` (agrega una fila nueva cada mes, no borres las anteriores) |

## Si algo sale mal

- **"pip no se reconoce como un comando"** — Python no quedó en el PATH.
  Vuelve a instalar Python y marca la casilla "Add Python to PATH".
- **La terminal dice que falta un módulo** — vuelve a correr
  `pip install -r requirements.txt`.
- **Subiste un archivo y dice que le faltan hojas o columnas** — es
  probable que hayas subido el archivo equivocado, o que el que
  exportaste de SISMO/Inventario/etc. tenga un formato distinto al
  esperado. Revisa el mensaje de error, dice exactamente qué falta.
- **Subiste un archivo malo por error** — hay una copia de la versión
  anterior guardada en `data_raw/versiones/`. Pídele a quien te ayudó a
  construir esto que la recupere.
