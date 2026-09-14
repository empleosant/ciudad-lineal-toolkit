"""Utilidades de texto compartidas. Python puro, sin Streamlit."""

import re
import unicodedata


def normaliza(t):
    """Minúsculas, sin acentos y con los separadores raros pasados a espacio."""
    t = re.sub(r"[/\\_\-]+", " ", t)
    return "".join(
        c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
    ).lower().strip()
