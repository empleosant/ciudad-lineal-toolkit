"""
Cliente de IA compartido por todas las herramientas, con cascada de proveedores.

Dos formas de llamar:

    genera(cli, sistema, entrada, ...)        una respuesta entera
    genera_flujo(cli, sistema, entrada, ...)  la respuesta a trozos (streaming)
    transcribe(cli, audio, mime)              audio grabado -> texto

Las dos primeras aceptan `json=True` para pedir la salida en JSON y
`pensar=True` para dejar razonar al modelo (por defecto, lo mínimo: son tareas
cortas). `genera` acepta además `plazo` y `respaldo`, que es lo que activa
`comun/plazos.py`: cortar una llamada colgada y lanzarle un respaldo. Solo lo
pide el codificador, que hace llamadas de un segundo; las herramientas que
redactan tardan mucho más y esperan sin plazo.

DOS CADENAS, NO UNA. `perfil=RAPIDO` (lo de fábrica) usa `modelos`, que empieza
por los Flash-Lite: cientos de consultas al día y respuesta en un segundo, que
es lo que necesita el codificador. `perfil=CALIDAD` usa `modelos_calidad`, que
empieza por los modelos completos: mucho menos cupo diario, pero un informe son
tres llamadas y ahí lo que se nota es cómo escribe. Cuando el bueno se queda
sin cupo, la misma cadena sigue por los rápidos y el informe sale igual. Los
castigos de una cadena no tocan a la otra.

LA CASCADA. `ORDEN` son los proveedores a intentar, de izquierda a derecha,
saltando los que no tengan clave. Dentro de cada uno, sus modelos son otra
cadena de relevo. Un proveedor que devuelve «cupo del día agotado» se aparta
una hora (`quemados`); un modelo que tropieza se degrada cinco minutos
(`degradados`). Las dos cosas caducan a propósito: sin caducidad, un 429 de
las siete de la mañana dejaba la sesión entera en el peor modelo.

Quién ha contestado de verdad se apunta en `ultimo_uso()`, porque si no el
relevo es invisible: el primer proveedor podría llevar una semana caído y la
herramienta parecería ir igual de bien.

Usa Streamlit para los Secrets, la caché del cliente y la memoria de sesión.
Lo que no lo necesita -los plazos y el respaldo- vive en `comun/plazos.py`,
que es Python puro y sí se puede probar.
"""

import os
import time

import streamlit as st

from comun.plazos import con_plazo  # noqa: F401  lo usan las herramientas

try:
    from google import genai
    from google.genai import types
except ImportError:                     # noqa: S110
    genai = types = None

try:
    from openai import OpenAI
except ImportError:                     # noqa: S110
    OpenAI = None

ESPERA_MAXIMA = 30   # segundos que aguanta el TRANSPORTE sin recibir datos.
                     #
                     # No es el tope de un intento, aunque lo parezca: es lo
                     # que acaba en el cliente HTTP, y ese plazo mide el tiempo
                     # SIN RECIBIR DATOS, no lo que dura la respuesta. El tope
                     # de verdad lo pone `plazos.PLAZO_INTENTO`, con reloj
                     # propio. Esto se queda como segunda línea, para la
                     # conexión que se queda muda del todo.
                     #
                     # No bajarlo de 10: el SDK de Google manda este plazo al
                     # servidor como X-Server-Timeout y Google rechaza con 400
                     # cualquier valor menor («Minimum allowed deadline is
                     # 10s»), con lo que TODAS las llamadas a Gemini fallarían
                     # en medio segundo.

PROVEEDOR = "gemini"   # el de fábrica. El panel de mantenimiento puede fijar
                       # otro solo para esa sesión; al recargar vuelve a este.

