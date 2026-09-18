"""
Batería del generador de CV: los botones de «Otros datos de interés».

Esos apartados -permiso, idiomas, informática, disponibilidad, otros- son
campos de texto libre y así siguen: es lo que se imprime en el documento. Los
botones de la pantalla solo ESCRIBEN en ese texto las frases de siempre.

Lo que se comprueba aquí es justo eso: que lo que escriben tiene el estilo del
modelo de la oficina, que marcar y desmarcar es reversible, y sobre todo que
NO SE COME lo que la persona haya escrito a mano, que es lo que convertiría una
comodidad en una pérdida de datos.

USO
    ~/.venvs/sispe/bin/python cv.py

Necesita las dependencias instaladas: `herramientas/cv/motor.py` importa
reportlab para el PDF. No llama a la IA ni gasta cuota.
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from herramientas.cv import motor  # noqa: E402

RESUMEN = []


def informe(nombre, fallos, total):
    pasa = not fallos
    RESUMEN.append((nombre, pasa))
    print(f"[{' OK ' if pasa else 'MAL'}] {nombre:46} {total - len(fallos):2}/{total}")
    for f in fallos:
        print(f"          · {f}")
    return pasa


def p_el_estilo_es_el_del_modelo():
    """Las frases tienen que salir como están escritas en los currículos de la
    oficina, no como las diría un programador."""
    fallos = []
    esperado = {
        motor.frase_permiso("B"): "Carnet de conducir B.",
        motor.frase_permiso("C+E (tráiler)"): "Carnet de conducir C+E.",
        motor.frase_permiso("Vehículo propio"): "Vehículo propio.",
        motor.frase_idioma("Español", "nativo"): "Español nativo.",
        motor.frase_idioma("Inglés", "básico"): "Inglés básico.",
        motor.frase_informatica(["correo electrónico"]): "Manejo de correo electrónico.",
        motor.frase_informatica(["correo electrónico", "Word"]):
            "Manejo de correo electrónico y Word.",
        motor.frase_informatica(["correo electrónico", "Word", "Excel"]):
            "Manejo de correo electrónico, Word y Excel.",
    }
    for sale, debe in esperado.items():
        if sale != debe:
            fallos.append(f"sale {sale!r} y debe salir {debe!r}")
    for frase in motor.DISPONIBILIDAD + motor.OTROS_DATOS:
        if not frase.endswith("."):
            fallos.append(f"sin punto final: {frase!r}")
        if frase[:1] != frase[:1].upper():
            fallos.append(f"sin mayúscula inicial: {frase!r}")
    return informe("Las frases salen con el estilo del modelo", fallos, len(esperado) + 2)


def p_marcar_y_desmarcar():
    fallos = []
    cat = motor.catalogo_permisos()
    t = motor.compone("", [motor.frase_permiso("B")], cat)
    if t != "Carnet de conducir B.":
        fallos.append(f"marcar uno da {t!r}")
    t2 = motor.compone(t, [motor.frase_permiso("B"), motor.frase_permiso("Vehículo propio")], cat)
    if t2 != "Carnet de conducir B. Vehículo propio.":
        fallos.append(f"marcar dos da {t2!r}")
    t3 = motor.compone(t2, [motor.frase_permiso("Vehículo propio")], cat)
    if t3 != "Vehículo propio.":
        fallos.append(f"desmarcar el primero da {t3!r}")
    t4 = motor.compone(t3, [], cat)
    if t4 != "":
        fallos.append(f"desmarcar todo deja {t4!r}, no vacío")
    return informe("Marcar y desmarcar es reversible", fallos, 4)


def p_no_se_come_lo_escrito_a_mano():
    """El que más duele si falla: alguien escribe tres líneas suyas y un botón
    se las lleva por delante."""
    fallos = []
    cat = motor.catalogo_permisos()
    suyo = "Carné de carretillero en vigor desde 2019."
    t = motor.compone(suyo, [motor.frase_permiso("B")], cat)
    if suyo not in t:
        fallos.append(f"al marcar se pierde lo escrito: {t!r}")
    t2 = motor.compone(t, [], cat)
    if t2 != suyo:
        fallos.append(f"al desmarcar queda {t2!r} en vez de {suyo!r}")
    # Y con saltos de línea, que es como va «Otros datos».
    mio = "Disponible para mudanzas.\nTengo furgoneta."
    t3 = motor.compone(mio, [motor.OTROS_DATOS[0]], motor.OTROS_DATOS, salto=True)
    if mio not in t3:
        fallos.append(f"con saltos se pierde: {t3!r}")
    if t3.splitlines()[0] != motor.OTROS_DATOS[0]:
        fallos.append(f"la marcada no va la primera: {t3!r}")
    t4 = motor.compone(t3, [], motor.OTROS_DATOS, salto=True)
    if t4 != mio:
        fallos.append(f"al desmarcar queda {t4!r} en vez de {mio!r}")
    return informe("No se come lo que se escribió a mano", fallos, 5)


def p_componer_dos_veces_no_cambia_nada():
    """La pantalla recompone en cada pulsación: si no fuera idempotente, el
    texto crecería solo."""
    fallos = []
    cat = motor.catalogo_idiomas()
    frases = [motor.frase_idioma("Español", "nativo"), motor.frase_idioma("Inglés", "medio")]
    uno = motor.compone("Lo mío.", frases, cat)
    dos = motor.compone(uno, frases, cat)
    tres = motor.compone(dos, frases, cat)
    if not (uno == dos == tres):
        fallos.append(f"crece: {uno!r} -> {dos!r} -> {tres!r}")
    if uno.count("Español nativo.") != 1:
        fallos.append(f"duplica la frase: {uno!r}")
    return informe("Componer dos veces no cambia nada", fallos, 2)


def p_cambiar_el_nivel_sustituye():
    """Subir a alguien de «básico» a «medio» tiene que SUSTITUIR, no añadir una
    segunda línea que se contradice con la primera."""
    fallos = []
    cat = motor.catalogo_idiomas()
    t = motor.compone("", [motor.frase_idioma("Inglés", "básico")], cat)
    t2 = motor.compone(t, [motor.frase_idioma("Inglés", "medio")], cat)
    if t2 != "Inglés medio.":
        fallos.append(f"queda {t2!r}")
    if "básico" in t2:
        fallos.append("se queda el nivel viejo")
    if motor.nivel_de(t2, "Inglés") != "medio":
        fallos.append(f"lo lee como {motor.nivel_de(t2, 'Inglés')}")
    return informe("Cambiar el nivel sustituye, no acumula", fallos, 3)


def p_lo_marcado_se_lee_del_texto():
    """No hay dato aparte: los botones se encienden con lo que ponga el texto,
    lo haya escrito un botón o una persona."""
    fallos = []
    a_mano = "Español nativo. Inglés alto. Algo mío."
    if motor.idiomas_de(a_mano) != [("Español", "nativo"), ("Inglés", "alto")]:
        fallos.append(f"lee {motor.idiomas_de(a_mano)}")
    if motor.marcadas("Carnet de conducir B.", motor.catalogo_permisos()) != ["Carnet de conducir B."]:
        fallos.append("no reconoce el permiso escrito a mano")
    if motor.informatica_de("Manejo de Word y Excel.") != ["Word", "Excel"]:
        fallos.append(f"informática: lee {motor.informatica_de('Manejo de Word y Excel.')}")
    if motor.idiomas_de("") != []:
        fallos.append("inventa idiomas con el campo vacío")
    return informe("Lo marcado se lee de lo escrito", fallos, 4)


def p_informatica_se_rehace_entera():
    fallos = []
    t = motor.compone_informatica("", ["Word"])
    if t != "Manejo de Word.":
        fallos.append(f"una: {t!r}")
    t2 = motor.compone_informatica(t, ["Word", "Excel"])
    if t2 != "Manejo de Word y Excel.":
        fallos.append(f"dos: {t2!r}")
    t3 = motor.compone_informatica("Mecanografía rápida. " + t2, ["Excel"])
    if t3 != "Manejo de Excel. Mecanografía rápida.":
        fallos.append(f"con texto propio: {t3!r}")
    t4 = motor.compone_informatica(t3, [])
    if t4 != "Mecanografía rápida.":
        fallos.append(f"al vaciar: {t4!r}")
    return informe("La frase de informática se rehace entera", fallos, 4)


def p_llega_al_documento_igual_que_antes():
    """Lo que de verdad importa: que el apartado del currículo salga como
    siempre. Los botones no pueden cambiar el documento, solo llenarlo."""
    fallos = []
    cv = motor.nuevo()
    cv["nombre"] = "Nombre Apellido"
    cv["permiso"] = motor.compone("", [motor.frase_permiso("B")], motor.catalogo_permisos())
    cv["idiomas"] = motor.compone("", [motor.frase_idioma("Español", "nativo"),
                                       motor.frase_idioma("Inglés", "básico")],
                                  motor.catalogo_idiomas())
    cv["informatica"] = motor.compone_informatica("", ["correo electrónico", "Word"])
    cv["otros"] = motor.compone("", motor.OTROS_DATOS[:2], motor.OTROS_DATOS, salto=True)
    texto = motor.texto_plano(cv)

    if "OTROS DATOS DE INTERÉS" not in texto:
        fallos.append("no sale el apartado")
    for debe in ("·   Idiomas: Español nativo. Inglés básico.",
                 "·   Informática: Manejo de correo electrónico y Word.",
                 "·   Carnet de conducir B.",
                 "·   Certificado de manipulador de alimentos.",
                 "·   Carné de carretillero."):
        if debe not in texto:
            fallos.append(f"falta la línea {debe!r}")
    if ".." in texto:
        fallos.append("hay puntos dobles en el documento")
    # Y el PDF se genera sin reventar con todo eso dentro.
    try:
        pdf = motor.documento_pdf(cv)
        if not pdf or len(pdf) < 500:
            fallos.append("el PDF sale vacío")
    except Exception as e:  # noqa: BLE001
        fallos.append(f"el PDF revienta: {type(e).__name__}: {e}")
    return informe("El documento sale como siempre", fallos, 8)


# ---------------------------------------------------------------------------
# La pantalla de verdad
# ---------------------------------------------------------------------------
# Lo de arriba comprueba la lógica. Esto comprueba el CABLEADO, que es donde
# falla este tipo de cosa: que al pulsar el botón cambie de verdad la caja de
# texto de al lado. Se hace con el banco de pruebas de Streamlit, que ejecuta
# la pantalla sin navegador y deja pulsar los controles.

ENVOLTORIO = """
import os, sys
RAIZ = {raiz!r}
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
import streamlit as st
# El menú de la banda negra y los enlaces entre herramientas llaman a
# page_link, que solo existe con la navegación de app.py montada. Aquí se
# ejecuta la página suelta, así que se desactivan.
from streamlit.delta_generator import DeltaGenerator
DeltaGenerator.page_link = lambda self, *a, **k: None
st.page_link = lambda *a, **k: None
ruta = os.path.join(RAIZ, "herramientas/cv/vista.py")
exec(compile(open(ruta, encoding="utf-8").read(), ruta, "exec"),
     {{"__name__": "__main__", "__file__": ruta}})
