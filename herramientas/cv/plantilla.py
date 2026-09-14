"""
El currículo sobre el modelo de la oficina (plantillas/Modelo_CV.docx).

El modelo es la fuente de verdad: se abre, se toman sus párrafos como
prototipos (nombre, contacto, cabecera azul, sector, experiencia, empresa,
funciones, formación, otros datos), se vacía el cuerpo y se vuelve a
rellenar copiando esos prototipos con el texto de la persona. Así el Word
que sale conserva estilos, fuentes (Trebuchet MS), colores, viñetas y
márgenes exactamente como el modelo.

UNA PÁGINA SIEMPRE. Aquí no hay Word para medir, así que se estima la
altura del documento con métricas de fuente y se reduce el tamaño de
letra (todo a la vez, proporcionalmente) hasta que quepa. El orden de
sacrificios, decidido con la oficina:

    1. Se mantienen los bloques por sector y se baja la letra hasta el
       mínimo legible (FACTOR_LEGIBLE).
    2. Si no basta, se dejan fuera las experiencias más antiguas (las
       últimas de la lista), una a una, hasta MIN_EXPERIENCIAS.
    3. Solo si aun así no cabe, se quitan los rótulos de sector y se
       sigue bajando la letra hasta FACTOR_MINIMO.

`cv["todas_experiencias"]` salta el paso 2: entran todas aunque la
letra tenga que bajar más.

    genera(cv) -> (bytes del .docx, decisión)
    decide(cv) -> decisión: {"bloques", "factor", "con_sectores", "omitidas"}
"""

import copy
import io
import math
import os

from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from PIL import ImageFont

from herramientas.cv import motor

PLANTILLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plantillas", "Modelo_CV.docx")

# Índices de los párrafos-prototipo dentro del modelo.
P_NOMBRE, P_CONTACTO, P_CABECERA, P_SECTOR = 0, 1, 4, 5
P_EXPERIENCIA, P_EMPRESA, P_FUNCIONES, P_FORMACION, P_OTROS = 6, 7, 8, 18, 21

# Página A4 con márgenes de 1 cm, en puntos.
ANCHO_UTIL = (11906 - 567 * 2) / 20
ALTO_UTIL = (16838 - 567 * 2) / 20
MARGEN_SEGURIDAD = 14        # puntos que se dejan libres al pie
FACTOR_MINIMO = 0.55
FACTOR_LEGIBLE = 0.85        # por debajo de esto se empieza a sacrificar contenido
MIN_EXPERIENCIAS = 3         # nunca se dejan fuera experiencias por debajo de esto
ALTURA_LINEA = 1.17          # Trebuchet MS: ascendente + descendente, en ems
ANCHO_TREBUCHET = 0.92       # DejaVu Sans es más ancha; se corrige
HOLGURA_AJUSTE = 1.06        # el ajuste por palabras desperdicia algo de línea