PROVEEDORES = {
    "gemini": {
        # El cupo diario del plan gratuito es POR MODELO y se renueva a
        # medianoche del PACÍFICO, no a medianoche de aquí: en España son las
        # 09:00 en invierno y las 10:00 en verano.
        #
        # Los Flash-Lite van delante y no por capricho: los Flash completos
        # tienen 20 peticiones al DÍA en el tramo gratuito -no llegan ni a
        # media mañana- y los Lite dan 500 al día y 15 por minuto cada uno.
        # Como el cupo es por modelo, encadenarlos son ~1.500 diarias.
        "clave": "GEMINI_API_KEY",
        "modelos": [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-3.6-flash",
        ],
        # Para redactar, al revés: los Flash completos delante. Su cupo diario
        # es mucho más corto -por eso NO valen para el codificador, que hace
        # cientos de consultas- pero un informe son tres llamadas y aquí lo
        # que se nota es la calidad de la redacción, no el segundo de espera.
        # Cuando se agote el cupo, la cadena sigue por los Lite de siempre: el
        # informe sale igual, solo que peor escrito.
        "modelos_calidad": [
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-2.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
        ],
    },
    "mistral": {
        # Los topes del plan gratuito son POR MODELO, no por cuenta. Ministral
        # 3B aguanta gran volumen y latencia baja; small y large van detrás.
        "clave": "MISTRAL_API_KEY",
        "modelos": [
            "ministral-3b-latest",
            "ministral-8b-latest",
            "mistral-small-latest",
            "mistral-large-latest",
        ],
        "modelos_calidad": [
            "mistral-large-latest",
            "mistral-small-latest",
            "ministral-8b-latest",
        ],
        "url": "https://api.mistral.ai/v1",
    },
    "groq": {
        # El único con modelo de transcripción propio: es el que sostiene el
        # dictado del generador de CV y el de los informes cuando Gemini no
        # está. Ver `transcribe`.
        # Sin `modelos_calidad` a propósito: aquí no hay clave con la que
        # comprobar qué modelos grandes tiene hoy (Kimi K2, GPT-OSS 120B y
        # compañía). Si algún día se pone GROQ_API_KEY, es el sitio donde
        # ponerlos, y «Probar TODOS los modelos» dirá si los nombres valen.
        "clave": "GROQ_API_KEY",
        "modelos": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "url": "https://api.groq.com/openai/v1",
        "transcripcion": "whisper-large-v3-turbo",
    },
    "openrouter": {
        # Último escalón, probablemente sin clave: mientras no haya
        # OPENROUTER_API_KEY en los Secrets, la cascada lo salta sin ruido.
        # «openrouter/free» es su enrutador automático, que elige el modelo
        # gratuito disponible en ese momento; fijar uno concreto es garantizar
        # que un día desaparezca. Sin comprar créditos son 50 peticiones al
        # día: da para tapar un hueco, no para sostener una jornada.
        "clave": "OPENROUTER_API_KEY",
        "modelos": ["openrouter/free"],
        "url": "https://openrouter.ai/api/v1",
    },
}

# ORDEN de la cascada. Se recorre de izquierda a derecha y se salta lo que no
# tenga clave. Si al medir resulta que otro responde mejor, se cambia AQUÍ y no
# hay que tocar nada más.
ORDEN = ["gemini", "mistral", "groq", "openrouter"]

CASCADA = "cascada"   # el selector de mantenimiento usa este valor para decir
                      # «recorre el orden»; cualquier otro fija un proveedor.

# Los dos perfiles. No es un ajuste que se toque: lo pide cada herramienta
# según lo que hace. El codificador contesta cientos de veces al día y quiere
# el modelo rápido; los informes y el asesor de formación redactan tres o
# cuatro veces al día y quieren el que escribe mejor.
RAPIDO = "rapido"
CALIDAD = "calidad"

CADUCIDAD_CASTIGO = 3600   # segundos que dura APARTAR UN PROVEEDOR. Solo se
                           # aparta por cupo del día agotado, y un cupo diario
                           # no vuelve en cinco minutos.

CADUCIDAD_DEGRADACION = 300   # segundos que dura BAJAR DE MODELO dentro de un
                              # proveedor. Mucho menos, y por una razón: casi
                              # todos los tropiezos son 5xx que pasan solos.
                              # Reintentar el modelo bueno cuesta un intento
                              # perdido cada cinco minutos; no reintentarlo
                              # costaba una hora en el peor modelo por dos
                              # décimas de mala suerte.

