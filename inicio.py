"""
Portada de la caja de herramientas.

Una tarjeta por herramienta, a partir de `comun/registro.py`. Aquí no hay
lógica: solo presentación.
"""

import streamlit as st

from comun import estilo
from comun.registro import HERRAMIENTAS

estilo.aplica()

try:
    banda = st.container(key="cabecera")
except TypeError:
    banda = st.container()
with banda:
    estilo.menu("inicio")
    st.markdown(
        '<div class="rotulo">Oficina de Empleo <span>&middot;</span> Ciudad Lineal</div>'
        '<div style="color:#fff;font-size:clamp(1.2rem,1.45vw,1.45rem);font-weight:700;'
        'letter-spacing:-.025em;margin-bottom:.35rem">Herramientas de orientación</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="seccion">Herramientas</div>', unsafe_allow_html=True)

try:
    rejilla = st.container(key="tarjetas")
except TypeError:
    rejilla = st.container()
with rejilla:
    for i in range(0, len(HERRAMIENTAS), 2):
        cols = st.columns(2, gap="medium")
        for col, h in zip(cols, HERRAMIENTAS[i:i + 2]):
            with col, st.container(border=True):
                st.markdown(
                    f'<div class="tarjeta-titulo">{h["titulo"]}</div>'
                    f'<div class="tarjeta-texto">{h["descripcion"]}</div>',
                    unsafe_allow_html=True,
                )
                st.page_link(h["ruta"], label=f"Abrir {h['titulo']}", icon=h["icono"])
