"""
Batería del documento de preparación de sesión.

El protocolo pide dos páginas A4 y lo dice en serio: si el documento se va a
tres, deja de servir para lo que sirve, que es llevarlo impreso a la entrevista
y tenerlo delante. Aquí se comprueba midiendo el PDF, no mirándolo.

Lo que se prueba:

  · Que cabe en dos páginas, incluso con el contenido en el tope de lo que el
    prompt le permite devolver a la IA, y aunque la IA se pase de largo.
  · Que no encoge la letra más de la cuenta para conseguirlo.
  · Que la segunda página cierra con un hueco en blanco para tomar notas
    durante la cita, y que cada bloque del punto 4 lleva su guion.
  · Que el papel sale sin firma, sin logotipo, sin mención institucional y con
    los metadatos sin autoría.
  · Que la frase de cautela va siempre y no se duplica.
  · Que el texto ajeno se escapa antes de convertirlo en marcado.
  · Que una ficha incompleta o rara no revienta.
  · Que el expediente va y vuelve entero, y que uno estropeado no deja la
    pantalla sin arrancar.
  · Que la matriz se lee entera de su documento y que la hoja de calibración
    sale con las columnas de la hoja.

Las fichas de prueba son inventadas, pero con la misma forma y la misma
densidad de texto que los documentos reales: con palabras largas de relleno el
texto ocupa casi el doble y la medida no vale para nada.

USO
    python informes.py              todas las pruebas
    python informes.py --detalle    enseña lo que falla, caso a caso

No llama a la IA ni gasta cuota. Tarda unos segundos: las fichas
desbordadas obligan al motor a recorrer todo el ajuste.
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


def desbordada(veces=3):
    """Mucho más de lo que el prompt permite, para probar el tope de dos hojas.

    El doble del máximo todavía entra encogiendo la letra; con el triple hay
    que recortar, y el motor recorta antes que abrir una tercera página.
    """
    f = tope()
    for lista in ("preguntas", "acciones", "trayectoria"):
        f[lista] = f[lista] * veces
    f["hipotesis"] = pal(110 * veces)
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

    return " ".join(recorre(motor._flujo(ficha, 1.0, motor._Notas())))


# ---------------------------------------------------------------------------
# Las pruebas
# ---------------------------------------------------------------------------

@prueba("Cabe en dos páginas")
def cabe():
    casos = [("en el tope del prompt", tope(), 2),
             ("del tamaño corriente", corriente(), 2),
             ("con caracteres raros", RARA, 2),
             ("sólo con la entradilla", {"entradilla": "Perfil."}, 1),
             ("completamente vacía", {}, 1),
             # Dos páginas es condición: si la IA se pasa de largo, el motor
             # encoge y, en último extremo, recorta. Nunca una tercera hoja.
             ("al doble del tope", desbordada(2), 2),
             ("al triple del tope", desbordada(3), 2)]
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


@prueba("La segunda página cierra con hueco de notas")
def hueco_de_notas():
    """El blanco del final es el sitio para escribir durante la cita.

    No lleva rayas ni puntos —el documento no se rellena a mano en su sitio—
    pero tiene que ser un hueco de verdad: si no llega al mínimo, el motor
    encoge la letra hasta que llega.
    """
    minimo = motor.NOTAS_MINIMO / motor.mm
    malas = []
    for etiqueta, ficha in (("del tamaño corriente", corriente()),
                            ("en el tope del prompt", tope())):
        _, d = motor.documento_pdf(ficha, con_detalle=True)
        if d["hueco"] < motor.NOTAS_MINIMO:
            malas.append(f"{etiqueta}: {d['hueco'] / motor.mm:.0f} mm de hueco, "
                         f"mínimo {minimo:.0f} mm")
    if "Notas de la cita" not in texto_del_documento(corriente()):
        malas.append("no sale la sección 6 habiendo segunda página")
    # En un folio no hay blanco que aprovechar: el recuadro no se pinta.
    if "Notas de la cita" in texto_del_documento({"entradilla": "Perfil."}):
        malas.append("sale la sección 6 en un documento de una página")
    return anota("La segunda página cierra con hueco de notas", not malas,
                 f"mínimo del motor: {minimo:.0f} mm"), malas


@prueba("Cada bloque del punto 4 lleva su guion")
def guiones():
    """Se busca de un vistazo mientras se habla: el guion marca dónde empieza."""
    from reportlab.platypus import Paragraph

    ficha = {"preguntas": [{"rotulo": f"Bloque {i}", "texto": pal(30)}
                           for i in range(6)]}
    bloques = [e for e in motor._flujo(ficha, 1.0)
               if isinstance(e, Paragraph) and "Bloque" in e.text]
    malas = []
    if len(bloques) != 6:
        malas.append(f"salen {len(bloques)} bloques de 6")
    sin = [b for b in bloques if getattr(b, "bulletText", None) != "–"]
    if sin:
        malas.append(f"{len(sin)} bloques sin guion")
    return anota("Cada bloque del punto 4 lleva su guion", not malas,
                 f"{len(bloques) - len(sin)}/{len(bloques)} bloques"), malas


@prueba("El expediente va y vuelve entero")
def expediente_ida_y_vuelta():
    """Sin esto no hay continuidad entre la preparación y la cita."""
    import json
    lleno = {c: f"valor de {c}" for c in motor.CAMPOS_EXPEDIENTE}
    lleno["ficha"] = {"rasgo": "comercio_limpieza", "entradilla": "Perfil."}
    # Los campos con vocabulario cerrado se rellenan con un valor suyo de verdad:
    # cualquier otra cosa la descarta `lee_expediente`, y con razón.
    for campo, vocabulario in motor.VOCABULARIOS.items():
        lleno[campo] = vocabulario[-1]
    vuelta, error = motor.lee_expediente(motor.expediente(lleno))
    malas = [f"al releer: {error}"] if error else []
    malas += [f"«{c}» vuelve como {vuelta.get(c)!r}, se guardó {lleno[c]!r}"
              for c in motor.CAMPOS_EXPEDIENTE if vuelta.get(c) != lleno[c]]
    # Lo que no es del expediente no se cuela de vuelta.
    colado, _ = motor.lee_expediente(
        json.dumps({"notas": "ok", "loquesea": "no soy del expediente"}).encode())
    if "loquesea" in colado:
        malas.append("se cuela un campo que no es del expediente")
    return anota("El expediente va y vuelve entero", not malas,
                 f"{len(motor.CAMPOS_EXPEDIENTE)} campos"), malas


@prueba("Un expediente estropeado no tumba la pantalla")
def expediente_roto():
    """Es un archivo suelto en el disco: puede llegar editado o a medio copiar.

    Lo que no sea de su tipo tiene que quedarse fuera, porque luego se le pasa
    tal cual al widget que lo espera y ahí ya no hay red.
    """
    import json
    casos = [
        ("no es JSON", b"{roto", None),
        ("no es un objeto", b"[1, 2, 3]", None),
        ("versión del futuro", json.dumps({"version": 99, "notas": "x"}).encode(), None),
        ("número donde va texto", json.dumps({"cv": 12345, "notas": "x"}).encode(), "12345"),
        ("lista donde va texto", json.dumps({"cv": ["a"], "notas": "x"}).encode(), None),
        ("booleano", json.dumps({"cv": True, "notas": "x"}).encode(), None),
        ("ficha que no es objeto", json.dumps({"ficha": "no", "notas": "x"}).encode(), None),
        ("motivación inventada", json.dumps({"motivacion": "Ninguna", "notas": "x"}).encode(), None),
    ]
    malas = []
    for etiqueta, crudo, esperado_cv in casos:
        try:
            datos, error = motor.lee_expediente(crudo)
        except Exception as e:  # noqa: BLE001
            malas.append(f"{etiqueta}: revienta con {type(e).__name__}")
            continue
        if not isinstance(datos, dict):
            malas.append(f"{etiqueta}: no devuelve un diccionario")
            continue
        if error and datos:
            malas.append(f"{etiqueta}: devuelve datos y error a la vez")
        # Todo lo que sobreviva tiene que ser del tipo que espera la pantalla.
        for campo, valor in datos.items():
            tipo = dict if campo == "ficha" else str
            if not isinstance(valor, tipo):
                malas.append(f"{etiqueta}: «{campo}» sale como {type(valor).__name__}")
        if esperado_cv is not None and datos.get("cv") != esperado_cv:
            malas.append(f"{etiqueta}: «cv» sale {datos.get('cv')!r}, esperado {esperado_cv!r}")
        if datos.get("motivacion") and datos["motivacion"] not in motor.MOTIVACIONES:
            malas.append(f"{etiqueta}: motivación fuera de vocabulario")
    return anota("Un expediente estropeado no tumba la pantalla", not malas,
                 f"{len(casos) - len(malas)}/{len(casos)} casos"), malas


@prueba("La matriz se lee entera del documento")
def matriz():
    """El .md es la fuente: si cambia el formato, esto lo canta.

    Las doce casillas salen de sus encabezados. Si alguien reescribe el
    documento y se lleva por delante uno, el desplegable de la pantalla pierde
    esa casilla en silencio y la hoja de calibración deja de poder registrarla.
    """
    malas = []
    if len(motor.CASILLAS) != 12:
        malas.append(f"se leen {len(motor.CASILLAS)} casillas, tendrían que ser 12")
    esperados = [f"{letra}{numero}" for letra in "ABCD" for numero in "123"]
    if list(motor.CODIGOS) != esperados:
        malas.append(f"los códigos salen {list(motor.CODIGOS)}")
    for codigo, nombre in motor.CASILLAS:
        if not nombre.strip():
            malas.append(f"{codigo} no tiene nombre")
    # Cada ficha tiene que traer su intervención y su riesgo: el prompt los usa.
    for pieza in ("Intervención central", "Riesgo típico", "Banda transversal",
                  "Campos que filtran recursos"):
        if pieza not in motor.MATRIZ:
            malas.append(f"falta «{pieza}» en lo que se le pasa a la IA")
    if motor.MATRIZ.count("**Riesgo típico.**") != 12:
        malas.append(f"hay {motor.MATRIZ.count('**Riesgo típico.**')} riesgos típicos, "
                     "tendría que haber uno por casilla")
    # Lo de después de la marca de corte no viaja al modelo.
    if "Hoja de calibración" in motor.MATRIZ:
        malas.append("la hoja de calibración se le está pasando a la IA")
    return anota("La matriz se lee entera del documento", not malas,
                 f"{len(motor.CASILLAS)} casillas · {len(motor.MATRIZ)} caracteres"), malas


@prueba("La hoja de calibración sale con sus columnas")
def calibracion():
    fila = motor.fila_calibracion({
        "casilla": "A1 · Problema de canal", "motivacion": "Desgastada",
        "encaje": "A medias", "referencia": "Cita del 15",
        "observaciones": "Pesa como B1."}).decode("utf-8-sig")
    cabecera, datos = fila.strip().splitlines()
    malas = []
    if cabecera != "Nº;Referencia del caso;Casilla;Motivación;¿Encaja? Observaciones":
        malas.append(f"la cabecera sale «{cabecera}»")
    campos = datos.split(";")
    if campos[0] != "":
        malas.append("el Nº tendría que ir en blanco: lo lleva la hoja")
    if campos[2] != "A1":
        malas.append(f"la casilla sale «{campos[2]}», se esperaba el código a secas")
    if campos[3] != "D":
        malas.append(f"la motivación sale «{campos[3]}», se esperaba la letra")
    if "A medias" not in campos[4] or "Pesa como B1." not in campos[4]:
        malas.append(f"encaje y observaciones no van juntos: «{campos[4]}»")
    # Sin nada anotado, la fila sale vacía pero con sus cinco columnas.
    vacia = motor.fila_calibracion({}).decode("utf-8-sig").strip().splitlines()[1]
    if vacia != ";;;;":
        malas.append(f"la fila vacía sale «{vacia}»")
    return anota("La hoja de calibración sale con sus columnas", not malas), malas


@prueba("Los prompts se montan enteros")
def prompts_enteros():
    """Las piezas compartidas se interpolan de verdad en los dos prompts.

    Van dentro de f-strings con llaves por todas partes (el JSON de ejemplo):
    una llave mal escapada deja el prompt sin la matriz o sin las reglas de
    rigor, y no se nota hasta que la IA devuelve algo raro.
    """
    from herramientas.informes import modelo
    malas = []
    for nombre, prompt in (("ANALISTA", modelo.ANALISTA),
                           ("PREPARACION", modelo.PREPARACION)):
        for pieza, etiqueta in ((motor.MATRIZ, "la matriz del documento"),
                                (modelo.RIGOR, "el rigor")):
            if not pieza or pieza not in prompt:
                malas.append(f"{nombre}: no lleva {etiqueta}")
        if "{" in prompt.replace("{{", "").replace("}}", "") and '{"rasgo"' not in prompt:
            malas.append(f"{nombre}: queda una llave sin sustituir")
    # El ejemplo de respuesta del documento tiene que seguir siendo JSON válido.
    import json
    import re
    bloque = re.search(r'\{"rasgo".*?"riesgo":\s*\{[^}]*\}\}', modelo.PREPARACION, re.S)
    if not bloque:
        malas.append("PREPARACION: no se encuentra el ejemplo de respuesta")
    else:
        try:
            json.loads(bloque.group())
        except Exception as e:  # noqa: BLE001
            malas.append(f"PREPARACION: el ejemplo de respuesta no es JSON válido ({e})")
    return anota("Los prompts se montan enteros", not malas), malas


@prueba("Lo acordado llega al prompt")
def acordado():
    texto = motor.lo_acordado({
        "objetivo1": "Camarera de piso", "objetivo2": "", "zona": "Ciudad Lineal",
        "adjuntos": "", "motivacion": "Desgastada"})
    malas = []
    if "Camarera de piso" not in texto:
        malas.append("falta el objetivo principal")
    if "Ciudad Lineal" not in texto:
        malas.append("falta la zona, que es la que decide las empresas")
    if "desgastada" not in texto:
        malas.append("falta la motivación")
    if "Objetivo secundario" in texto or "Va adjunto" in texto:
        malas.append("se cuela una etiqueta de un campo vacío")
    if motor.lo_acordado({}) != "":
        malas.append("sin datos no devuelve cadena vacía")
    return anota("Lo acordado llega al prompt", not malas), malas


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
