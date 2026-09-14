"""
Punto de entrada de la caja de herramientas.

Aquí solo se monta la navegación a partir de `comun/registro.py`. Cada
herramienta vive en su carpeta dentro de `herramientas/`:

    herramientas/<nombre>/vista.py   la pantalla (lo único que usa Streamlit)
    herramientas/<nombre>/motor.py   la lógica, sin Streamlit
    herramientas/<nombre>/datos/     catálogos, vocabularios, plantillas
    comun/                           lo que comparten varias herramientas

El menú de herramientas no va en la barra lateral de Streamlit sino dentro
de la banda negra de cada página (ver `comun/estilo.py`): así no depende
de ningún control interno de Streamlit y se ve igual en móvil.
"""

import streamlit as st

from comun.registro import PAGINAS

# Única llamada permitida a set_page_config. Las páginas no deben repetirla.
st.set_page_config(
    page_title="Herramientas · Oficina de Empleo",
    page_icon="◉",
    layout="wide",
)

paginas = [
    st.Page(
        h["ruta"], title=h["titulo"], icon=h["icono"],
        url_path=h["url"], default=(h["url"] is None),
    )
    for h in PAGINAS
]

st.navigation(paginas, position="hidden").run()
