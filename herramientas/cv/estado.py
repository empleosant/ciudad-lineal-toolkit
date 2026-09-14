"""
El currículo en curso, guardado en la sesión de Streamlit.

Es el punto de unión con el codificador SISPE: su botón «+ CV» llama a
`anade_experiencia()` y el generador la encuentra al abrirse. Cualquier
otra herramienta que quiera aportar algo al currículo entra por aquí.

Claves de sesión: todas con prefijo `cv_`.
"""

import streamlit as st

from herramientas.cv import motor

PAGINA = "herramientas/cv/vista.py"   # para st.page_link desde otras herramientas


def inicia():
    st.session_state.setdefault("cv_datos", motor.nuevo())
    st.session_state.setdefault("cv_auto_orden", True)
    st.session_state.setdefault("cv_manuales", 0)


def cv():
    inicia()
    return st.session_state["cv_datos"]


def experiencias():
    return cv()["experiencias"]


def en_lista(codigo):
    return any(e["codigo"] == codigo for e in experiencias())


def anade_experiencia(codigo, denominacion, motivo=""):
    """Desde el codificador: una ocupación del catálogo pasa al currículo."""
    if en_lista(codigo):
        return
    experiencias().append(motor.experiencia(codigo, denominacion, motivo))


def anade_a_mano(**campos):
    """Una experiencia que no viene del codificador.

    No todo lo que se pone en un currículo hace falta codificarlo en SISPE, y
    hay quien llega con el itinerario ya contado. El código interno solo sirve
    para que cada ficha conserve sus datos al moverla.
    """
    n = st.session_state["cv_manuales"] = st.session_state.get("cv_manuales", 0) + 1
    ficha = motor.experiencia()
    ficha["codigo"] = f"mano-{n}"
    ficha.update({k: v for k, v in campos.items() if k in ficha})
    experiencias().append(ficha)
    return ficha


def vacia():
    st.session_state["cv_datos"] = motor.nuevo()
