"""Utilidades de texto compartidas. Python puro, sin Streamlit."""

import html
import re
import unicodedata


def normaliza(t):
    """Minúsculas, sin acentos y con los separadores raros pasados a espacio."""
    t = re.sub(r"[/\\_\-]+", " ", t)
    return "".join(
        c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
    ).lower().strip()


def esc(t):
    """Para meter texto ajeno dentro de markdown con unsafe_allow_html.

    Hace falta de verdad: los nombres de curso salen de un Excel que se
    descarga otra vez cada pocas semanas, y basta un & o un < en una celda
    para descuadrar la tarjeta entera.
    """
    return html.escape(str(t or ""))
