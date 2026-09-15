"""
Cliente de IA compartido por todas las herramientas.

Una sola configuración de proveedor (Gemini o cualquier API compatible con
OpenAI) y dos formas de llamar:

    genera(cli, sistema, entrada, ...)        una respuesta entera
    genera_flujo(cli, sistema, entrada, ...)  la respuesta a trozos (streaming)

Las dos aceptan `json=True` para pedir la salida en JSON y `pensar=True`
para dejar razonar al modelo (por defecto, lo mínimo: son tareas cortas).

    transcribe(cli, audio, mime)              audio grabado -> texto

Gemini transcribe con el mismo modelo de texto. En los proveedores
compatibles con OpenAI hace falta un modelo de transcripción aparte
(`transcripcion` en PROVEEDORES); si no lo hay, no se puede.

La lista de modelos es una cadena de relevo: si el primero agota la cuota,
el siguiente. Qué modelo está respondiendo se recuerda en la sesión
(`ia_modelo_ok`) para no volver a tropezar en la misma piedra, y el que
acaba contestando se apunta aparte (`ultimo_uso()`) para poder enseñarlo.

Usa Streamlit para los Secrets, la caché del cliente y la memoria de sesión.
"""

import os

import streamlit as st

try:
    from google import genai
    from google.genai import types
except ImportError:                     # noqa: S110
    genai = types = None

try:
    from openai import OpenAI
except ImportError:                     # noqa: S110
    OpenAI = None

ESPERA_MAXIMA = 30   # segundos por intento. A 45 una llamada atascada te dejaba
                     # mirando la pantalla; a 12 se cortaban llamadas que iban a
                     # terminar bien y caias al catalogo sin afinar.

PROVEEDOR = "gemini"

PROVEEDORES = {
    "gemini": {
        "clave": "GEMINI_API_KEY",
        "modelos": [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-3.6-flash",
        ],
    },
    "groq": {
        "clave": "GROQ_API_KEY",
        "modelos": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "url": "https://api.groq.com/openai/v1",
        "transcripcion": "whisper-large-v3-turbo",
    },
    "mistral": {
        "clave": "MISTRAL_API_KEY",
        "modelos": ["mistral-small-latest"],
        "url": "https://api.mistral.ai/v1",
    },
}

AJUSTES = PROVEEDORES[PROVEEDOR]
MODELOS = AJUSTES["modelos"]


def secreto(nombre):
    """Lee de los Secrets de Streamlit y, si no está, del entorno."""
    try:
        valor = st.secrets.get(nombre)
    except Exception:  # noqa: BLE001
        valor = None
    return valor or os.environ.get(nombre)


def modelo_actual():
    return MODELOS[min(st.session_state.get("ia_modelo_ok", 0), len(MODELOS) - 1)]


def apunta_uso(modelo):
    """Quien ha respondido de verdad, para poder enseñarlo en pantalla.

    Sin esto el relevo es invisible: el primer modelo de la cadena podria
    llevar una semana caido y la herramienta pareceria ir igual de bien."""
    st.session_state["ia_ultimo_proveedor"] = PROVEEDOR
    st.session_state["ia_ultimo_modelo"] = modelo


def ultimo_uso():
    """(proveedor, modelo) del ultimo que contesto, o ("", "") si nadie."""
    return (
        st.session_state.get("ia_ultimo_proveedor", ""),
        st.session_state.get("ia_ultimo_modelo", ""),
    )


def sin_cuota(e):
    t = str(e)
    return "429" in t or "RESOURCE_EXHAUSTED" in t or "quota" in t.lower()


@st.cache_resource(show_spinner=False)
def cliente():
    """El cliente del proveedor, o None si no hay clave o falta la librería."""
    clave = secreto(AJUSTES["clave"])
    if not clave:
        return None
    if PROVEEDOR == "gemini":
        if not genai:
            return None
        try:
            return genai.Client(
                api_key=clave,
                http_options=types.HttpOptions(timeout=ESPERA_MAXIMA * 1000),
            )
        except Exception:  # noqa: BLE001
            return genai.Client(api_key=clave)
    if not OpenAI:
        return None
    return OpenAI(api_key=clave, base_url=AJUSTES["url"], timeout=ESPERA_MAXIMA)


def _config_gemini(sistema, max_tokens, json, nivel):
    cfg = dict(max_output_tokens=max_tokens)
    if sistema:
        cfg["system_instruction"] = sistema
    if json:
        cfg["response_mime_type"] = "application/json"
    if nivel:
        try:
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level=nivel)
        except Exception:  # noqa: BLE001
            pass
    return cfg