LIMITES_CASTIGO = {"ia_modelo_desde": CADUCIDAD_DEGRADACION}


def secreto(nombre):
    """Lee de los Secrets de Streamlit y, si no está, del entorno."""
    try:
        valor = st.secrets.get(nombre)
    except Exception:  # noqa: BLE001  sin archivo de secrets, st.secrets revienta
        valor = None
    return valor or os.environ.get(nombre)


def tiene_clave(prov):
    return bool(secreto(PROVEEDORES[prov]["clave"]))


def claves_aceptadas():
    """Las claves que valdrían, en orden de cascada. Para los avisos."""
    return [PROVEEDORES[p]["clave"] for p in ORDEN]


def aviso_sin_clave():
    """La frase que se enseña cuando no hay ninguna clave puesta."""
    return ("No hay ninguna clave de IA en los Secrets (vale cualquiera de "
            + ", ".join(claves_aceptadas()) + ").")


# ---------------------------------------------------------------------------
# Castigos: apartar un proveedor, degradar un modelo. Los dos caducan.
# ---------------------------------------------------------------------------

def _castigo_vivo(registro, prov):
    """¿Sigue en pie el castigo de ESE proveedor, o ya ha caducado?

    Apartar a un proveedor sin fecha era una condena perpetua. El cupo se
    renueva -el diario a medianoche, el de por minuto en sesenta segundos-
    pero la sesión no se entera de que ha pasado el día: una pestaña abierta
    desde ayer seguiría dando al mejor proveedor por muerto para siempre.
    """
    marca = st.session_state.get(registro, {}).get(prov)
    if marca is None:
        return False
    limite = LIMITES_CASTIGO.get(registro, CADUCIDAD_CASTIGO)
    if time.time() - marca > limite:
        st.session_state[registro].pop(prov, None)
        return False
    return True


def quemados():
    """Los apartados que TODAVÍA lo están, ya purgados los que han caducado."""
    return {p for p in list(st.session_state.get("ia_agotados", {}))
            if _castigo_vivo("ia_agotados", p)}


def degradados():
    """Proveedor -> modelo de respaldo en el que sigue clavado ahora mismo.

    La degradación dentro de un proveedor es tan invisible como el apartado y
    engaña más: el nombre del proveedor sigue siendo el bueno y lo único que
    cambia es el modelo, que nadie mira.
    """
    fuera = {}
    for clave in list(st.session_state.get("ia_modelo_ok", {})):
        prov, _, perfil = clave.partition(":")
        perfil = perfil or RAPIDO
        if prov not in PROVEEDORES:
            continue
        i = _idx_modelo(prov, perfil)   # purga de paso lo que haya caducado
        if i:
            lista = modelos_de(prov, perfil) or PROVEEDORES[prov]["modelos"]
            fuera[clave] = lista[min(i, len(lista) - 1)]
    return fuera


def orden_proveedores():
    """Proveedores a intentar, en orden, para esta llamada.

    Un proveedor fijado a mano en mantenimiento apaga la cascada: si el relevo
    siguiera activo, una prueba comparativa podría acabar respondida por otro
    y estaríamos midiendo algo distinto de lo que creemos.
    """
    elegido = st.session_state.get("ia_proveedor", CASCADA)
    if elegido in PROVEEDORES:
        return [elegido]
    vivos = [p for p in ORDEN if tiene_clave(p)]
    apartados = quemados()
    # Si están todos quemados se vuelve a intentar con todos: más vale una
    # llamada perdida que dejar la sesión sin IA por un error mal leído.
    return [p for p in vivos if p not in apartados] or vivos


def proveedor_actual():
    orden = orden_proveedores()
    return orden[0] if orden else PROVEEDOR


def ajustes_actual():
    return PROVEEDORES[proveedor_actual()]


