"""Funnel de marketing por canal y campaña: lead → solicitud → aprobado → compra (RODDOTIZADO).

Se calcula una vez al día por fuera del tablero (GitHub Actions, funnel/ejecutar.py), cruzando:
  - CRM-RODDOS (WhatsApp: leads, anuncios de Meta, códigos LP de la landing)
  - RODDOS-web (solicitudes de crédito, origen guardado, decisión del asesor)
  - Inventario 2026.xlsx, pestaña Facturación (ventas: fecha, documento, celular, canal declarado)

Solo se guardan TOTALES (sin nombres, documentos ni teléfonos) en la base del tablero
(bsc_dashboard.funnel_resumen). La página pages/6_Marketing.py solo lee esos totales.
Modelo de atribución: docs/investigacion/09-modelo-atribucion-funnel.md en el repo de CRM-RODDOS.
"""