"""


def abre_pantalla():
    import tempfile
    from streamlit.testing.v1 import AppTest
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(ENVOLTORIO.format(raiz=RAIZ))
    tmp.close()
    at = AppTest.from_file(tmp.name, default_timeout=120)
    at.run()
    return at


def _caja(at, etiqueta):
    cajas = [w for w in list(at.text_input) + list(at.text_area) if w.label.startswith(etiqueta)]
    return cajas[0] if cajas else None


def _grupo(at, clave):
    grupos = [g for g in at.get("button_group") if g.key == clave]
    return grupos[0] if grupos else None


def p_pantalla_paso_1():
    """Permiso y disponibilidad, que están en el paso 1."""
    at = abre_pantalla()
    fallos = []

    _grupo(at, "cv_p_permiso").select("B").run()
    valor = _caja(at, "Permiso").value
    if valor != "Carnet de conducir B.":
        fallos.append(f"pulsar B deja {valor!r}")

    _grupo(at, "cv_p_permiso").select("Vehículo propio").run()
    valor = _caja(at, "Permiso").value
    if valor != "Carnet de conducir B. Vehículo propio.":
        fallos.append(f"añadir vehículo deja {valor!r}")

    _grupo(at, "cv_p_permiso").unselect("B").run()
    valor = _caja(at, "Permiso").value
    if valor != "Vehículo propio.":
        fallos.append(f"despulsar B deja {valor!r}")

    # Lo escrito a mano en la caja, con un botón pulsado después.
    _caja(at, "Permiso").set_value("Vehículo propio. Furgoneta de 3.500 kg.").run()
    _grupo(at, "cv_p_permiso").select("C (camión)").run()
    valor = _caja(at, "Permiso").value
    if "Furgoneta de 3.500 kg." not in valor or "Carnet de conducir C." not in valor:
        fallos.append(f"se pierde lo escrito a mano: {valor!r}")

    _grupo(at, "cv_p_disponibilidad").select("Incorporación inmediata.").run()
    if _caja(at, "Disponibilidad").value != "Incorporación inmediata.":
        fallos.append(f"disponibilidad: {_caja(at, 'Disponibilidad').value!r}")

    if at.exception:
        fallos.append(f"excepción en la pantalla: {str(at.exception[0].value)[:80]}")
    return informe("En la pantalla: permiso y disponibilidad", fallos, 6)


def p_pantalla_paso_3():
    """Idiomas con su nivel, informática y otros datos."""
    at = abre_pantalla()
    at.session_state["cv_paso"] = 2
    at.run()
    fallos = []

    _grupo(at, "cv_p_idiomas").select("Español").select("Inglés").run()
    valor = _caja(at, "Idiomas").value
    if valor != "Español nativo. Inglés básico.":
        fallos.append(f"marcar dos idiomas deja {valor!r}")

    # El nivel es un control aparte por cada idioma marcado.
    nivel = _grupo(at, "cv_n_Inglés")
    if nivel is None:
        fallos.append("no aparece el selector de nivel del idioma marcado")
    else:
        nivel.set_value("alto").run()
        valor = _caja(at, "Idiomas").value
        if valor != "Español nativo. Inglés alto.":
            fallos.append(f"subir el nivel deja {valor!r}")

    _grupo(at, "cv_p_informatica").select("correo electrónico").select("Word").run()
    valor = _caja(at, "Informática").value
    if valor != "Manejo de correo electrónico y Word.":
        fallos.append(f"informática deja {valor!r}")

    _grupo(at, "cv_p_otros").select("Carné de carretillero.").run()
    valor = _caja(at, "Otros datos").value
    if valor != "Carné de carretillero.":
        fallos.append(f"otros datos deja {valor!r}")

    if at.exception:
        fallos.append(f"excepción en la pantalla: {str(at.exception[0].value)[:80]}")
    return informe("En la pantalla: idiomas, informática y otros", fallos, 5)


PRUEBAS = [
    p_el_estilo_es_el_del_modelo,
    p_marcar_y_desmarcar,
    p_no_se_come_lo_escrito_a_mano,
    p_componer_dos_veces_no_cambia_nada,
    p_cambiar_el_nivel_sustituye,
    p_lo_marcado_se_lee_del_texto,
    p_informatica_se_rehace_entera,
    p_llega_al_documento_igual_que_antes,
    p_pantalla_paso_1,
    p_pantalla_paso_3,
]


def main():
    print(f"Botones: {len(motor.PERMISOS)} de permiso · {len(motor.IDIOMAS)} idiomas × "
          f"{len(motor.NIVELES_IDIOMA)} niveles · {len(motor.INFORMATICA)} de informática · "
          f"{len(motor.DISPONIBILIDAD)} de disponibilidad · {len(motor.OTROS_DATOS)} otros\n")
    for prueba in PRUEBAS:
        try:
            prueba()
        except Exception as e:  # noqa: BLE001
            nombre = prueba.__name__.removeprefix("p_").replace("_", " ")
            RESUMEN.append((nombre, False))
            print(f"[MAL] {nombre:46} {type(e).__name__}: {e}")
    bien = sum(1 for _, ok in RESUMEN if ok)
    print(f"\n{bien} de {len(RESUMEN)} pruebas pasan")
    return 0 if bien == len(RESUMEN) else 1


if __name__ == "__main__":
    sys.exit(main())