def modelos_de(prov, perfil=RAPIDO):
    """Modelos a recorrer en la cadena de relevo de ESE proveedor, para ESE uso.

    Con `perfil=CALIDAD` se usa `modelos_calidad` si el proveedor la tiene, que
    es la misma cadena puesta al revés: primero el que escribe mejor, y los
    rápidos detrás para cuando el bueno se quede sin cupo.

    Si en mantenimiento se ha fijado uno a mano, la cadena se queda en ese y
    solo en ese, por el mismo motivo que la cascada se apaga al fijar proveedor.
    """
    lista = PROVEEDORES[prov]["modelos"]
    if perfil == CALIDAD:
        lista = PROVEEDORES[prov].get("modelos_calidad") or lista
    todos = [m for m in lista
             if m not in st.session_state.get("ia_inexistentes", {}).get(prov, [])]
    fijo = st.session_state.get("ia_modelo_fijo")
    return [fijo] if fijo in todos else todos


def _clave_cadena(prov, perfil):
    """Los castigos de una cadena no valen para la otra.

    El índice y la degradación se guardan por proveedor Y perfil: si el modelo
    bueno de los informes se queda sin cupo, eso no puede degradar la cadena
    del codificador, que usa otros modelos distintos.
    """
    return prov if perfil == RAPIDO else f"{prov}:{perfil}"


def _idx_modelo(prov, perfil=RAPIDO):
    """El índice de la cadena de relevo es POR proveedor.

    Compartir un solo número entre todos hacía que, tras degradar en uno, la
    cascada entrase en el siguiente apuntando a un modelo que quizá ni existe
    en su lista.
    """
    clave = _clave_cadena(prov, perfil)
    if not _castigo_vivo("ia_modelo_desde", clave):
        st.session_state.setdefault("ia_modelo_ok", {}).pop(clave, None)
        return 0
    return st.session_state.setdefault("ia_modelo_ok", {}).get(clave, 0)


def _fija_modelo(prov, modelo, perfil=RAPIDO):
    """Recuerda por qué modelo empezar la próxima vez, por NOMBRE.

    Se guarda su posición, pero se calcula aquí sobre la cadena viva. Cuando
    se guardaba la posición que traía el bucle, sacar un modelo de la cadena
    -porque resulta que no existe- movía a todos los de detrás y el número
    apuntaba de pronto a otro: el modelo que acababa de responder bien
    aparecía como degradado sin haber fallado.
    """
    vivos = modelos_de(prov, perfil)
    i = vivos.index(modelo) if modelo in vivos else 0
    clave = _clave_cadena(prov, perfil)
    st.session_state.setdefault("ia_modelo_ok", {})[clave] = i
    desde = st.session_state.setdefault("ia_modelo_desde", {})
    if i:
        # setdefault, no asignación: la hora es la de la PRIMERA degradación.
        # Refrescarla en cada llamada sería no caducar nunca.
        desde.setdefault(clave, time.time())
    else:
        # El primero de la cadena no es una degradación: nada que caducar.
        desde.pop(clave, None)


def apunta_uso(prov, modelo):
    """Quién ha respondido de verdad, para poder enseñarlo en pantalla."""
    st.session_state["ia_ultimo_proveedor"] = prov
    st.session_state["ia_ultimo_modelo"] = modelo
    conteo = st.session_state.setdefault("ia_uso_proveedor", {})
    conteo[prov] = conteo.get(prov, 0) + 1


def ultimo_uso():
    """(proveedor, modelo) del último que contestó, o ("", "") si nadie."""
    return (
        st.session_state.get("ia_ultimo_proveedor", ""),
        st.session_state.get("ia_ultimo_modelo", ""),
    )


def sin_cuota(e):
    t = str(e)
    return "429" in t or "RESOURCE_EXHAUSTED" in t or "quota" in t.lower()


def por_minuto(e):
    """Distingue el tope POR MINUTO del cupo diario agotado.

    Los dos llegan como 429 y con el mismo texto de «exceeded your quota», pero
    no son lo mismo: el de por minuto se pasa solo en unos segundos. Tratarlo
    como cupo agotado apartaba al proveedor una hora por un tropiezo de
    sesenta segundos.
    """
    t = str(e).lower()
    if not sin_cuota(e):
        return False
    if "per day" in t or "requests per day" in t or "perday" in t:
        return False
    return True


