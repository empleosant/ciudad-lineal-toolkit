"""
Motor del codificador SISPE. Python puro: no importa Streamlit.

Carga el catálogo y el vocabulario al importarse (Python solo lo hace una
vez por proceso) y ofrece:

    busca(consulta, ...)     puntúa el catálogo contra un texto libre
    verifica(lista)          filtra lo que propone la IA contra el catálogo
    interpreta(bruto)        convierte la respuesta JSON de la IA en tarjetas
    raiz(palabra)            el lematizador mínimo

Lo prueban `pruebas/evaluar.py` y `pruebas/estres.py` importándolo tal cual.
Antes de tocar `raiz` o `busca`:

    python pruebas/evaluar.py && python pruebas/estres.py
"""

import json
import math
import os
import re
from collections import defaultdict
from difflib import SequenceMatcher

from comun.texto import normaliza

DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
CATALOGO = os.path.join(DATOS, "ocupaciones_sispe_ultraligero.txt")
AMPLIADO = os.path.join(DATOS, "terminos_ampliados.txt")
VOCABULARIO = os.path.join(DATOS, "vocabulario.json")

VACIAS_MINIMAS = {
    "de", "del", "la", "el", "los", "las", "en", "y", "o", "con", "para",
    "por", "un", "una", "al", "sin", "que", "su", "general", "persona",
    "personas", "dame", "dime", "codigo", "puesto", "trabajo",
}


def carga_vocabulario(ruta=VOCABULARIO):
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            vacias = {normaliza(w) for w in datos.get("vacias", []) if w}
            sinonimos = {
                normaliza(k): str(v)
                for k, v in (datos.get("sinonimos") or {}).items() if k and v
            }
            if vacias or sinonimos:
                return vacias or set(VACIAS_MINIMAS), sinonimos
        except Exception:  # noqa: BLE001
            pass
    return set(VACIAS_MINIMAS), {}


NIVELES = {
    "10": "Dirección",
    "20": "Mandos intermedios",
    "30": "Jefes de equipo",
    "00": "Técnicos / Sin categoría",
    "70": "Auxiliares",
    "80": "Peones",
    "90": "Aprendices",
}


def raiz(w):
    """Lematizador mínimo: número, después sufijo de agente, después género.

    Las tres fases son INDEPENDIENTES a propósito. Si se juntan en una cadena
    elif, el plural y el singular de la misma palabra dejan de lematizar
    igual: "montadores" se queda en "montador" (solo se aplica la regla de
    plural) mientras que "montador" llega a "mont". El catálogo está en plural
    y el ciudadano escribe en singular, así que dejan de encontrarse. Se probó
    el 21/08/2026 y rompía 216 nombres de agente del catálogo.

    Tampoco conviene meter aquí participios (-ado, -ido): en este catálogo
    "cuidado", "montado" o "trasdosado" son sustantivos, no formas verbales, y
    recortarlos los confunde con "cuidador" y "montador".

    El gerundio (-ando, -iendo) se probó y no aporta: el pase de
    interpretación ya normaliza la consulta antes de la búsqueda local.

    Antes de tocar esta función:  python pruebas/evaluar.py && python pruebas/estres.py
    """
    if len(w) > 5 and w.endswith("es"):
        w = w[:-2]
    elif len(w) > 4 and w.endswith("s"):
        w = w[:-1]
    if len(w) > 5 and w.endswith("or"):
        w = w[:-2]
    if len(w) > 4 and w[-1] in "aoe":
        w = w[:-1]
    return w


VACIAS, SINONIMOS = carga_vocabulario()


