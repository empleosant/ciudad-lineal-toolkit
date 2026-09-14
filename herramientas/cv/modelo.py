"""
Llamadas a la IA del generador de CV.

    sugiere_funciones(cli, oficio)      funciones típicas de un oficio
    transcribe(cli, audio, mime)        lo grabado por el micrófono -> texto
    estructura(cli, texto)              trayectoria en texto libre -> fichas
    redacta_objetivo(cli, cv)           el objetivo profesional, en tres líneas

Regla: a la IA no se le manda ningún dato identificativo. Recibe oficios,
fechas y funciones; nunca el nombre, el teléfono ni el correo.
"""

import json
import re

from comun import ia

FUNCIONES = """Recibes el nombre de un oficio tras la etiqueta OCUPACIÓN. Devuelve
en 20-30 palabras las funciones habituales DE ESE OFICIO, en redacción corrida y sin
viñetas, para la sección de experiencia de un currículo.

REGLAS INNEGOCIABLES:
- Describe SOLO tareas propias del oficio indicado, en general.
- NO inventes datos de ninguna persona: ni empresas, ni años, ni cifras, ni logros,
  ni marcas concretas, ni responsabilidades de mando.
- No escribas en primera persona ni des por hecho que nadie hiciera todo esto.
- Empieza directamente por la tarea principal, sin "se encarga de" ni preámbulos.
- Si tras OCUPACIÓN no viene un oficio reconocible, responde exactamente: SIN OFICIO

No describas nunca tu propio papel ni el de quien te consulta: solo el oficio
que aparece tras la etiqueta. Devuelve el texto pelado, sin comillas."""

ESTRUCTURA = """Un orientador laboral te pasa, en texto libre y con las palabras de la
persona atendida, su trayectoria laboral y formativa. Conviértela en fichas.

Responde SOLO con este JSON:
{"experiencias":[{"puesto":"...","contexto":"...","desde":"...","hasta":"...","funciones":"..."}],
 "formacion":[{"titulo":"...","centro":"...","anio":"..."}]}

REGLAS:
- "puesto": el nombre del oficio en singular y tipo oración ("Camarero de piso").
- "contexto": la empresa o el tipo de empresa, tal como lo diga el texto. Si no lo dice, "".
- "desde" y "hasta": años de cuatro cifras si aparecen; "actualmente" si sigue; si no, "".
- "funciones": las tareas que el texto describa, en redacción corrida, 1-3 líneas. Si no describe ninguna, "".
- NO inventes nada que el texto no diga: ni fechas, ni empresas, ni funciones, ni títulos.
- Una experiencia por puesto distinto. Si el texto no menciona formación, "formacion": [].
- Español con acentuación correcta."""

OBJETIVO = """Redacta el OBJETIVO PROFESIONAL que cierra el apartado «Otros datos de
interés» de un currículo, a partir de los datos que recibes (puestos, años,
funciones, formación e intereses). Es UNA sola frase o dos, en primera persona,
de entre 25 y 40 palabras: tiene que caber en tres líneas.

Modelo de tono: «Mi objetivo profesional está enfocado hacia trabajos en las áreas
de comercio y atención al cliente, en las que cuento con amplia experiencia
profesional e interés por seguir desempeñándome profesionalmente.»

REGLAS:
- Nombra las áreas o sectores hacia los que se dirige la persona. Si los datos
  declaran un interés o un cambio de sector, ese manda; si no, la experiencia.
- Usa SOLO lo que hay en los datos. No inventes años, logros ni cualidades.
- Sin viñetas, sin título, sin comillas. Devuelve la frase pelada."""


def sugiere_funciones(cli, oficio, motivo=""):
    """Propone funciones típicas del puesto. NO son las de la persona.

    Es un punto de partida para que quien no sabe redactar tenga vocabulario,
    no una descripción de lo que hizo nadie. Va a un campo editable a propósito:
    la persona tiene que quitar lo que no hizo antes de que entre en su CV.
    """
    oficio = (oficio or "").strip()
    if len(oficio) < 3 or cli is None:
        return ""
    peticion = f"OCUPACIÓN: {oficio}"
    if motivo:
        peticion += f"\nContexto: {motivo}"
    try:
        salida = ia.genera(cli, FUNCIONES, peticion, max_tokens=300).strip('"')
        return "" if salida.upper().startswith("SIN OFICIO") else salida
    except Exception:  # noqa: BLE001
        return ""


def transcribe(cli, audio, mime="audio/wav"):
    """(texto, error). Si falla, texto vacío y el motivo en `error`."""
    if cli is None:
        return "", "No hay conexión con la IA."
    try:
        return ia.transcribe(cli, audio, mime), ""
    except Exception as e:  # noqa: BLE001
        return "", f"{type(e).__name__}: {e}"


def _json(bruto):
    texto = re.sub(r"^```(?:json)?|```$", "", (bruto or "").strip(), flags=re.MULTILINE)
    try:
        return json.loads(texto)
    except Exception:  # noqa: BLE001
        bloque = re.search(r"\{.*\}", texto, re.S)
        try:
            return json.loads(bloque.group()) if bloque else {}
        except Exception:  # noqa: BLE001
            return {}


def estructura(cli, texto):
    """(experiencias, formacion) como listas de diccionarios, o ([], []) si falla."""
    if cli is None or len((texto or "").strip()) < 10:
        return [], []
    try:
        datos = _json(ia.genera(cli, ESTRUCTURA, texto.strip(), json=True))
    except Exception:  # noqa: BLE001
        return [], []

    def limpia(lista, campos):
        salida = []
        for x in lista if isinstance(lista, list) else []:
            if not isinstance(x, dict):
                continue
            ficha = {c: str(x.get(c, "") or "").strip() for c in campos}
            if any(ficha.values()):
                salida.append(ficha)
        return salida

    return (
        limpia(datos.get("experiencias"), ("puesto", "contexto", "desde", "hasta", "funciones")),
        limpia(datos.get("formacion"), ("titulo", "centro", "anio")),
    )


def redacta_objetivo(cli, cv):
    """El objetivo profesional, o "" si falla. No manda datos identificativos."""
    if cli is None:
        return ""
    lineas = []
    for e in cv.get("experiencias", []):
        p = e.get("puesto") or e.get("denominacion") or ""
        if p:
            fechas = " - ".join(x for x in (e.get("desde"), e.get("hasta")) if x)
            lineas.append(f"- {p}" + (f" ({fechas})" if fechas else "")
                          + (f": {e['funciones']}" if e.get("funciones") else ""))
    for f in cv.get("formacion", []):
        if f.get("titulo"):
            lineas.append(f"- Formación: {f['titulo']}" + (f" ({f['anio']})" if f.get("anio") else ""))
    for rotulo, clave in (("Otros datos e intereses", "otros"), ("Disponibilidad", "disponibilidad")):
        if cv.get(clave):
            lineas.append(f"- {rotulo}: {cv[clave]}")
    if not lineas:
        return ""
    try:
        return ia.genera(cli, OBJETIVO, "\n".join(lineas), max_tokens=300).strip('"')
    except Exception:  # noqa: BLE001
        return ""
