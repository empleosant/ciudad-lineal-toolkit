"""
Batería de la cascada de proveedores de IA.

`comun/ia.py` decide a quién se le pide cada respuesta y qué hacer cuando ese
alguien falla: relevar al modelo siguiente, apartar al proveedor que se ha
quedado sin cupo del día, volver a probar el bueno cuando el castigo caduca.
Es lo que sostiene la herramienta cuando Gemini se cae a media mañana, y hasta
hoy no lo comprobaba nadie.

No llama a la IA ni gasta cuota: se le ponen proveedores de mentira que
contestan, tardan o fallan a la orden. Las claves también son falsas, en el
entorno del proceso.

USO
    ~/.venvs/sispe/bin/python cascada.py

Necesita las dependencias instaladas (importa Streamlit por la vía de
`comun/ia.py`), como `informes.py` y a diferencia de las otras dos.
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Claves de mentira ANTES de importar: `tiene_clave` las lee del entorno.
for nombre in ("GEMINI_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY"):
    os.environ[nombre] = "de-mentira"
os.environ.pop("OPENROUTER_API_KEY", None)

import streamlit as st              # noqa: E402

from comun import ia                # noqa: E402

RESUMEN = []


def informe(nombre, fallos, total):
    pasa = not fallos
    RESUMEN.append((nombre, pasa))
    print(f"[{' OK ' if pasa else 'MAL'}] {nombre:44} {total - len(fallos):2}/{total}")
    for f in fallos:
        print(f"          · {f}")
    return pasa


def limpia():
    """Sesión en blanco: los castigos no pueden colarse de una prueba a otra."""
    for k in list(st.session_state.keys()):
        del st.session_state[k]


class Doble:
    """Un proveedor de mentira. `guion` es una lista de lo que hace cada
    llamada, en orden: un texto lo devuelve, una excepción la levanta, un
    número son segundos que tarda antes de devolver «tarde»."""

    def __init__(self, guion):
        self.guion = list(guion)
        self.llamadas = []          # (proveedor, modelo) de cada intento

    def __call__(self, prov, cli, modelo, sistema, entrada, max_tokens, json, pensar):
        self.llamadas.append((prov, modelo))
        que = self.guion.pop(0) if self.guion else "ok"
        if isinstance(que, BaseException):
            raise que
        if isinstance(que, (int, float)):
            time.sleep(que)
            return "tarde"
        return que

    @property
    def proveedores(self):
        return [p for p, _ in self.llamadas]

    @property
    def modelos(self):
        return [m for _, m in self.llamadas]


def monta(guion):
    """Pone el doble y un cliente de mentira, y devuelve el doble."""
    doble = Doble(guion)
    ia._una_llamada = doble
    ia._cliente = lambda prov: f"cliente-{prov}"
    ia._cliente_para = lambda prov, cli, primero: f"cliente-{prov}"
    return doble


def no_existe(modelo="gemini-3.5-flash-lite"):
    """El 404 tal como lo devuelven los proveedores cuando cierran un modelo."""
    return RuntimeError(
        f"404 NOT_FOUND: models/{modelo} is not found for API version v1beta")


def cupo_diario():
    return RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded, requests per day")


def por_minuto():
    return RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded per minute")


# ---------------------------------------------------------------------------

def p_contesta_el_primero():
    limpia()
    d = monta(["la respuesta"])
    r = ia.genera(None, "s", "e")
    fallos = []
    if r != "la respuesta":
        fallos.append(f"devuelve {r!r}")
    if d.proveedores != ["gemini"]:
        fallos.append(f"ha llamado a {d.proveedores}")
    if ia.ultimo_uso()[0] != "gemini":
        fallos.append(f"apunta {ia.ultimo_uso()}")
    return informe("Si el primero contesta, no se molesta a nadie más", fallos, 3)


def p_cupo_diario_aparta():
    limpia()
    # Gemini dice que no le queda cupo del día: se le aparta sin insistir con
    # sus otros modelos -el cupo es de la cuenta- y contesta Mistral.
    d = monta([cupo_diario(), "de mistral"])
    r = ia.genera(None, "s", "e")
    fallos = []
    if r != "de mistral":
        fallos.append(f"devuelve {r!r}")
    if "gemini" not in ia.quemados():
        fallos.append(f"no ha apartado a gemini: {ia.quemados()}")
    if d.proveedores.count("gemini") != 1:
        fallos.append(f"insiste con gemini: {d.proveedores}")
    # Y en la siguiente consulta ya no se le vuelve a preguntar.
    d2 = monta(["otra vez mistral"])
    ia.genera(None, "s", "e")
    if "gemini" in d2.proveedores:
        fallos.append("vuelve a gemini con el castigo vivo")
    return informe("El cupo del día aparta al proveedor una hora", fallos, 4)


def p_por_minuto_no_aparta():
    limpia()
    d = monta([por_minuto(), "el segundo modelo"])
    r = ia.genera(None, "s", "e")
    fallos = []
    if r != "el segundo modelo":
        fallos.append(f"devuelve {r!r}")
    if ia.quemados():
        fallos.append(f"ha apartado por un tope de un minuto: {ia.quemados()}")
    if d.proveedores != ["gemini", "gemini"]:
        fallos.append(f"ha salido del proveedor: {d.proveedores}")
    return informe("El tope por minuto no aparta a nadie", fallos, 3)


def p_degrada_y_fija():
    limpia()
    d = monta([RuntimeError("503 Service Unavailable"), "el de repuesto"])
    ia.genera(None, "s", "e")
    fallos = []
    if ia.degradados().get("gemini") != ia.PROVEEDORES["gemini"]["modelos"][1]:
        fallos.append(f"no queda degradado: {ia.degradados()}")
    # La siguiente consulta arranca ya en el modelo de repuesto, no reintenta
    # el que acaba de fallar.
    d2 = monta(["otra vez"])
    ia.genera(None, "s", "e")
    if d2.modelos != [ia.PROVEEDORES["gemini"]["modelos"][1]]:
        fallos.append(f"no arranca en el degradado: {d2.modelos}")
    return informe("Un tropiezo degrada el modelo y se recuerda", fallos, 2)


def p_la_degradacion_caduca():
    limpia()
    monta([RuntimeError("503"), "repuesto"])
    ia.genera(None, "s", "e")
    # Se envejece la marca: como si hubieran pasado los cinco minutos.
    st.session_state["ia_modelo_desde"]["gemini"] -= ia.CADUCIDAD_DEGRADACION + 1
    d = monta(["el bueno otra vez"])
    ia.genera(None, "s", "e")
    fallos = []
    if d.modelos != [ia.PROVEEDORES["gemini"]["modelos"][0]]:
        fallos.append(f"no vuelve al bueno: {d.modelos}")
    if ia.degradados():
        fallos.append(f"sigue degradado: {ia.degradados()}")
    return informe("La degradación caduca y se reintenta el bueno", fallos, 2)


def p_el_apartado_caduca():
    limpia()
    monta([cupo_diario(), "mistral"])
    ia.genera(None, "s", "e")
    st.session_state["ia_agotados"]["gemini"] -= ia.CADUCIDAD_CASTIGO + 1
    d = monta(["gemini de vuelta"])
    ia.genera(None, "s", "e")
    fallos = []
    if d.proveedores[:1] != ["gemini"]:
        fallos.append(f"no vuelve a probar gemini: {d.proveedores}")
    if ia.quemados():
        fallos.append(f"sigue apartado: {ia.quemados()}")
    return informe("El apartado caduca a la hora", fallos, 2)


def p_todos_fallan():
    limpia()
    monta([RuntimeError("503 el ultimo error")] * 40)
    fallos = []
    try:
        ia.genera(None, "s", "e")
        fallos.append("no ha levantado excepción")
    except RuntimeError as e:
        if "503" not in str(e):
            fallos.append(f"pierde el error original: {e}")
    except Exception as e:  # noqa: BLE001
        fallos.append(f"cambia el tipo: {type(e).__name__}")
    return informe("Si fallan todos, se relanza el último error", fallos, 1)


def p_sin_claves():
    limpia()
    guardadas = {}
    for p in ia.ORDEN:
        nombre = ia.PROVEEDORES[p]["clave"]
        guardadas[nombre] = os.environ.pop(nombre, None)
    monta(["no deberia llamarse"])
    fallos = []
    try:
        ia.genera(None, "s", "e")
        fallos.append("no avisa de que no hay claves")
    except RuntimeError as e:
        if "clave" not in str(e).lower():
            fallos.append(f"aviso poco claro: {e}")
    finally:
        for nombre, valor in guardadas.items():
            if valor is not None:
                os.environ[nombre] = valor
    return informe("Sin ninguna clave, lo dice en vez de reventar", fallos, 1)


def p_proveedor_fijado():
    limpia()
    st.session_state["ia_proveedor"] = "mistral"
    d = monta([RuntimeError("503")] * 4 + ["no deberia llegar"])
    fallos = []
    try:
        ia.genera(None, "s", "e")
        fallos.append("ha salido del proveedor fijado")
    except RuntimeError:
        pass
    if set(d.proveedores) != {"mistral"}:
        fallos.append(f"ha llamado a {set(d.proveedores)}")
    return informe("Fijar un proveedor apaga la cascada", fallos, 2)


def p_plazo_releva():
    limpia()
    # La primera llamada se cuelga más que el plazo; la siguiente contesta.
    # Con respaldo, la colgada gasta dos intentos: el original y su respaldo.
    d = monta([1.0, 1.0, "el siguiente modelo"])
    arranque = time.perf_counter()
    r = ia.genera(None, "s", "e", plazo=0.3, respaldo=0.1)
    tardado = time.perf_counter() - arranque
    fallos = []
    if r != "el siguiente modelo":
        fallos.append(f"devuelve {r!r}")
    if tardado > 1.0:
        fallos.append(f"ha esperado a la colgada: {tardado:.2f} s")
    return informe("Una llamada colgada se releva sin esperarla", fallos, 2)


def p_anota_los_relevos():
    limpia()
    monta([RuntimeError("503 primero"), "el segundo"])
    lineas = []
    ia.genera(None, "s", "e", al_relevar=lineas.append)
    fallos = []
    if len(lineas) != 1:
        fallos.append(f"anota {len(lineas)} líneas: {lineas}")
    elif "503" not in lineas[0] and "RuntimeError" not in lineas[0]:
        fallos.append(f"la línea no dice qué pasó: {lineas[0]}")
    return informe("Cada relevo deja su línea", fallos, 1)


def p_modelo_fijado_con_degradacion_vieja():
    """El caso que se colaba: fijar un modelo deja la cadena en uno solo, y un
    índice de degradación más alto dejaba el `range` vacío. El proveedor se
    saltaba entero sin intentarlo, y con un solo proveedor eso es quedarse sin
    IA con la clave puesta y el modelo respondiendo."""
    limpia()
    st.session_state["ia_modelo_ok"] = {"gemini": 3}
    st.session_state["ia_modelo_desde"] = {"gemini": time.time()}
    st.session_state["ia_modelo_fijo"] = ia.PROVEEDORES["gemini"]["modelos"][0]
    d = monta(["con el modelo fijado"])
    fallos = []
    r = ia.genera(None, "s", "e")
    if r != "con el modelo fijado":
        fallos.append(f"devuelve {r!r}")
    if d.modelos != [ia.PROVEEDORES["gemini"]["modelos"][0]]:
        fallos.append(f"ha llamado a {d.modelos}")
    return informe("Un modelo fijado se usa aunque hubiera degradación", fallos, 2)


def p_modelo_que_no_existe():
    """Un nombre de modelo que el proveedor no reconoce no es un tropiezo: no
    va a existir por esperar cinco minutos. Sale de la cadena de la sesión, y
    la consulta siguiente ya no lo paga."""
    limpia()
    d = monta([no_existe(), "el siguiente modelo"])
    fallos = []
    r = ia.genera(None, "s", "e")
    if r != "el siguiente modelo":
        fallos.append(f"devuelve {r!r}")
    muerto = ia.PROVEEDORES["gemini"]["modelos"][0]
    if ia.muertos().get("gemini") != [muerto]:
        fallos.append(f"no lo anota como inexistente: {ia.muertos()}")
    if ia.degradados():
        fallos.append(f"lo trata como degradación: {ia.degradados()}")
    # La consulta siguiente NO vuelve a intentarlo.
    d2 = monta(["ya sin pagar el intento"])
    ia.genera(None, "s", "e")
    if muerto in d2.modelos:
        fallos.append(f"vuelve a llamar al que no existe: {d2.modelos}")
    return informe("Un modelo que no existe sale de la cadena", fallos, 4)


def p_proveedor_entero_sin_modelos():
    """Lo que le pasó a main: los tres modelos de Gemini cerrados a la vez, la
    rama entera muerta y todo resuelto por el de respaldo sin avisar. Aquí se
    salta al proveedor y se anota, para que el panel lo pueda decir."""
    limpia()
    cuantos = len(ia.PROVEEDORES["gemini"]["modelos"])
    d = monta([no_existe(m) for m in ia.PROVEEDORES["gemini"]["modelos"]] + ["de mistral"])
    fallos = []
    r = ia.genera(None, "s", "e")
    if r != "de mistral":
        fallos.append(f"devuelve {r!r}")
    if len(ia.muertos().get("gemini", [])) != cuantos:
        fallos.append(f"no anota los {cuantos}: {ia.muertos()}")
    # Y en la consulta siguiente ni se le pregunta.
    d2 = monta(["mistral otra vez"])
    ia.genera(None, "s", "e")
    if "gemini" in d2.proveedores:
        fallos.append(f"sigue llamando a gemini: {d2.proveedores}")
    return informe("Un proveedor sin modelos vivos se salta entero", fallos, 3)


def p_no_confunde_404_con_lo_demas():
    limpia()
    fallos = []
    for e, debe in (
        (no_existe(), True),
        (RuntimeError("404 NOT_FOUND: models/x is not found"), True),
        (cupo_diario(), False),
        (por_minuto(), False),
        (RuntimeError("503 Service Unavailable"), False),
        (TimeoutError("Sin respuesta del modelo en 6 s."), False),
        (RuntimeError("400 INVALID_ARGUMENT"), False),
    ):
        if ia.no_existe(e) is not debe:
            fallos.append(f"{str(e)[:40]!r}: dice {ia.no_existe(e)}, debe ser {debe}")
    return informe("«No existe» no se confunde con cuota ni con caídas", fallos, 7)


def p_prueba_todos_los_modelos():
    """El botón «Probar TODOS los modelos» del panel es lo único que puede
    decir qué nombres han caducado cuando las claves solo están en el
    despliegue: tiene que recorrer la lista entera, no el modelo de turno, y
    dejar dicho cuál no existe."""
    limpia()
    modelos = ia.PROVEEDORES["gemini"]["modelos"]
    # El primero ya no existe; los demás contestan. Mistral y Groq, también.
    d = monta([no_existe(modelos[0])] + ["ok"] * 20)
    ok, detalle = ia.prueba(todos=True)
    fallos = []
    if not ok:
        fallos.append("da por fallida una prueba en la que casi todo responde")
    if modelos[0] not in detalle or "NO EXISTE" not in detalle:
        fallos.append("no dice cuál es el que no existe")
    if d.modelos.count(modelos[-1]) != 1:
        fallos.append(f"no ha probado la lista entera: {d.modelos}")
    if ia.muertos().get("gemini") != [modelos[0]]:
        fallos.append(f"no lo saca de la cadena: {ia.muertos()}")
    return informe("«Probar todos» recorre la lista y señala al que falta", fallos, 4)


def p_el_perfil_cambia_la_cadena():
    """Los informes redactan tres veces al día y quieren el modelo que mejor
    escribe; el codificador contesta cientos de veces y quiere el rápido. Cada
    uno pide su cadena, y no son la misma."""
    limpia()
    d = monta(["ok"])
    ia.genera(None, "s", "e", perfil=ia.CALIDAD)
    fallos = []
    esperado = ia.PROVEEDORES["gemini"]["modelos_calidad"][0]
    if d.modelos != [esperado]:
        fallos.append(f"con CALIDAD llama a {d.modelos}, no a {esperado}")
    limpia()
    d = monta(["ok"])
    ia.genera(None, "s", "e")
    if d.modelos != [ia.PROVEEDORES["gemini"]["modelos"][0]]:
        fallos.append(f"sin perfil llama a {d.modelos}")
    return informe("Cada herramienta pide la cadena que le toca", fallos, 2)


def p_los_castigos_no_se_mezclan():
    """El modelo bueno de los informes se queda sin cupo a media mañana. Eso no
    puede degradar la cadena del codificador, que usa otros modelos."""
    limpia()
    monta([RuntimeError("503"), "el segundo de calidad"])
    ia.genera(None, "s", "e", perfil=ia.CALIDAD)
    fallos = []
    d = monta(["ok"])
    ia.genera(None, "s", "e")          # el codificador, sin perfil
    if d.modelos != [ia.PROVEEDORES["gemini"]["modelos"][0]]:
        fallos.append(f"el codificador arranca degradado: {d.modelos}")
    # Y al revés: la cadena de calidad sigue donde la dejamos.
    d = monta(["ok"])
    ia.genera(None, "s", "e", perfil=ia.CALIDAD)
    if d.modelos != [ia.PROVEEDORES["gemini"]["modelos_calidad"][1]]:
        fallos.append(f"la de calidad no recuerda su relevo: {d.modelos}")
    return informe("Los castigos de una cadena no tocan a la otra", fallos, 2)


def p_sin_cupo_el_bueno_sigue_por_los_rapidos():
    """Lo que hace que esto sea seguro: cuando el modelo bueno agota su cupo
    del día, el informe sale igual con el de siempre. Peor escrito, pero
    sale."""
    limpia()
    calidad = ia.PROVEEDORES["gemini"]["modelos_calidad"]
    # Fallan los completos; contesta el primer Lite de la misma cadena.
    d = monta([RuntimeError("503")] * 3 + ["con el rapido"])
    fallos = []
    r = ia.genera(None, "s", "e", perfil=ia.CALIDAD)
    if r != "con el rapido":
        fallos.append(f"devuelve {r!r}")
    if d.modelos != calidad[:4]:
        fallos.append(f"no recorre la cadena de calidad entera: {d.modelos}")
    if d.proveedores != ["gemini"] * 4:
        fallos.append(f"se sale del proveedor: {d.proveedores}")
    return informe("Sin cupo del bueno, el informe sale con el rápido", fallos, 3)


def p_proveedor_sin_lista_de_calidad():
    """Groq no tiene `modelos_calidad` porque no hay clave con la que saber qué
    modelos grandes tiene hoy. Pedir calidad no puede dejarlo fuera."""
    limpia()
    st.session_state["ia_proveedor"] = "groq"
    d = monta(["ok"])
    ia.genera(None, "s", "e", perfil=ia.CALIDAD)
    fallos = []
    if d.modelos != [ia.PROVEEDORES["groq"]["modelos"][0]]:
        fallos.append(f"llama a {d.modelos}")
    return informe("Sin lista de calidad se usa la normal", fallos, 1)


def p_transcribe_salta_a_quien_sabe():
    limpia()
    # Gemini y Groq saben transcribir; Mistral no, y hay que saltárselo.
    pedidos = []

    class ClienteFalso:
        def __init__(self, prov):
            self.prov = prov
            self.audio = self
            self.transcriptions = self

        def create(self, **k):
            pedidos.append(self.prov)
            return type("R", (), {"text": "lo dicho"})()

    ia._cliente = lambda prov: ClienteFalso(prov)
    ia._cliente_para = lambda prov, cli, primero: ClienteFalso(prov)
    st.session_state["ia_agotados"] = {"gemini": time.time()}   # gemini, fuera
    fallos = []
    r = ia.transcribe(None, b"audio")
    if r != "lo dicho":
        fallos.append(f"devuelve {r!r}")
    if pedidos != ["groq"]:
        fallos.append(f"ha pedido la transcripción a {pedidos}")
    return informe("Transcribe solo quien sabe, y se salta a quien no", fallos, 2)


PRUEBAS = [
    p_contesta_el_primero,
    p_cupo_diario_aparta,
    p_por_minuto_no_aparta,
    p_degrada_y_fija,
    p_la_degradacion_caduca,
    p_el_apartado_caduca,
    p_todos_fallan,
    p_sin_claves,
    p_proveedor_fijado,
    p_plazo_releva,
    p_anota_los_relevos,
    p_modelo_fijado_con_degradacion_vieja,
    p_modelo_que_no_existe,
    p_proveedor_entero_sin_modelos,
    p_no_confunde_404_con_lo_demas,
    p_prueba_todos_los_modelos,
    p_el_perfil_cambia_la_cadena,
    p_los_castigos_no_se_mezclan,
    p_sin_cupo_el_bueno_sigue_por_los_rapidos,
    p_proveedor_sin_lista_de_calidad,
    p_transcribe_salta_a_quien_sabe,
]


def main():
    print(f"Cascada: {' → '.join(ia.ORDEN)}")
    print(f"Con clave de mentira: {[p for p in ia.ORDEN if ia.tiene_clave(p)]}\n")
    arranque = time.perf_counter()
    for prueba in PRUEBAS:
        try:
            prueba()
        except Exception as e:  # noqa: BLE001
            nombre = prueba.__name__.removeprefix("p_").replace("_", " ")
            RESUMEN.append((nombre, False))
            print(f"[MAL] {nombre:44} {type(e).__name__}: {e}")
    bien = sum(1 for _, ok in RESUMEN if ok)
    print(f"\n{bien} de {len(RESUMEN)} pruebas pasan  ·  {time.perf_counter() - arranque:.1f}s")
    return 0 if bien == len(RESUMEN) else 1


if __name__ == "__main__":
    sys.exit(main())
