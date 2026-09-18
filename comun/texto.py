"""Utilidades de texto compartidas. Python puro, sin Streamlit."""

import html
import re
import unicodedata


def normaliza(t):
    """Minúsculas, sin acentos, los separadores raros pasados a espacio y UN
    solo espacio entre palabras.

    Lo último hace falta porque no todo se compara palabra a palabra. En el
    buscador hay dos sitios que miran la cadena entera: las claves de varias
    palabras del vocabulario, que se buscan con `clave in q`, y el bonus por
    coincidencia exacta, que compara la consulta con la denominación.

    Sin colapsar los espacios, escribir dos seguidos cambiaba la respuesta. Con
    «teleoperadora de atencion al cliente» la clave «atencion al cliente»
    casaba y salía primero EMPLEADOS DEL ÁREA DE ATENCIÓN AL CLIENTE; con
    espacios de más dejaba de casar y salía TELEOPERADORES. La misma consulta y
    dos respuestas distintas, según lo rápido que escriba quien pregunta.

    Los guiones, barras y guiones bajos ya se colapsaban porque el patrón de
    arriba lleva un +. A los espacios les faltaba lo mismo.
    """
    t = re.sub(r"[/\\_\-]+", " ", t)
    t = "".join(
        c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", t).lower().strip()


def esc(t):
    """Para meter texto ajeno dentro de markdown con unsafe_allow_html.

    Hace falta de verdad: los nombres de curso salen de un Excel que se
    descarga otra vez cada pocas semanas, y basta un & o un < en una celda
    para descuadrar la tarjeta entera.
    """
    return html.escape(str(t or ""))