_FUENTES = {
    False: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    True: "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}
_cache_fuentes = {}


def _fuente(negrita, pt):
    clave = (negrita, round(pt, 1))
    if clave not in _cache_fuentes:
        try:
            _cache_fuentes[clave] = ImageFont.truetype(_FUENTES[negrita], size=max(1, round(pt * 10)) / 10)
        except Exception:  # noqa: BLE001
            _cache_fuentes[clave] = None
    return _cache_fuentes[clave]


def _ancho_texto(texto, pt, negrita=False):
    f = _fuente(negrita, pt)
    if f is None:
        return len(texto) * pt * 0.52
    return f.getlength(texto) * ANCHO_TREBUCHET


# ---------------------------------------------------------------------------
# El contenido, como lista de bloques independientes del formato
# ---------------------------------------------------------------------------

def _bloques(cv, con_sectores, omitir=0):
    """[(tipo, datos)] en el orden del documento. `omitir`: cuántas experiencias
    se dejan fuera por el final de la lista (las más antiguas)."""
    b = [("nombre", (cv.get("nombre") or "Nombre Apellido1 Apellido2").strip())]
    if cv.get("telefono"):
        b.append(("contacto", f"Tlf.: {cv['telefono'].strip()}"))
    if cv.get("email"):
        b.append(("contacto", f"Email: {cv['email'].strip()}"))
    if cv.get("localidad"):
        b.append(("contacto", cv["localidad"].strip()))

    exps = list(cv.get("experiencias", []))
    if omitir:
        exps = exps[:len(exps) - omitir]
    if exps:
        b.append(("cabecera", "EXPERIENCIA LABORAL"))
        agrupadas = motor.experiencias_agrupadas(exps) if con_sectores else [(None, e) for e in exps]
        for sector, e in agrupadas:
            if sector:
                b.append(("sector", sector))
            b.append(("experiencia", (motor.titulo_experiencia(e), _periodo_partes(e))))
            if e.get("contexto"):
                b.append(("empresa", f"Empresa: {e['contexto'].strip().rstrip('.')}."))
            if e.get("funciones"):
                b.append(("funciones", f"Funciones: {e['funciones'].strip()}"))

    if cv.get("formacion"):
        b.append(("cabecera", "FORMACIÓN ACADÉMICA / COMPLEMENTARIA"))
        for f in cv["formacion"]:
            if f.get("titulo"):
                b.append(("formacion", (f["titulo"].strip(), (f.get("centro") or "").strip(),
                                        (f.get("anio") or "").strip())))

    otros = []
    if cv.get("idiomas"):
        otros.append(f"Idiomas: {cv['idiomas'].strip()}")
    if cv.get("informatica"):
        otros.append(f"Informática: {cv['informatica'].strip()}")
    if cv.get("permiso"):
        otros.append(cv["permiso"].strip())
    if cv.get("disponibilidad"):
        otros.append(cv["disponibilidad"].strip())
    for linea in (cv.get("otros") or "").splitlines():
        if linea.strip():
            otros.append(linea.strip())
    if cv.get("objetivo"):
        # Siempre el último punto: hacia dónde se dirige la persona, en tres líneas.
        otros.append(cv["objetivo"].strip())
    if otros:
        b.append(("cabecera", "OTROS DATOS DE INTERÉS"))
        for o in otros:
            b.append(("otros", o if o.endswith((".", "!", "?")) else o + "."))
    return b


def _periodo_partes(e):
    """("(6 años - ", "2016-2022", ")") o ("", "", "") si no hay fechas."""
    desde, hasta = (e.get("desde") or "").strip(), (e.get("hasta") or "").strip()
    if not (desde or hasta):
        return ("", "", "")
    rango = "-".join(x for x in (desde, hasta) if x)
    a1, a2 = motor.anio(desde), motor.anio(hasta)
    if a1 and a2 and a2 >= a1:
        n = max(1, a2 - a1)
        return (f"({n} año{'s' if n != 1 else ''} - ", rango, ")")
    return ("(", rango, ")")


# ---------------------------------------------------------------------------
# Estimación de altura (para decidir el factor de escala)
# ---------------------------------------------------------------------------

# Por tipo de bloque: (tamaño pt, negrita, sangría izquierda pt, espacio antes,
#                      espacio después, interlineado múltiple).
# Tamaños y sangrías son los del modelo. Espacios e interlineado van algo
# más holgados que en el modelo (que los tenía a 0,9-0,95 y sin hueco entre
# bloques) para que se lea más claro; se aplican al Word en `_aire`.
_METRICA = {
    "nombre": (27, True, 0, 0, 0, 1.0),
    "contacto": (19, False, 35.45, 0, 0, 1.15),
    "cabecera": (20, False, 0, 9, 3, 1.15),
    "cabecera1": (20, False, 0, 0, 3, 1.15),   # la primera, pegada al contacto
    "sector": (20, False, 2.85, 6, 4, 1.0),
    "experiencia": (18, True, 38.85, 6, 0, 1.05),
    "empresa": (16, False, 70.9, 0, 0, 1.05),
    "funciones": (16, False, 35.45, 0, 0, 1.05),
    "formacion": (16, False, 36, 6, 0, 1.0),
    "otros": (16, False, 33.15, 6, 0, 1.05),
}


def _texto_plano(tipo, datos):
    if tipo == "experiencia":
        titulo, (a, fechas, c) = datos
        return f"{titulo} {a}{fechas}{c}"
    if tipo == "formacion":
        titulo, centro, anio = datos
        return " ".join(x for x in (f"{titulo} –", f"{centro},", f"{anio}.") if x.strip(" –,."))
    return datos


def _altura(bloques, factor):
    total = 0.0
    for tipo, datos in bloques:
        pt, negrita, sangria, antes, despues, mult = _METRICA[tipo]
        pt *= factor
        ancho = ANCHO_UTIL - sangria
        texto = _texto_plano(tipo, datos)
        lineas = 0
        for parrafo in texto.split("\n") or [""]:
            lineas += max(1, math.ceil(_ancho_texto(parrafo, pt, negrita) * HOLGURA_AJUSTE / ancho))
        total += lineas * pt * ALTURA_LINEA * mult + antes + despues
    return total


def _factor_que_cabe(bloques):
    f = 1.0
    while f > FACTOR_MINIMO:
        if _altura(bloques, f) <= ALTO_UTIL - MARGEN_SEGURIDAD:
            return f
        f = round(f - 0.02, 2)
    return FACTOR_MINIMO


def decide(cv):
    """La mejor combinación para una página, siguiendo el orden de sacrificios.

    Devuelve {"bloques", "factor", "con_sectores", "omitidas"}; `omitidas`
    son los títulos de las experiencias que se han dejado fuera.
    """
    exps = cv.get("experiencias", [])

    def resultado(bloques, factor, con_sectores, omitir):
        return {
            "bloques": bloques, "factor": factor,
            "con_sectores": con_sectores and any(t == "sector" for t, _ in bloques),
            "omitidas": [motor.titulo_experiencia(e) for e in exps[len(exps) - omitir:]] if omitir else [],
        }

    # 1. Todo, con sectores, letra hasta el mínimo legible.
    con = _bloques(cv, True)
    f_con = _factor_que_cabe(con)
    if f_con >= FACTOR_LEGIBLE:
        return resultado(con, f_con, True, 0)

    # 2. Fuera las experiencias más antiguas, una a una, con sectores.
    omitir = 0
    if not cv.get("todas_experiencias"):
        while len(exps) - omitir > MIN_EXPERIENCIAS:
            omitir += 1
            con_menos = _bloques(cv, True, omitir)
            f_menos = _factor_que_cabe(con_menos)
            if f_menos >= FACTOR_LEGIBLE:
                return resultado(con_menos, f_menos, True, omitir)
        con, f_con = _bloques(cv, True, omitir), _factor_que_cabe(_bloques(cv, True, omitir))

    # 3. Último recurso: sin rótulos de sector, y la letra hasta donde haga falta.
    sin = _bloques(cv, False, omitir)
    f_sin = _factor_que_cabe(sin)
    if f_sin > f_con:
        return resultado(sin, f_sin, False, omitir)
    return resultado(con, f_con, True, omitir)


# ---------------------------------------------------------------------------
# Construcción del Word a partir de los prototipos del modelo
# ---------------------------------------------------------------------------

def _run_como(proto_run, texto, con_tab=False):
    r = copy.deepcopy(proto_run)
    for hijo in list(r):
        if hijo.tag != qn("w:rPr"):
            r.remove(hijo)
    if con_tab:
        etree.SubElement(r, qn("w:tab"))
    t = etree.SubElement(r, qn("w:t"))
    t.text = texto
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return r


def _parrafo_como(proto, runs_texto, con_tab=False):
    """Copia el prototipo y sustituye sus runs por (prototipo_run, texto)."""
    p = copy.deepcopy(proto)
    for hijo in list(p):
        if hijo.tag != qn("w:pPr"):
            p.remove(hijo)
    primero = True
    for proto_run, texto in runs_texto:
        if texto == "":
            continue
        p.append(_run_como(proto_run, texto, con_tab and primero))
        primero = False
    return p


def _runs(proto):
    return proto.findall(qn("w:r"))


def _escala(elemento, factor):
    """Multiplica tamaños de letra y espacios entre párrafos que cuelguen del elemento."""
    for tag in ("w:sz", "w:szCs"):
        for sz in elemento.iter(qn(tag)):
            v = sz.get(qn("w:val"))
            if v and v.isdigit():
                sz.set(qn("w:val"), str(max(8, round(int(v) * factor))))
    for sp in elemento.iter(qn("w:spacing")):
        for atributo in ("w:before", "w:after"):
            v = sp.get(qn(atributo))
            if v and v.isdigit():
                sp.set(qn(atributo), str(round(int(v) * factor)))


def _aire(p, tipo):
    """Aplica al párrafo el espacio antes/después y el interlineado de _METRICA."""
    _, _, _, antes, despues, mult = _METRICA[tipo]
    if tipo == "cabecera1":
        mult = _METRICA["cabecera"][5]
    ppr = p.find(qn("w:pPr"))
    sp = ppr.find(qn("w:spacing"))
    if sp is None:
        sp = etree.SubElement(ppr, qn("w:spacing"))
    sp.set(qn("w:before"), str(round(antes * 20)))
    sp.set(qn("w:after"), str(round(despues * 20)))
    sp.set(qn("w:line"), str(round(mult * 240)))
    sp.set(qn("w:lineRule"), "auto")
    return p


def _funciones_con_sangria(p):
    """Sustituye el truco de tabuladores del modelo por una sangría izquierda fija.

    Todas las líneas de «Funciones:» empiezan a la misma altura que la
    etiqueta (1,25 cm), que es como quedó en la corrección a mano del modelo.
    """
    ppr = p.find(qn("w:pPr"))
    for tabs in ppr.findall(qn("w:tabs")):
        ppr.remove(tabs)
    ind = ppr.find(qn("w:ind"))
    if ind is None:
        ind = etree.SubElement(ppr, qn("w:ind"))
    for k in list(ind.attrib):
        del ind.attrib[k]
    ind.set(qn("w:left"), "709")
    return p


def genera(cv):
    """El currículo en Word sobre el modelo. (bytes, decisión de `decide`)."""
    decision = decide(cv)
    bloques, factor = decision["bloques"], decision["factor"]
    doc = Document(PLANTILLA)
    cuerpo = doc.element.body
    protos = [copy.deepcopy(p._p) for p in doc.paragraphs]
    for p in list(cuerpo):
        if p.tag == qn("w:p"):
            cuerpo.remove(p)
    sect = cuerpo.find(qn("w:sectPr"))

    primera_cabecera = [True]

    def anade(p, tipo):
        if tipo == "cabecera" and primera_cabecera[0]:
            tipo, primera_cabecera[0] = "cabecera1", False
        _aire(p, tipo)
        if sect is not None:
            sect.addprevious(p)
        else:
            cuerpo.append(p)

    r_nombre = _runs(protos[P_NOMBRE])[0]
    r_contacto = _runs(protos[P_CONTACTO])[0]
    r_cabecera = _runs(protos[P_CABECERA])[0]
    r_sector = _runs(protos[P_SECTOR])[0]
    rx = _runs(protos[P_EXPERIENCIA])          # negrita, negrita, normal, cursiva, normal
    r_empresa = _runs(protos[P_EMPRESA])[0]
    r_funciones = _runs(protos[P_FUNCIONES])[0]
    rf = _runs(protos[P_FORMACION])            # negrita, normal, cursiva, normal
    r_otros = _runs(protos[P_OTROS])[0]

    for tipo, datos in bloques:
        if tipo == "nombre":
            anade(_parrafo_como(protos[P_NOMBRE], [(r_nombre, datos)]), tipo)
        elif tipo == "contacto":
            anade(_parrafo_como(protos[P_CONTACTO], [(r_contacto, datos)], con_tab=True), tipo)
        elif tipo == "cabecera":
            anade(_parrafo_como(protos[P_CABECERA], [(r_cabecera, datos)]), tipo)
        elif tipo == "sector":
            anade(_parrafo_como(protos[P_SECTOR], [(r_sector, datos)]), tipo)
        elif tipo == "experiencia":
            titulo, (a, fechas, c) = datos
            anade(_parrafo_como(protos[P_EXPERIENCIA], [
                (rx[0], titulo), (rx[1], " " if fechas else ""), (rx[2], a), (rx[3], fechas), (rx[4], c),
            ]), tipo)
        elif tipo == "empresa":
            anade(_parrafo_como(protos[P_EMPRESA], [(r_empresa, datos)]), tipo)
        elif tipo == "funciones":
            anade(_funciones_con_sangria(_parrafo_como(protos[P_FUNCIONES], [(r_funciones, datos)])), tipo)
        elif tipo == "formacion":
            titulo, centro, anio = datos
            cola = f" {anio}." if anio else ("." if not centro else "")
            anade(_parrafo_como(protos[P_FORMACION], [
                (rf[0], f"{titulo} –" if (centro or anio) else titulo),
                (rf[1], " " if centro else ""), (rf[2], f"{centro}," if (centro and anio) else centro),
                (rf[3], cola),
            ]), tipo)
        elif tipo == "otros":
            anade(_parrafo_como(protos[P_OTROS], [(r_otros, datos)]), tipo)

    if factor < 1.0:
        _escala(cuerpo, factor)
        try:
            _escala(doc.part.numbering_part.element, factor)   # las viñetas también
        except Exception:  # noqa: BLE001
            pass

    salida = io.BytesIO()
    doc.save(salida)
    return salida.getvalue(), decision
