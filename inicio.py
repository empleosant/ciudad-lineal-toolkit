"""
Portada de la caja de herramientas.

Una tarjeta por herramienta, a partir de `comun/registro.py`. Aquí no hay
lógica: solo presentación.
"""

import streamlit as st

from comun import estilo
from comun.registro import HERRAMIENTAS

estilo.aplica()

estilo.banda(
    "inicio", "Herramientas de orientación",
    "Pequeñas utilidades para el día a día de la oficina, que se pasan datos entre sí.",
)

st.markdown('<div class="seccion">Herramientas</div>', unsafe_allow_html=True)
cols = st.columns(3, gap="medium")
for i, h in enumerate(HERRAMIENTAS):
    with cols[i % 3]:
        st.markdown(
            f'<div class="via grande"><div class="t">{h["titulo"]}</div>'
            f'<div class="d">{h["descripcion"]}</div></div>',
            unsafe_allow_html=True,
        )
        st.page_link(h["ruta"], label=f"Abrir {h['titulo']}", icon=h["icono"])

st.markdown('<div class="seccion">Cómo se conectan</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2, gap="medium")
c1.markdown(
    '<div class="estado-doc"><div class="l">Codificador → Generador de CV</div>'
    '<div class="n">Busca la ocupación, pulsa «+ CV» y la experiencia aparece en el generador '
    'con el nombre del puesto ya preparado.</div></div>', unsafe_allow_html=True,
)
c2.markdown(
    '<div class="estado-doc"><div class="l">Generador de CV → Asesor de formación</div>'
    '<div class="n">El asesor puede tomar el perfil del currículo en curso, sin el nombre ni '
    'el contacto, para proponer cursos.</div></div>', unsafe_allow_html=True,
)
