"""
Almacén compartido en un Gist de GitHub.

Cada herramienta guarda ahí archivos JSON planos (diccionarios de texto a
texto). Sirve para que lo que aprende la app en una sesión lo vean todas.

Se activa con dos Secrets: GIST_ID y GITHUB_TOKEN (token classic con el
permiso «gist»). Sin ellos, todo devuelve vacío y nada se rompe.
"""

import json
import time
import urllib.error
import urllib.request

import streamlit as st

from comun.ia import secreto


def _credenciales():
    gist, token = secreto("GIST_ID"), secreto("GITHUB_TOKEN")
    return (gist, token) if gist and token else (None, None)


def activo():
    return _credenciales()[0] is not None


def _peticion(url, token, datos=None, metodo="GET"):
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    p = urllib.request.Request(url, data=cuerpo, method=metodo)
    p.add_header("Authorization", f"Bearer {token}")
    p.add_header("Accept", "application/vnd.github+json")
    if cuerpo:
        p.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(p, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


@st.cache_data(ttl=300, show_spinner=False)
def lee(archivo):
    """El diccionario guardado en `archivo`, o {} si no hay Gist o falla.

    Sale a GitHub. Se relee cada 5 minutos, así que de vez en cuando una
    búsqueda paga este viaje sin que se note de dónde viene.
    """
    gist, token = _credenciales()
    if not gist:
        return {}
    try:
        datos = _peticion(f"https://api.github.com/gists/{gist}", token)
        contenido = datos["files"][archivo]["content"]
        return {str(k): str(v) for k, v in json.loads(contenido).items()}
    except Exception:  # noqa: BLE001
        return {}


def escribe(archivo, datos):
    """Sustituye el contenido de `archivo`. Lanza la excepción si falla."""
    gist, token = _credenciales()
    _peticion(
        f"https://api.github.com/gists/{gist}", token,
        datos={"files": {archivo: {
            "content": json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True)
        }}},
        metodo="PATCH",
    )
    lee.clear()


def prueba(archivo):
    """Escribe una marca, la relee y la borra. Devuelve (ok, mensaje)."""
    if not activo():
        return False, "No hay GIST_ID o GITHUB_TOKEN en los Secrets."

    marca = f"_prueba_{int(time.time())}"
    try:
        actual = dict(lee(archivo))
        antes = len(actual)
        actual[marca] = "comprobacion"
        escribe(archivo, actual)
    except urllib.error.HTTPError as e:
        pistas = {
            401: "el token no vale o está revocado",
            403: "al token le falta el permiso «gist»",
            404: "el GIST_ID no existe o no es tuyo",
        }
        return False, f"Al escribir: {e.code}, {pistas.get(e.code, 'error de GitHub')}."
    except Exception as e:  # noqa: BLE001
        return False, f"Al escribir: {type(e).__name__}: {e}"

    try:
        vuelta = lee(archivo)
    except Exception as e:  # noqa: BLE001
        return False, f"Al releer: {type(e).__name__}: {e}"

    if marca not in vuelta:
        return False, "Se escribió, pero al releer no aparece."

    del vuelta[marca]
    try:
        escribe(archivo, vuelta)
    except Exception:  # noqa: BLE001
        pass

    return True, f"Escritura y lectura correctas. {antes} términos guardados."