def no_existe(e):
    """¿El error dice que ESE MODELO no existe?

    Es un error distinto de todos los demás y hay que tratarlo distinto. Un
    5xx pasa solo y merece que se reintente en cinco minutos; un nombre de
    modelo que el proveedor no reconoce no va a existir por esperar, y
    reintentarlo cada cinco minutos es pagar un intento perdido por consulta
    para siempre, sin que nadie se entere.

    Pasa de verdad y más de lo que parece: los proveedores cierran modelos
    antes de la fecha que anuncian y los catálogos gratuitos rotan. A `main`
    le dejó la rama entera de Gemini caída -tres modelos devolviendo 404
    NOT_FOUND- y todo se resolvía con el proveedor de respaldo sin avisar.
    """
    t = str(e).lower()
    if "404" not in t and "not_found" not in t and "not found" not in t:
        return False
    return ("model" in t or "modelo" in t) or "not_found" in t


def muertos():
    """Proveedor -> modelos que esta sesión ya sabe que no existen."""
    return {p: list(ms) for p, ms in st.session_state.get("ia_inexistentes", {}).items() if ms}


def _mata_modelo(prov, modelo):
    """Saca un modelo de la cadena para el resto de la sesión.

    No caduca, a diferencia de la degradación: si el proveedor dice que no lo
    conoce, no lo va a conocer dentro de cinco minutos. Al recargar la página
    se vuelve a intentar, que es lo que hay que hacer cuando se cambia la
    lista de modelos o el proveedor publica uno nuevo.
    """
    st.session_state.setdefault("ia_inexistentes", {}).setdefault(prov, []).append(modelo)
    # El índice de la cadena apuntaba a la lista de antes: se reinicia para
    # que la próxima llamada arranque por el primero de los que siguen vivos.
    # Las dos cadenas del proveedor, porque un modelo que no existe no existe
    # tampoco para la otra.
    for clave in (_clave_cadena(prov, RAPIDO), _clave_cadena(prov, CALIDAD)):
        st.session_state.setdefault("ia_modelo_ok", {}).pop(clave, None)
        st.session_state.setdefault("ia_modelo_desde", {}).pop(clave, None)


def _quema(prov, e):
    """Aparta un proveedor, solo si el error dice expresamente que es el cupo
    del DÍA. Ante la duda no se quema."""
    if sin_cuota(e) and not por_minuto(e):
        st.session_state.setdefault("ia_agotados", {}).setdefault(prov, time.time())


def modelo_actual(perfil=RAPIDO):
    prov = proveedor_actual()
    m = modelos_de(prov, perfil) or PROVEEDORES[prov]["modelos"]
    return m[min(_idx_modelo(prov, perfil), len(m) - 1)]


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _cliente(proveedor):
    """El proveedor va como argumento para que forme parte de la clave de caché.

    Sin él, Streamlit guardaba UN solo cliente: la cascada cambiaba de
    proveedor y seguía respondiendo el anterior.
    """
    ajustes = PROVEEDORES[proveedor]
    clave = secreto(ajustes["clave"])
    if not clave:
        return None
    if proveedor == "gemini":
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
    return OpenAI(api_key=clave, base_url=ajustes["url"], timeout=ESPERA_MAXIMA)


def cliente():
    """El cliente del primer proveedor vivo, o None si no hay ninguna clave.

    Las vistas lo piden una vez y se lo pasan a su `modelo.py`; los relevos de
    la cascada abren el suyo por su cuenta.
    """
    return _cliente(proveedor_actual())


def _cliente_para(prov, cli, primero):
    """El cliente del primer proveedor ya viene dado por la vista; el resto se
    abren aquí (la caché de Streamlit hace que salga gratis a partir de la
    segunda vez)."""
    if cli is not None and prov == primero:
        return cli
    return _cliente(prov)


# ---------------------------------------------------------------------------
# Las llamadas
# ---------------------------------------------------------------------------

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