def carga_indice(catalogo=CATALOGO, ampliado_ruta=AMPLIADO):
    if not os.path.exists(catalogo):
        return {"ok": False, "registros": []}

    ampliado = {}
    if os.path.exists(ampliado_ruta):
        with open(ampliado_ruta, "r", encoding="utf-8") as f:
            for linea in f:
                if ":" in linea:
                    cod, terms = linea.split(":", 1)
                    ampliado[cod.strip()] = terms.strip()

    registros, inv, inv_raiz = [], defaultdict(list), defaultdict(list)
    inv_extra = defaultdict(list)
    with open(catalogo, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if ":" not in linea:
                continue
            codigo, denom = linea.split(":", 1)
            tokens = [
                t for t in re.findall(r"\w+", normaliza(denom))
                if len(t) > 2 and t not in VACIAS
            ]
            propias = {raiz(t) for t in tokens}
            sueltas = {
                raiz(t)
                for t in re.findall(r"\w+", normaliza(ampliado.get(codigo.strip(), "")))
                if len(t) > 2 and t not in VACIAS
            }
            registros.append({
                "codigo": codigo.strip(),
                "denom": denom.strip(),
                "palabras": set(tokens),
                "raices": propias,
                "cabeza": {raiz(t) for t in tokens[:3]},
                "extra": sueltas - propias,
            })

    n = max(1, len(registros))
    for i, r in enumerate(registros):
        for w in r["palabras"]:
            inv[w].append(i)
        for w in r["raices"]:
            inv_raiz[w].append(i)
        for w in r["extra"]:
            inv_extra[w].append(i)

    trigramas = defaultdict(set)
    for w in inv_raiz:
        for j in range(len(w) - 2):
            trigramas[w[j:j + 3]].add(w)

    return {
        "ok": True,
        "registros": registros,
        "por_codigo": {r["codigo"]: r["denom"] for r in registros},
        "posicion": {r["codigo"]: i for i, r in enumerate(registros)},
        "inv": inv,
        "inv_raiz": inv_raiz,
        "idf": {w: math.log(1 + n / len(ix)) for w, ix in inv.items()},
        "idf_raiz": {w: math.log(1 + n / len(ix)) for w, ix in inv_raiz.items()},
        "inv_extra": inv_extra,
        "idf_extra": {w: math.log(1 + n / len(ix)) for w, ix in inv_extra.items()},
        "ampliado": len(ampliado),
        "trigramas": trigramas,
        "vocab_raiz": list(inv_raiz.keys()),
    }


IDX = carga_indice()


def parecidas(palabra, umbral=0.84, tope=3):
    posibles = set()
    for j in range(len(palabra) - 2):
        posibles |= IDX["trigramas"].get(palabra[j:j + 3], set())
    salida = []
    for c in posibles:
        if abs(len(c) - len(palabra)) > 3:
            continue
        r = SequenceMatcher(None, palabra, c).ratio()
        if r >= umbral:
            salida.append((r, c))
    salida.sort(reverse=True)
    return salida[:tope]


def busca(consulta, tope=20, grupos=None, lexico=None, refuerzos=None):
    """Puntúa el catálogo contra la consulta y devuelve (puntos, código, denominación).

    `lexico` son sinónimos aprendidos (clave -> expansión) y `refuerzos`
    correcciones de orden (código -> palabras). Los dos vienen del Gist
    compartido; sin ellos, la búsqueda funciona igual con el vocabulario base.
    """
    q = normaliza(consulta)
    terminos = {}
    cabezas = set()

    clausulas = [
        c.strip()
        for c in re.split(r"\s+(?:y|e|o|ademas|tambien)\s+", q)
        if c.strip()
    ]
    if not clausulas:
        clausulas = [q]

    for clausula in clausulas:
        contadas = 0
        for w in re.findall(r"\w+", clausula):
            if len(w) > 2 and w not in VACIAS and w not in terminos:
                contadas += 1
                if contadas == 1:
                    cabezas.add(raiz(w))
                terminos[w] = 1.0 if contadas <= 3 else 0.7

    palabras_q = set(re.findall(r"\w+", q))
    diccionario = dict(lexico or {})
    diccionario.update(SINONIMOS)
    for clave, expansion in diccionario.items():
        if (clave in palabras_q) if " " not in clave else (clave in q):
            for w in re.findall(r"\w+", normaliza(expansion)):
                terminos.setdefault(w, 0.85)
    if not terminos:
        return []

    originales = {raiz(w) for w, peso in terminos.items() if peso == 1.0}
    puntos, cubierto = defaultdict(float), defaultdict(set)

    def suma(i, valor, termino):
        puntos[i] += valor
        cubierto[i].add(termino)

    for w, peso in terminos.items():
        r = raiz(w)
        encontrado = False
        if w in IDX["inv"]:
            encontrado = True
            k = IDX["idf"][w] * peso * 3.0
            for i in IDX["inv"][w]:
                suma(i, k, r)
        if r in IDX["inv_raiz"]:
            encontrado = True
            k = IDX["idf_raiz"][r] * peso * 2.2
            for i in IDX["inv_raiz"][r]:
                suma(i, k, r)
        if r in IDX["inv_extra"]:
            encontrado = True
            k = IDX["idf_extra"][r] * peso * 1.6
            for i in IDX["inv_extra"][r]:
                suma(i, k, r)

        if len(r) > 3:
            for v in IDX["vocab_raiz"]:
                if v != r and (v.startswith(r) or r.startswith(v)):
                    k = IDX["idf_raiz"][v] * peso * 1.0
                    for i in IDX["inv_raiz"][v]:
                        suma(i, k, r)
        if not encontrado and len(r) > 4:
            for ratio, c in parecidas(r):
                k = IDX["idf_raiz"][c] * peso * ratio * 1.4
                for i in IDX["inv_raiz"][c]:
                    suma(i, k, r)

    stems_consulta = {raiz(w) for w in re.findall(r"\w+", q) if len(w) > 2}
    for codigo, aprendidas in (refuerzos or {}).items():
        i = IDX["posicion"].get(codigo)
        if i is None:
            continue
        comunes = stems_consulta & {raiz(w) for w in aprendidas.split()}
        if comunes:
            suma(i, 14.0 * len(comunes), next(iter(comunes)))

    n_term = max(1, len(originales))
    n_total = max(1, len({raiz(w) for w in terminos}))
    resultados = []
    for i, valor in puntos.items():
        reg = IDX["registros"][i]
        nucleo = 1.0 + 0.5 * len(cubierto[i] & reg["cabeza"])
        if cabezas and (cabezas & reg["cabeza"]):
            nucleo *= 1.8
        familia = 1.0
        if grupos:
            familia = 1.7 if reg["codigo"][0] in grupos else 0.45

        propios = len(cubierto[i] & originales)
        cobertura = (
            0.55
            + 0.30 * min(1.0, len(cubierto[i]) / n_total)
            + 0.15 * min(1.0, propios / n_term)
        )
        resultados.append(
            (valor * nucleo * cobertura * familia, reg["codigo"], reg["denom"])
        )
    resultados.sort(reverse=True)
    return resultados[:tope]


def objetos_parciales(bruto):
    inicio = bruto.find("[")
    if inicio == -1:
        return []
    salida, prof, arranque = [], 0, None
    cadena = escape = False
    for i in range(inicio + 1, len(bruto)):
        c = bruto[i]
        if cadena:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                cadena = False
            continue
        if c == '"':
            cadena = True
        elif c == "{":
            if prof == 0:
                arranque = i
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0 and arranque is not None:
                try:
                    salida.append(json.loads(bruto[arranque:i + 1]))
                except Exception:  # noqa: BLE001
                    pass
                arranque = None
        elif c == "]" and prof == 0:
            break
    return salida


def verifica(lista):
    limpias, descartadas = [], 0
    vistos = set()
    for o in lista or []:
        codigo = str(o.get("codigo", "")).strip()
        if codigo in vistos:
            continue
        if codigo in IDX["por_codigo"]:
            vistos.add(codigo)
            nivel = str(o.get("nivel", "00")).strip()[:2] or "00"
            limpias.append({
                "codigo": codigo,
                "denominacion": IDX["por_codigo"][codigo],
                "nivel": nivel,
                "nivel_texto": NIVELES.get(nivel, "Técnicos / Sin categoría"),
                "motivo": str(o.get("motivo", "")).strip(),
            })
        elif codigo:
            descartadas += 1
    return limpias[:6], descartadas


def limpia_opcion(texto):
    t = texto.strip().strip("¿?¡!.,;").strip()
    for _ in range(4):
        t = re.sub(
            r"^(?:la|el|los|las|un|una|unos|unas|en|a|al|del|de|para|con|por|su|sus)\s+",
            "", t, flags=re.IGNORECASE,
        ).strip()
    if len(t) > 44:
        t = t[:44].rsplit(" ", 1)[0]
        # Cortar por una palabra entera no basta: si el corte cae justo detras
        # de un conector queda "Gestion de contabilidad y", que no significa
        # nada. Se retrocede hasta que la ultima palabra tenga contenido.
        colgantes = {
            "y", "o", "u", "e", "de", "del", "al", "a", "en", "con", "por",
            "para", "sin", "sobre", "the", "la", "el", "los", "las", "un",
            "una", "mas", "más", "que", "su", "sus",
        }
        piezas = t.split()
        while len(piezas) > 1 and piezas[-1].lower().strip(",;") in colgantes:
            piezas.pop()
        t = " ".join(piezas) + "…"
    return t.capitalize()


def extraer_opciones(pregunta, opciones_modelo=None):
    if opciones_modelo and isinstance(opciones_modelo, list):
        limpias = [str(o).strip() for o in opciones_modelo if str(o).strip()]
        if len(limpias) >= 2 and set(limpias) != {"Sí", "No"}:
            return [limpia_opcion(x) for x in limpias[:3]]

    q = pregunta.strip().strip("¿?¡!").strip()
    fillers = [
        r"^su actividad principal consist[ií]a en\s+",
        r"^su tarea principal era\s+",
        r"^su labor principal era\s+",
        r"^su puesto era de\s+",
        r"^se dedicaba a\s+",
        r"^trabajaba en\s+",
        r"^realizaba tareas de\s+",
        r"^hac[ií]a funciones de\s+",
        r"^pasaba la mayor parte del tiempo en\s+",
        r"^se ocupaba de\s+",
        r"^hac[ií]a\s+",
        r"^era\s+",
        r"^realizaba\s+",
    ]
    q_limpia = q
    for f in fillers:
        q_limpia = re.sub(f, "", q_limpia, flags=re.IGNORECASE).strip()

    if " o " in q_limpia:
        partes = [p.strip() for p in re.split(r"\s+o\s+", q_limpia, maxsplit=1) if p.strip()]
        if len(partes) == 2:
            op1 = limpia_opcion(partes[0])
            op2 = limpia_opcion(partes[1])
            if op1 and op2 and op1.lower() != op2.lower():
                return [op1, op2]

    return ["Sí", "No"]


def interpreta(bruto):
    texto = re.sub(r"^```(?:json)?|```$", "", (bruto or "").strip(), flags=re.MULTILINE)
    datos = {}
    try:
        datos = json.loads(texto)
    except Exception:  # noqa: BLE001
        bloque = re.search(r"\{.*\}", texto, re.S)
        if bloque:
            try:
                datos = json.loads(bloque.group())
            except Exception:  # noqa: BLE001
                datos = {}
    if not datos:
        ocupaciones, descartadas = verifica(objetos_parciales(texto))
        return {"ocupaciones": ocupaciones, "pregunta": "", "opciones": [], "descartadas": descartadas}

    ocupaciones, descartadas = verifica(datos.get("ocupaciones"))
    sugeridos = " ".join(
        re.findall(r"[a-zñáéíóúü]+", normaliza(str(datos.get("otros_terminos", "") or "")))[:12]
    )
    pregunta = str(datos.get("pregunta", "") or "").strip()
    opciones = extraer_opciones(pregunta, datos.get("opciones")) if pregunta else []

    return {
        "ocupaciones": ocupaciones,
        "pregunta": pregunta,
        "opciones": opciones,
        "descartadas": descartadas,
        "mas_terminos": sugeridos,
    }
