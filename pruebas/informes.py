"""
Batería del documento de preparación de sesión.

El protocolo pide dos páginas A4 y lo dice en serio: si el documento se va a
tres, deja de servir para lo que sirve, que es llevarlo impreso a la entrevista
y escribir encima. Aquí se comprueba midiendo el PDF, no mirándolo.

Lo que se prueba:

  · Que cabe en dos páginas, incluso con el contenido en el tope de lo que el
    prompt le permite devolver a la IA.
  · Que no encoge la letra más de la cuenta para conseguirlo.
  · Que el papel sale sin firma, sin logotipo, sin mención institucional y con
    los metadatos sin autoría.
  · Que la frase de cautela va siempre y no se duplica.
  · Que el texto ajeno se escapa antes de convertirlo en marcado.
  · Que una ficha incompleta o rara no revienta.

Las fichas de prueba son inventadas, pero con la misma forma y la misma
densidad de texto que los documentos reales: con palabras largas de relleno el
texto ocupa casi el doble y la medida no vale para nada.

USO
    python informes.py              todas las pruebas
    python informes.py --detalle    enseña lo que falla, caso a caso

No llama a la IA ni gasta cuota. Tarda un par de segundos.
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001  consolas antiguas
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from herramientas.informes import motor  # noqa: E402

DETALLE = "--detalle" in sys.argv

PRUEBAS = []
RESUMEN = []


def prueba(nombre):
    def envuelve(f):
        PRUEBAS.append((nombre, f))
        return f
    return envuelve


def anota(nombre, ok, detalle=""):
    RESUMEN.append((nombre, ok))
    print(f"[ {'OK' if ok else '--'} ] {nombre:44} {detalle}")
    return ok


# ---------------------------------------------------------------------------
# Fichas de prueba
# ---------------------------------------------------------------------------

# Un pozo de palabras con la densidad del castellano corriente (unas 4,9 letras
# por palabra). El relleno inventado, todo de palabras largas, mide casi el
# doble y haría que la prueba midiera otra cosa.
_POZO = (
    "el objetivo que declara se apoya en experiencia cerrada hace años y su "
    "trayectoria verificable en españa es de otro sector quien lea el cv ve los "
    "tres últimos años y clasifica el perfil de apertura promete cosas que ningún "
    "empleo respalda a eso se suman nueve ocupaciones en áreas de interés y una "
    "formación antigua que no acredita nada y sí revela la edad es contratable ya "
    "porque son sectores de alta rotación en madrid pero no ha elegido todavía"
).split()


def pal(n):
    """`n` palabras de relleno, con la densidad del texto real."""
    if not n:
        return ""
    return " ".join(_POZO[i % len(_POZO)] for i in range(n)).capitalize() + "."


def tope():
    """El máximo que el prompt le permite devolver a la IA, todo a la vez.

    Si esta ficha cabe en dos páginas, cualquier respuesta que respete el
    prompt cabe. Los números salen de la sección MEDIDA de
    `herramientas/informes/modelo.py`: si allí se suben, hay que subirlos aquí.
    """
    return {
        "rasgo": "tope_del_prompt",
        "entradilla": pal(35),
        "trayectoria": [
            {"periodo": "01/2018 – 10/2024", "duracion": "6 a. 10 m.",
             "que": "Auxiliar de auditoría, cadena de droguerías (Colombia). Único empleo declarado"}
            for _ in range(8)
        ],
        "tension": {"rotulo": "Las dos cosas que ordenan esta sesión", "texto": pal(85)},
        "hipotesis": pal(110),
        "direcciones_entradilla": pal(22),
        "direcciones": [
            {"papel": papel, "familia": "Administración de inventario y stock",
             "variantes": "Control de existencias, apoyo administrativo en almacén y logística",
             "acredita": pal(28), "falta": pal(45)}
            for papel in ("Principal", "Secundaria", "A explorar")
        ],
        "preguntas": [{"rotulo": "Rótulo de bloque razonablemente largo", "texto": pal(35)}
                      for _ in range(8)],
        "acciones": [{"rotulo": "Rótulo de acción razonablemente largo", "texto": pal(35)}
                     for _ in range(6)],
        "riesgo": {"rotulo": "Los dos riesgos a evitar", "texto": pal(65)},
    }


def corriente():
    """Una ficha del tamaño que salen normalmente."""
    f = tope()
    f["rasgo"] = "comercio_limpieza"
    f["trayectoria"] = f["trayectoria"][:6]
    f["tension"]["texto"] = pal(60)
    f["hipotesis"] = pal(85)
    f["preguntas"] = f["preguntas"][:6]
    f["acciones"] = f["acciones"][:4]
    return f


RARA = {
    "entradilla": "Con <caracteres> & raros \"y\" 'comillas'",
    "trayectoria": [{"periodo": "2020", "que": "R&D <b>no</b> es etiqueta", "duracion": "1 a."}],
    "tension": {"rotulo": "A & B", "texto": "Con **negrita sin cerrar y <tag>"},
    "hipotesis": "**A3** con *capa* de **A2**",
    "direcciones": [{"papel": "Principal", "familia": "X & Y", "variantes": "",
                     "acredita": "<script>", "falta": "a>b"}],
    "preguntas": [{"rotulo": "¿Y?", "texto": "&&&"}],
    "acciones": [{"rotulo": None, "texto": None}],
    "riesgo": {"rotulo": "", "texto": "ok"},
}


def texto_del_documento(ficha):
    """Todo el texto que se va a imprimir, en una cadena.

    Se lee del flujo de elementos y no del PDF ya escrito: reportlab
    subconjunta las fuentes y dentro del archivo el texto va codificado, así
    que sacarlo de ahí pediría una librería de lectura de PDF que este
    proyecto no necesita para nada más.
    """
    from reportlab.platypus import Paragraph, Table

    def recorre(cosa):
        if isinstance(cosa, Paragraph):
            yield cosa.text
        elif isinstance(cosa, Table):
            for fila in cosa._cellvalues:
                for celda in fila:
                    yield from recorre(celda)
        elif isinstance(cosa, (list, tuple)):
            for x in cosa:
                yield from recorre(x)

    return " ".join(recorre(motor._flujo(ficha, 1.0)))


# ---------------------------------------------------------------------------
# Las pruebas
# ---------------------------------------------------------------------------

@prueba("Cabe en dos páginas")
def cabe():
    casos = [("en el tope del prompt", tope(), 2),
             ("del tamaño corriente", corriente(), 2),
             ("con caracteres raros", RARA, 2),
             ("sólo con la entradilla", {"entradilla": "Perfil."}, 1),
             ("completamente vacía", {}, 1)]
    malas = []
    for etiqueta, ficha, esperadas in casos:
        _, d = motor.documento_pdf(ficha, con_detalle=True)
        if d["paginas"] != esperadas:
            malas.append(f"{etiqueta}: {d['paginas']} páginas, esperadas {esperadas}")
    return anota("Cabe en dos páginas", not malas,
                 f"{len(casos) - len(malas)}/{len(casos)} fichas"), malas


@prueba("No encoge la letra de más")
def no_encoge():
    """El ajuste existe para los casos raros, no para el uso normal.

    Con Caladea y Carlito, una ficha del tamaño corriente sale a tamaño
    completo. Sin ellas, DejaVu es más ancha y hay que bajar un punto: por eso
    interesa que `packages.txt` llegue al servidor.
    """
    corriente_minimo = 1.0 if motor.CON_FUENTES_DEL_PROTOCOLO else 0.88
    malas = []
    for etiqueta, ficha, minimo in (("corriente", corriente(), corriente_minimo),
                                    ("tope del prompt", tope(), 0.86)):
        _, d = motor.documento_pdf(ficha, con_detalle=True)
        if d["factor"] < minimo:
            malas.append(f"{etiqueta}: factor {d['factor']}, mínimo aceptable {minimo}")
    return anota("No encoge la letra de más", not malas,
                 f"mínimo del motor: {motor.FACTOR_MINIMO}"), malas


@prueba("El papel no lleva membrete")
def sin_membrete():
    pdf = motor.documento_pdf(corriente())
    texto = texto_del_documento(corriente())
    malas = [f"aparece «{x}»" for x in
             ("Comunidad de Madrid", "Oficina de Empleo", "SEPE", "Ciudad Lineal")
             if x in texto]
    if b"/Author (" in pdf and b"/Author ()" not in pdf:
        malas.append("los metadatos llevan autoría")
    return anota("El papel no lleva membrete", not malas), malas


@prueba("La frase de cautela va siempre")
def cautela():
    malas = []
    for entradilla in ("Perfil de comercio.", "", None):
        texto = texto_del_documento({"entradilla": entradilla, "hipotesis": "x"})
        veces = texto.count("Lectura hecha únicamente")
        if veces != 1:
            malas.append(f"entradilla {entradilla!r}: la frase sale {veces} veces")
    return anota("La frase de cautela va siempre", not malas), malas


@prueba("El texto ajeno se escapa")
def escapa():
    casos = [
        ("**A3** con capa", "<b>A3</b> con capa"),
        ("*facility services*", "<i>facility services</i>"),
        ("R&D <b>literal</b>", "R&amp;D &lt;b&gt;literal&lt;/b&gt;"),
        ("**a & b**", "<b>a &amp; b</b>"),
        ("**sin cerrar", "**sin cerrar"),
        ("2 * 3 = 6", "2 * 3 = 6"),
        (None, ""),
    ]
    malas = [f"{e!r} -> {motor.rico(e)!r}, esperado {s!r}"
             for e, s in casos if motor.rico(e) != s]
    return anota("El texto ajeno se escapa", not malas,
                 f"{len(casos) - len(malas)}/{len(casos)} casos"), malas


@prueba("Las secciones vacías no se pintan")
def secciones():
    texto = texto_del_documento({"entradilla": "Perfil.", "hipotesis": "A3"})
    malas = []
    if "La trayectoria en una lectura" in texto:
        malas.append("sale la sección 1 sin trayectoria")
    if "Lo que hay que preguntar" in texto:
        malas.append("sale la sección 4 sin preguntas")
    if "Hipótesis de partida" not in texto:
        malas.append("no sale la sección 2 habiendo hipótesis")
    return anota("Las secciones vacías no se pintan", not malas), malas


def main():
    print(f"Fuentes: {motor.TITULO_R} para títulos, {motor.TEXTO_R} para texto"
          + ("" if motor.CON_FUENTES_DEL_PROTOCOLO else
             "  (NO son las del protocolo: falta instalar packages.txt)"))
    print(f"Caja de texto: {motor.ANCHO_UTIL / 72 * 25.4:.1f} mm\n")

    inicio = time.time()
    fallos = []
    for nombre, funcion in PRUEBAS:
        ok, malas = funcion()
        if not ok:
            fallos.append((nombre, malas))

    print(f"\n{len(RESUMEN) - len(fallos)} de {len(RESUMEN)} pruebas pasan"
          f"  ·  {time.time() - inicio:.1f}s")
    if fallos:
        print("\nNo pasan:")
        for nombre, malas in fallos:
            print(f"  · {nombre}")
            if DETALLE:
                for m in malas:
                    print(f"      {m}")
        if not DETALLE:
            print("\nRepite con --detalle para ver los casos concretos.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
