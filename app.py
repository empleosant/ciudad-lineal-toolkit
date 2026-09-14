"""
Punto de entrada de la caja de herramientas.

Aquí solo se define la navegación. Cada herramienta vive en su carpeta
dentro de `herramientas/` y se registra en la lista de abajo. Añadir una
herramienta nueva es crear su carpeta y añadir una línea a HERRAMIENTAS.

    herramientas/<nombre>/vista.py   la pantalla (lo único que usa Streamlit)
    herramientas/<nombre>/motor.py   la lógica, sin Streamlit (paso 2)
    herramientas/<nombre>/datos/     catálogos, vocabularios, plantillas
    comun/                           lo que comparten varias herramientas
"""

import streamlit as st

# Única llamada permitida a set_page_config. Las páginas no deben repetirla.
st.set_page_config(
    page_title="Herramientas · Oficina de Empleo",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="auto",
)

HERRAMIENTAS = [
    st.Page(
        "herramientas/sispe/vista.py",
        title="Codificador SISPE",
        icon=":material/manage_search:",
        url_path="sispe",
        default=True,
    ),
    st.Page(
        "herramientas/cv/vista.py",
        title="Generador de CV",
        icon=":material/description:",
        url_path="cv",
    ),
]

pagina = st.navigation({"Herramientas": HERRAMIENTAS})
pagina.run()