def _una_llamada(prov, cli, modelo, sistema, entrada, max_tokens, json, pensar):
    """Un intento contra UN modelo de UN proveedor. Devuelve el texto o lanza.

    No toca la sesión: puede correr dentro del hilo de `con_plazo`, y
    session_state no es para hilos secundarios. Apuntar el uso y fijar el
    modelo se hacen fuera, en `genera`.
    """
    if prov == "gemini":
        cfg = _config_gemini(sistema, max_tokens, json, None if pensar else "minimal")
        r = cli.models.generate_content(
            model=modelo, contents=entrada,
            config=types.GenerateContentConfig(**cfg),
        )
        return (getattr(r, "text", "") or "").strip()

    extra = {"response_format": {"type": "json_object"}} if json else {}
    r = cli.chat.completions.create(
        model=modelo,
        messages=[{"role": "system", "content": sistema}, {"role": "user", "content": entrada}],
        max_tokens=max_tokens, temperature=0, **extra,
    )
    return (r.choices[0].message.content or "").strip()


def genera(cli, sistema, entrada, max_tokens=2048, json=False, pensar=False,
           plazo=None, respaldo=None, al_relevar=None, perfil=RAPIDO):
    """Una respuesta entera, recorriendo la cascada. Lanza la última excepción
    si no contesta nadie.

    `plazo` y `respaldo` son segundos y se los queda `plazos.con_plazo`: cortan
    el intento y le lanzan una segunda petición. Sin ellos se espera lo que
    haga falta, que es lo que necesitan las herramientas que redactan.

    `al_relevar(texto)` recibe una línea por cada intento fallido, para poder
    enseñar después por qué la respuesta tardó lo que tardó.

    `perfil=CALIDAD` cambia la cadena de modelos por la de redactar: primero el
    que escribe mejor, aunque tenga menos cupo. Lo piden las herramientas que
    redactan, no el codificador.
    """
    orden = orden_proveedores()
    primero = orden[0] if orden else None
    ultimo = None
    for prov in orden:
        cliente_prov = _cliente_para(prov, cli, primero)
        if cliente_prov is None:
            continue
        modelos = modelos_de(prov, perfil)
        if not modelos:
            continue         # todos sus modelos han resultado no existir
        # El índice se acota a la lista: si se ha fijado un modelo a mano, la
        # cadena se queda en uno y un índice viejo dejaría el `range` vacío,
        # que es saltarse al proveedor sin intentarlo siquiera.
        for modelo in modelos[min(_idx_modelo(prov, perfil), len(modelos) - 1):]:
            arranque = time.perf_counter()
            try:
                hacer = lambda: _una_llamada(      # noqa: E731
                    prov, cliente_prov, modelo, sistema, entrada,
                    max_tokens, json, pensar,
                )
                if plazo:
                    anota = None
                    if al_relevar:
                        anota = lambda s: al_relevar(f"{modelo}:{s:.1f}s:Respaldo")  # noqa: E731
                    texto = con_plazo(hacer, plazo, respaldo=respaldo, al_respaldar=anota)
                else:
                    texto = hacer()
            except Exception as e:  # noqa: BLE001
                if al_relevar:
                    al_relevar(f"{prov}/{modelo}:{time.perf_counter() - arranque:.1f}s:"
                               f"{type(e).__name__}")
                ultimo = e
                if no_existe(e):
                    # No es un tropiezo: ese nombre de modelo no existe. Fuera
                    # de la cadena hasta que se recargue la página.
                    _mata_modelo(prov, modelo)
                    continue
                _quema(prov, e)
                if prov in quemados():
                    break            # cupo del día: no hay más que rascar aquí
                continue             # otro tropiezo: al siguiente modelo
            _fija_modelo(prov, modelo, perfil)
            apunta_uso(prov, modelo)
            return texto
    if ultimo:
        raise ultimo
    raise RuntimeError(aviso_sin_clave())


