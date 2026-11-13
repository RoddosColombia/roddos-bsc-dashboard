"""Columna "Canal venta" de Facturación (lo que DECLARA el cliente al asesor) → lista estándar.

Desde nov-2026 la columna es una lista desplegable con estas 10 opciones. Las ventas anteriores
traen texto libre ("REFERIDO/ERIKA", "PAUTA/FACEBOOK", "VOZ"…): aquí se convierten sin tocar el
Excel. El nombre de quien refiere NUNCA sale de esta función (va en la columna "Referido por").
"""
import re
import unicodedata

REFERIDO = "Referido"
VOZ_A_VOZ = "Voz a voz"
PAUTA_META = "Pauta Meta"
PAUTA_GOOGLE = "Pauta Google"
PAUTA_SIN_IDENTIFICAR = "Pauta sin identificar"
REDES_ORGANICAS = "Redes orgánicas"
CALLE = "Calle"
CLIENTE_RODDOS = "Cliente RODDOS"
ALIADO = "Aliado"
NO_RECUERDA = "No recuerda"
VACIO = "Sin dato"

OPCIONES = [REFERIDO, VOZ_A_VOZ, PAUTA_META, PAUTA_GOOGLE, PAUTA_SIN_IDENTIFICAR,
            REDES_ORGANICAS, CALLE, CLIENTE_RODDOS, ALIADO, NO_RECUERDA]


def _plano(texto):
    s = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.upper()).strip()


def normalizar(texto):
    """Texto de "Canal venta" → (canal estándar, dudoso). `dudoso` marca conversiones a revisar
    (p. ej. "INSTAGRAM" a secas: puede ser pauta o una publicación orgánica)."""
    s = _plano(texto)
    if not s:
        return VACIO, False
    base, _, detalle = s.partition("/")
    base, detalle = base.strip(), detalle.strip()

    # Valores ya estándar (lista desplegable).
    for op in OPCIONES:
        if base == _plano(op):
            return op, False

    if base.startswith("REFERID"):
        if "SIN ID" in base:
            return VOZ_A_VOZ, False
        return REFERIDO, False
    if base in ("EMPLEADO",):
        return REFERIDO, False
    if base.startswith("VOZ"):
        return VOZ_A_VOZ, False
    if base.startswith("PAUTA"):
        if re.search(r"FACEBOOK|INSTAGRAM|META|\bFB\b|\bIG\b", detalle):
            return PAUTA_META, False
        if "GOOGLE" in detalle or "YOUTUBE" in detalle:
            return PAUTA_GOOGLE, False
        return PAUTA_SIN_IDENTIFICAR, False
    if base in ("FACEBOOK", "INSTAGRAM", "META"):
        return REDES_ORGANICAS, True
    if base.startswith("ORGANIC") or base.startswith("REDES"):
        return REDES_ORGANICAS, False
    if base == "GOOGLE":
        return PAUTA_GOOGLE, True
    if base.startswith("VOLANT") or base.startswith("CALLE") or base.startswith("OFICINA"):
        return CALLE, False
    if base.startswith("RODDOTIZADO") or base.startswith("CLIENTE") or "ANTIGUO" in base:
        return CLIENTE_RODDOS, False
    if base.startswith("ALIAD"):
        return ALIADO, False
    if base in ("MERCATELY", "WHATSAPP", "NO RECUERDA", "NO SABE"):
        return NO_RECUERDA, False
    return NO_RECUERDA, True
