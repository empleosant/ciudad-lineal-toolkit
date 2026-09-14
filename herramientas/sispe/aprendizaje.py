"""
Lo que el codificador aprende con el uso y comparte entre sesiones.

Dos diccionarios en el Gist común (ver `comun/gist.py`):

    lexico.json     jerga -> vocabulario oficial, traducida por la IA
    refuerzos.json  código -> palabras que deben empujarlo hacia arriba

Sin Gist configurado, todo devuelve vacío y el buscador va con el
vocabulario base.
"""

from comun import gist
from herramientas.sispe.motor import IDX

ARCHIVO_LEXICO = "lexico.json"
ARCHIVO_REFUERZOS = "refuerzos.json"


def lexico():
    return gist.lee(ARCHIVO_LEXICO)


def refuerzos():
    return gist.lee(ARCHIVO_REFUERZOS)


def guarda_termino(clave, valor):
    if not gist.activo():
        return False
    try:
        actual = dict(lexico())
        if actual.get(clave) == valor:
            return True
        actual[clave] = valor
        gist.escribe(ARCHIVO_LEXICO, actual)
        return True
    except Exception:  # noqa: BLE001
        return False


def guarda_refuerzo(codigo, palabras):
    if not gist.activo() or codigo not in IDX["por_codigo"]:
        return False
    nuevas = [w for w in palabras if len(w) > 2]
    if not nuevas:
        return False
    try:
        actual = dict(refuerzos())
        previas = actual.get(codigo, "").split()
        fusion = list(dict.fromkeys(previas + nuevas))[:24]
        if fusion == previas:
            return True
        actual[codigo] = " ".join(fusion)
        gist.escribe(ARCHIVO_REFUERZOS, actual)
        return True
    except Exception:  # noqa: BLE001
        return False


def prueba():
    """Comprueba que el Gist guarda y devuelve. (ok, mensaje)."""
    return gist.prueba(ARCHIVO_LEXICO)
