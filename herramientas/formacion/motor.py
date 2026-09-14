"""
Motor del asesor de formación. Python puro: no importa Streamlit.

    lee_cursos(bytes, nombre)         Excel o CSV -> lista de cursos (dict por fila)
    preselecciona(cursos, perfil, n)  los n cursos que más casan con el perfil
    lista_para_ia(cursos)             los cursos numerados, en texto compacto
    perfil_desde_cv(cv)               el currículo del generador, sin datos personales
"""

import io
import re

import pandas as pd

from comun.texto import normaliza

MAX_TEXTO_CELDA = 140
COLUMNAS_MAX = 10

VACIAS = {
    "de", "del", "la", "el", "los", "las", "en", "y", "o", "con", "para", "por",
    "un", "una", "al", "sin", "que", "su", "se", "a", "e", "u", "es", "son",
    "curso", "cursos", "formacion", "nivel", "horas", "modalidad", "online",
    "presencial", "general", "persona", "experiencia", "anos", "años", "trabajo",
}


def _raiz(w):
    if len(w) > 5 and w.endswith("es"):
        w = w[:-2]
    elif len(w) > 4 and w.endswith("s"):
        w = w[:-1]
    if len(w) > 5 and w.endswith("or"):
        w = w[:-2]
    if len(w) > 4 and w[-1] in "aoe":
        w = w[:-1]
    return w


def _palabras(texto):
    return {_raiz(w) for w in re.findall(r"\w+", normaliza(texto or "")) if len(w) > 2 and w not in VACIAS}


def lee_cursos(datos, nombre="cursos.xlsx", hoja=None):
    """Lista de cursos. Cada curso es {"n": fila, "campos": {columna: valor}}.

    Devuelve (cursos, hojas). Se quedan las columnas con contenido, hasta
    COLUMNAS_MAX, y cada celda recortada a MAX_TEXTO_CELDA caracteres.
    """
    nombre = (nombre or "").lower()
    if nombre.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(datos), sep=None, engine="python", dtype=str)
        hojas = []
    else:
        libro = pd.ExcelFile(io.BytesIO(datos))
        hojas = list(libro.sheet_names)
        df = libro.parse(hoja if hoja in hojas else hojas[0], dtype=str)

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    columnas = [c for c in df.columns if not c.lower().startswith("unnamed")][:COLUMNAS_MAX]

    cursos = []
    for i, (_, fila) in enumerate(df.iterrows(), 1):
        campos = {}
        for c in columnas:
            v = fila.get(c)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            v = re.sub(r"\s+", " ", str(v)).strip()
            if v and v.lower() != "nan":
                campos[c] = v[:MAX_TEXTO_CELDA]
        if campos:
            cursos.append({"n": i, "campos": campos})
    return cursos, hojas


PISTAS_TITULO = ("denominaci", "nombre", "curso", "especialidad", "titulo", "título", "accion", "acción")


def columna_titulo(cursos):
    """La columna que mejor sirve de título: por su nombre o, si no, la de texto más largo."""
    if not cursos:
        return None
    columnas = list(cursos[0]["campos"].keys())
    for c in columnas:
        if any(p in c.lower() for p in PISTAS_TITULO):
            return c
    medias = {}
    for c in columnas:
        valores = [x["campos"].get(c, "") for x in cursos[:200]]
        medias[c] = sum(len(v) for v in valores) / max(1, len(valores))
    return max(medias, key=medias.get)


def titulo_curso(curso, columna=None):
    campos = curso["campos"]
    if columna and campos.get(columna):
        return campos[columna]
    return next(iter(campos.values()))


def texto_curso(curso):
    return " ".join(curso["campos"].values())


def preselecciona(cursos, perfil, n=60):
    """Los n cursos con más palabras en común con el perfil, en su orden original.

    Si hay n o menos, se devuelven todos. Es solo para no mandar a la IA un
    catálogo entero: la elección de verdad la hace ella.
    """
    if len(cursos) <= n:
        return cursos
    claves = _palabras(perfil)
    puntuados = []
    for c in cursos:
        propias = _palabras(texto_curso(c))
        comunes = len(claves & propias)
        parciales = sum(1 for a in claves for b in propias if a != b and len(a) > 3 and (b.startswith(a) or a.startswith(b)))
        puntuados.append((comunes * 2 + parciales * 0.5, c["n"], c))
    puntuados.sort(key=lambda x: (-x[0], x[1]))
    elegidos = {c["n"] for _, _, c in puntuados[:n]}
    return [c for c in cursos if c["n"] in elegidos]


def lista_para_ia(cursos):
    lineas = []
    for c in cursos:
        lineas.append(f"[{c['n']}] " + " | ".join(f"{k}: {v}" for k, v in c["campos"].items()))
    return "\n".join(lineas)


def perfil_desde_cv(cv):
    """El currículo del generador en texto, sin nombre ni contacto."""
    partes = []
    if cv.get("perfil"):
        partes.append(f"Perfil: {cv['perfil']}")
    for e in cv.get("experiencias", []):
        p = e.get("puesto") or e.get("denominacion")
        if not p:
            continue
        fechas = " - ".join(x for x in (e.get("desde"), e.get("hasta")) if x)
        linea = f"- Experiencia: {p}" + (f" ({fechas})" if fechas else "")
        if e.get("funciones"):
            linea += f". Funciones: {e['funciones']}"
        partes.append(linea)
    for f in cv.get("formacion", []):
        if f.get("titulo"):
            partes.append(f"- Formación: {f['titulo']}" + (f" ({f['anio']})" if f.get("anio") else ""))
    for rotulo, clave in (("Idiomas", "idiomas"), ("Informática", "informatica"),
                          ("Permiso de conducir", "permiso"), ("Disponibilidad", "disponibilidad")):
        if cv.get(clave):
            partes.append(f"- {rotulo}: {cv[clave]}")
    return "\n".join(partes)


def resuelve(recomendaciones, cursos):
    """Cruza lo que devuelve la IA con los cursos reales. Descarta números inventados."""
    por_n = {c["n"]: c for c in cursos}
    salida, descartadas, vistos = [], 0, set()
    for r in recomendaciones or []:
        try:
            n = int(str(r.get("n", "")).strip("[] "))
        except ValueError:
            descartadas += 1
            continue
        if n not in por_n or n in vistos:
            descartadas += 1
            continue
        vistos.add(n)
        salida.append({
            "curso": por_n[n],
            "por_que": str(r.get("por_que", "")).strip(),
            "prioridad": str(r.get("prioridad", "")).strip().lower() or "media",
            "aviso": str(r.get("aviso", "")).strip(),
        })
    return salida, descartadas