def genera(cli, sistema, entrada, max_tokens=2048, json=False, pensar=False):
    """Una llamada, una respuesta en texto. Lanza la excepción si falla."""
    m = modelo_actual()
    if PROVEEDOR == "gemini":
        cfg = _config_gemini(sistema, max_tokens, json, None if pensar else "minimal")
        r = cli.models.generate_content(
            model=m, contents=entrada,
            config=types.GenerateContentConfig(**cfg),
        )
        apunta_uso(m)
        return (getattr(r, "text", "") or "").strip()

    extra = {"response_format": {"type": "json_object"}} if json else {}
    r = cli.chat.completions.create(
        model=m,
        messages=[{"role": "system", "content": sistema}, {"role": "user", "content": entrada}],
        max_tokens=max_tokens, temperature=0, **extra,
    )
    apunta_uso(m)
    return (r.choices[0].message.content or "").strip()


def _flujo_gemini(cli, sistema, entrada, max_tokens, json):
    # Cascada: primero el modelo y la configuración que funcionaron la última
    # vez; si fallan antes de emitir nada, se prueba la siguiente. Si ya había
    # emitido, el error se propaga tal cual: reintentar duplicaría la salida.
    opciones = [
        _config_gemini(sistema, max_tokens, json, nivel)
        for nivel in ("minimal", "low", None)
    ]
    ultimo = None
    for m in range(st.session_state.get("ia_modelo_ok", 0), len(MODELOS)):
        for i in range(st.session_state.get("ia_cfg", 0), len(opciones)):
            emitido = False
            try:
                flujo = cli.models.generate_content_stream(
                    model=MODELOS[m], contents=entrada,
                    config=types.GenerateContentConfig(**opciones[i]),
                )
                for trozo in flujo:
                    if not emitido:
                        st.session_state["ia_modelo_ok"] = m
                        st.session_state["ia_cfg"] = i
                        apunta_uso(MODELOS[m])
                        emitido = True
                    if getattr(trozo, "text", None):
                        yield trozo.text
                return
            except Exception as e:  # noqa: BLE001
                if emitido:
                    raise
                ultimo = e
                if sin_cuota(e):
                    break
    raise ultimo


def _flujo_openai(cli, sistema, entrada, max_tokens, json):
    extra = {"response_format": {"type": "json_object"}} if json else {}
    m = modelo_actual()
    flujo = cli.chat.completions.create(
        model=m,
        messages=[{"role": "system", "content": sistema}, {"role": "user", "content": entrada}],
        max_tokens=max_tokens, temperature=0, stream=True, **extra,
    )
    emitido = False
    for trozo in flujo:
        if not trozo.choices:
            continue
        texto = trozo.choices[0].delta.content
        if texto:
            if not emitido:
                apunta_uso(m)
                emitido = True
            yield texto


def genera_flujo(cli, sistema, entrada, max_tokens=2048, json=False):
    """La respuesta a trozos, para pintar el avance mientras llega."""
    if PROVEEDOR == "gemini":
        yield from _flujo_gemini(cli, sistema, entrada, max_tokens, json)
    else:
        yield from _flujo_openai(cli, sistema, entrada, max_tokens, json)


TRANSCRIPCION = (
    "Transcribe literalmente, en español, lo que se dice en el audio. "
    "Devuelve solo el texto transcrito, sin comentarios ni etiquetas. "
    "Si no se entiende nada, devuelve una cadena vacía."
)


def transcribe(cli, audio, mime="audio/wav"):
    """El texto de una grabación. Lanza la excepción si falla."""
    if PROVEEDOR == "gemini":
        r = cli.models.generate_content(
            model=modelo_actual(),
            contents=[types.Part.from_bytes(data=audio, mime_type=mime), TRANSCRIPCION],
            config=types.GenerateContentConfig(**_config_gemini(None, 2048, False, "minimal")),
        )
        return (getattr(r, "text", "") or "").strip()
    modelo = AJUSTES.get("transcripcion")
    if not modelo:
        raise RuntimeError(f"El proveedor {PROVEEDOR} no tiene modelo de transcripción.")
    r = cli.audio.transcriptions.create(
        model=modelo, file=("grabacion.wav", audio, mime), language="es",
    )
    return (getattr(r, "text", "") or "").strip()


def prueba():
    """Para el panel de mantenimiento: (ok, mensaje)."""
    cli = cliente()
    if cli is None:
        return False, f"No hay clave {AJUSTES['clave']} en los Secrets."
    try:
        r = genera(cli, "Responde únicamente con la palabra ok.", "ok", max_tokens=16)
        return True, f"{modelo_actual()}: {r[:60]}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"