def _flujo_gemini(cli, modelo, sistema, entrada, max_tokens, json, arranque_cfg):
    """Los trozos de UN modelo de Gemini, probando las configuraciones de
    razonamiento de menos a más. Devuelve también con qué configuración fue."""
    opciones = [
        _config_gemini(sistema, max_tokens, json, nivel)
        for nivel in ("minimal", "low", None)
    ]
    ultimo = None
    for i in range(min(arranque_cfg, len(opciones) - 1), len(opciones)):
        emitido = False
        try:
            flujo = cli.models.generate_content_stream(
                model=modelo, contents=entrada,
                config=types.GenerateContentConfig(**opciones[i]),
            )
            for trozo in flujo:
                if not emitido:
                    yield ("cfg", i)
                    emitido = True
                if getattr(trozo, "text", None):
                    yield ("texto", trozo.text)
            return
        except Exception as e:  # noqa: BLE001
            # Si ya había emitido, el error se propaga: reintentar duplicaría
            # lo que la persona ya está leyendo en pantalla.
            if emitido:
                raise
            ultimo = e
            if sin_cuota(e):
                break
    raise ultimo


def _flujo_openai(cli, modelo, sistema, entrada, max_tokens, json):
    extra = {"response_format": {"type": "json_object"}} if json else {}
    flujo = cli.chat.completions.create(
        model=modelo,
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
                yield ("cfg", 0)
                emitido = True
            yield ("texto", texto)


def genera_flujo(cli, sistema, entrada, max_tokens=2048, json=False, al_relevar=None,
                 perfil=RAPIDO):
    """La respuesta a trozos, para pintar el avance mientras llega.

    Recorre la misma cascada que `genera`, con una diferencia: en cuanto se ha
    emitido el primer trozo ya no hay relevo posible, porque reintentar
    duplicaría la salida. Ese error se propaga.
    """
    orden = orden_proveedores()
    primero = orden[0] if orden else None
    ultimo = None
    for prov in orden:
        cliente_prov = _cliente_para(prov, cli, primero)
        if cliente_prov is None:
            continue
        modelos = modelos_de(prov, perfil)
        if not modelos:
            continue
        for modelo in modelos[min(_idx_modelo(prov, perfil), len(modelos) - 1):]:
            arranque = time.perf_counter()
            emitido = False
            try:
                if prov == "gemini":
                    trozos = _flujo_gemini(
                        cliente_prov, modelo, sistema, entrada, max_tokens, json,
                        st.session_state.get("ia_cfg", 0),
                    )
                else:
                    trozos = _flujo_openai(
                        cliente_prov, modelo, sistema, entrada, max_tokens, json)
                for que, valor in trozos:
                    if que == "cfg":
                        st.session_state["ia_cfg"] = valor
                        _fija_modelo(prov, modelo, perfil)
                        apunta_uso(prov, modelo)
                        emitido = True
                        continue
                    yield valor
                return
            except Exception as e:  # noqa: BLE001
                if emitido:
                    raise
                if al_relevar:
                    al_relevar(f"{prov}/{modelo}:{time.perf_counter() - arranque:.1f}s:"
                               f"{type(e).__name__}")
                ultimo = e
                if no_existe(e):
                    _mata_modelo(prov, modelo)
                    continue
                _quema(prov, e)
                if prov in quemados():
                    break
                continue
    if ultimo:
        raise ultimo
    raise RuntimeError(aviso_sin_clave())


TRANSCRIPCION = (
    "Transcribe literalmente, en español, lo que se dice en el audio. "
    "Devuelve solo el texto transcrito, sin comentarios ni etiquetas. "
    "Si no se entiende nada, devuelve una cadena vacía."
)


def transcribe(cli, audio, mime="audio/wav"):
    """El texto de una grabación, recorriendo los proveedores que saben.

    Gemini transcribe con el mismo modelo de texto. En los compatibles con
    OpenAI hace falta un modelo de transcripción aparte (`transcripcion` en
    PROVEEDORES): el que no lo tenga se salta, aunque tenga clave.
    """
    orden = orden_proveedores()
    primero = orden[0] if orden else None
    ultimo = None
    for prov in orden:
        if prov != "gemini" and not PROVEEDORES[prov].get("transcripcion"):
            continue
        cliente_prov = _cliente_para(prov, cli, primero)
        if cliente_prov is None:
            continue
        modelos = modelos_de(prov)
        if not modelos:
            continue
        modelo = modelos[min(_idx_modelo(prov), len(modelos) - 1)]
        try:
            if prov == "gemini":
                r = cliente_prov.models.generate_content(
                    model=modelo,
                    contents=[types.Part.from_bytes(data=audio, mime_type=mime),
                              TRANSCRIPCION],
                    config=types.GenerateContentConfig(
                        **_config_gemini(None, 2048, False, "minimal")),
                )
                texto = (getattr(r, "text", "") or "").strip()
            else:
                r = cliente_prov.audio.transcriptions.create(
                    model=PROVEEDORES[prov]["transcripcion"],
                    file=("grabacion.wav", audio, mime), language="es",
                )
                texto = (getattr(r, "text", "") or "").strip()
        except Exception as e:  # noqa: BLE001
            ultimo = e
            if no_existe(e):
                _mata_modelo(prov, modelo)
            else:
                _quema(prov, e)
            continue
        apunta_uso(prov, modelo)
        return texto
    if ultimo:
        raise ultimo
    raise RuntimeError("Ningún proveedor con clave sabe transcribir audio.")


def prueba(todos=False):
    """Para el panel de mantenimiento: (ok, mensaje), proveedor por proveedor.

    Con `todos`, recorre la CADENA ENTERA de cada proveedor en vez de solo el
    modelo que toca ahora. Es la única forma de comprobar desde fuera que los
    nombres de `PROVEEDORES` siguen existiendo cuando no se tienen las claves
    a mano: aquí las pone el despliegue. Lo mismo que hace
    `scripts/comprobar_ia.py`, pero desde el navegador y sin catálogo: a base
    de llamar. Son 16 tokens por modelo, una decena de llamadas en total.

    Un modelo que resulte no existir sale de la cadena igual que si hubiera
    fallado en una consulta de verdad, así que esta prueba además ARREGLA la
    sesión: deja de intentarlo.
    """
    con_clave = [p for p in ORDEN if tiene_clave(p)]
    if not con_clave:
        return False, aviso_sin_clave()

    lineas, alguno = [], False
    for prov in con_clave:
        cli = _cliente(prov)
        if cli is None:
            lineas.append(f"{prov}: falta la librería")
            continue
        cadena = modelos_de(prov)
        if not cadena:
            lineas.append(f"{prov}: ninguno de sus modelos existe")
            continue
        if todos:
            # Las dos listas enteras, no solo los que siguen vivos: la gracia
            # es descubrir cuáles ya no están. Sin repetir los que salen en las
            # dos, que son unos cuantos.
            aprobar = list(dict.fromkeys(
                PROVEEDORES[prov]["modelos"]
                + PROVEEDORES[prov].get("modelos_calidad", [])
            ))
        else:
            aprobar = [cadena[min(_idx_modelo(prov), len(cadena) - 1)]]
        for modelo in aprobar:
            try:
                r = _una_llamada(prov, cli, modelo, "Responde únicamente con la palabra ok.",
                                 "ok", 16, False, False)
                lineas.append(f"{prov} ({modelo}): {r[:40]}")
                alguno = True
            except Exception as e:  # noqa: BLE001
                if no_existe(e):
                    _mata_modelo(prov, modelo)
                    lineas.append(f"{prov} ({modelo}): NO EXISTE, hay que quitarlo de PROVEEDORES")
                else:
                    lineas.append(f"{prov} ({modelo}): {type(e).__name__}: {str(e)[:60]}")

    inexistentes = muertos()
    if inexistentes:
        lineas.append("MODELOS QUE NO EXISTEN (revisar PROVEEDORES): "
                      + "; ".join(f"{p}: {', '.join(ms)}" for p, ms in inexistentes.items()))
    apartados = quemados()
    if apartados:
        lineas.append("Apartados ahora mismo: " + ", ".join(sorted(apartados)))
    bajados = degradados()
    if bajados:
        lineas.append("Degradados: " + ", ".join(f"{p} -> {m}" for p, m in bajados.items()))
    return alguno, "\n\n".join(lineas)
