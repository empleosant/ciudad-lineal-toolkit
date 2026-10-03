"""
Lo que hay «en la mesa»: lo que ya se sabe de la persona que se está atendiendo.

No guarda nada nuevo de la persona: lee lo que las herramientas ya tienen en
la sesión (la última ocupación del codificador, el currículo en curso) y le
suma una sola cosa propia, las empresas de la guía que se van marcando. Con
eso `comun/estilo.py` pinta la franja bajo la barra negra y la cesta del
menú, y cualquier herramienta sabe de qué ocupación y de qué sector se está
hablando sin volver a preguntarlo.

Aquí no hay nombre ni contacto: solo el código de ocupación, el sector y la
cuenta de experiencias. Todo vive en la sesión del navegador y se va al
cerrarla o al pulsar «Vaciar».

Claves de sesión propias: prefijo `mesa_`.
"""

import re

import streamlit as st

from comun import guia

EMPRESAS = "mesa_empresas"      # {clave de la ficha: ficha}, en el orden en que se marcan


# ---------------------------------------------------------------------------
# Lo que se lee de las herramientas
# ---------------------------------------------------------------------------

def experiencias():
    """Las experiencias del currículo en curso, sin crearlo si no existe."""
    return (st.session_state.get("cv_datos") or {}).get("experiencias", [])


def cesta():
    """Cuántos puestos lleva el currículo en curso: el número del menú."""
    return len(experiencias())


def ocupacion():
    """(código, denominación) de la que se está hablando, o None.

    La recomendada de la última búsqueda del codificador; si no hay búsqueda,
    la última experiencia del currículo que vino con código del catálogo.
    """
    actual = st.session_state.get("sispe_actual")
    if actual:
        payload = actual[1] or {}
        ocupaciones = [] if payload.get("aviso") else payload.get("ocupaciones", [])
        if ocupaciones and ocupaciones[0].get("codigo"):
            return ocupaciones[0]["codigo"], ocupaciones[0].get("denominacion", "")
    for e in reversed(experiencias()):
        if re.fullmatch(r"\d{8}", e.get("codigo") or ""):
            return e["codigo"], e.get("denominacion") or e.get("puesto") or ""
    return None


def codigos():
    """Los códigos de la mesa: la ocupación de la que se habla y las del currículo."""
    salida = []
    oc = ocupacion()
    if oc:
        salida.append(oc[0])
    for e in experiencias():
        codigo = e.get("codigo") or ""
        if re.fullmatch(r"\d{8}", codigo) and codigo not in salida:
            salida.append(codigo)
    return salida


def secciones(cee=False):
    """Los sectores de la guía para lo que hay en la mesa (sin los generales)."""
    return guia.secciones(codigos(), generales=False, cee=cee)


def sector():
    """«Hostelería › Hoteles»: el sector principal de la ocupación, o ''."""
    oc = ocupacion()
    destinos = guia.destinos(oc[0]) if oc else []
    if not destinos or destinos[0][0] not in guia.CAPITULOS:
        return ""
    capitulo, apartado = destinos[0]
    corto = guia.CAPITULOS[capitulo]["corto"]
    return f"{corto} › {apartado}" if apartado else corto


# ---------------------------------------------------------------------------
# Las empresas marcadas
# ---------------------------------------------------------------------------

def empresas():
    return list(st.session_state.setdefault(EMPRESAS, {}).values())


def marcada(f):
    return guia.clave(f) in st.session_state.get(EMPRESAS, {})


def marca(f, si=None):
    """Marca o desmarca una ficha; sin `si`, le da la vuelta."""
    elegidas = st.session_state.setdefault(EMPRESAS, {})
    k = guia.clave(f)
    if si is None:
        si = k not in elegidas
    if si:
        elegidas[k] = f
    else:
        elegidas.pop(k, None)


def casilla(f, clave, detalle=True):
    """Una casilla por ficha: nombre en negrita y, debajo, a qué se dedica.

    `clave` distingue las pintadas (la misma empresa puede salir en el panel
    del codificador y en la pestaña de la guía). El valor sale siempre de la
    mesa, así que las dos casillas van a una.
    """
    k = f"mesa_c_{clave}_{guia.clave(f)}"
    st.session_state[k] = marcada(f)
    texto = f"**{f['nombre']}**" + (f"  \n{f['que']}" if detalle and f.get("que") else "")
    st.checkbox(texto, key=k, on_change=_al_marcar, args=(f, k))


def _al_marcar(f, k):
    marca(f, bool(st.session_state.get(k)))


# ---------------------------------------------------------------------------
# La franja y el vaciado
# ---------------------------------------------------------------------------

def hay():
    return bool(ocupacion() or experiencias() or st.session_state.get(EMPRESAS))


def resumen():
    """[(rótulo, valor, código)] de lo que se pinta en la franja, en orden."""
    datos = []
    oc = ocupacion()
    if oc:
        nombre = oc[1].capitalize() if oc[1].isupper() else oc[1]
        datos.append(("", nombre, oc[0]))
        if sector():
            datos.append(("Sector", sector(), ""))
    n = cesta()
    if n:
        datos.append(("CV", f"{n} experiencia{'s' if n != 1 else ''}", ""))
    m = len(st.session_state.get(EMPRESAS, {}))
    if m:
        datos.append(("Empresas", f"{m} marcada{'s' if m != 1 else ''}", ""))
    return datos


def vacia():
    """Para la siguiente persona: fuera el currículo, la búsqueda y las empresas.

    Lo que cada herramienta guarda para sí (los ajustes, el catálogo de
    cursos subido, el registro de búsquedas del día) no se toca.
    """
    from herramientas.cv import estado as cv_estado
    cv_estado.vacia()
    for k in [k for k in st.session_state if k.startswith(("cv_w_", "mesa_"))]:
        del st.session_state[k]
    st.session_state["cv_paso"] = 0
    st.session_state["sispe_actual"] = None
    st.session_state["sispe_ultima"] = ""
    st.session_state["consulta"] = ""
