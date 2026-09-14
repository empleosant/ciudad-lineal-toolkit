"""
Motor del asesor de formación. Python puro: no importa Streamlit.

Pensado para el Excel del buscador de acciones formativas de la Comunidad
de Madrid (vialaboris.comunidad.madrid/Formacion), que trae una fila por
EDICIÓN de un curso: mismo nombre repetido con distinto centro, municipio
y fecha. Se agrupa por denominación para que la IA razone sobre cursos.

    lee_filas(bytes, nombre)          Excel o CSV -> filas (dict por fila) y hojas
    agrupa(filas)                     filas -> cursos con sus ediciones
    preselecciona(cursos, perfil, n)  si hay demasiados, los que más casan
    lista_para_ia(cursos)             los cursos numerados, en texto compacto
    resuelve(recomendaciones, cursos) cruza lo que devuelve la IA con los reales
    perfil_desde_cv(cv)               el currículo del generador, sin datos personales
"""

import io
import re
from datetime import date

from comun.texto import normaliza

MAX_TEXTO_CELDA = 140
COLUMNAS_MAX = 12

# Nombres de columna del Excel de la Comunidad de Madrid, y cómo se llaman aquí.
PISTAS = {
    "denominacion": ("denominaci", "nombre del curso", "curso", "especialidad", "acción formativa", "accion formativa"),
    "tipo": ("tipo",),
    "codigo_esp": ("código especialidad", "codigo especialidad", "certificado"),
    "inicio": ("fecha de inicio", "inicio"),
    "fin": ("fecha de fin", "fin"),
    "modalidad": ("modalidad",),
    "centro": ("centro",),
    "municipio": ("municipio", "localidad"),
    "cp": ("código postal", "codigo postal", "cp"),
    "codigo": ("código", "codigo"),
}

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


def _limpia(v):
    if v is None:
        return ""
    if isinstance(v, float) and v != v:  # NaN
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    v = re.sub(r"\s+", " ", str(v)).strip()
    if v.lower() == "nan":
        return ""
    v = re.sub(r"^(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}(:\d{2})?$", r"\1", v)  # fecha con hora
    return v[:MAX_TEXTO_CELDA]


def _leer_excel(datos, hoja=None):
    """Con calamine, que abre archivos que a openpyxl le fallan por los estilos."""
    try:
        from python_calamine import CalamineWorkbook
        libro = CalamineWorkbook.from_filelike(io.BytesIO(datos))
        hojas = list(libro.sheet_names)
        filas = libro.get_sheet_by_name(hoja if hoja in hojas else hojas[0]).to_python()
        return filas, hojas
    except ImportError:
        import pandas as pd
        libro = pd.ExcelFile(io.BytesIO(datos))
        hojas = list(libro.sheet_names)
        df = libro.parse(hoja if hoja in hojas else hojas[0], header=None, dtype=str)
        return df.fillna("").values.tolist(), hojas


def lee_filas(datos, nombre="cursos.xlsx", hoja=None):
    """(filas, hojas). Cada fila es {"n": número, "campos": {columna: valor}}.

    La cabecera es la primera fila con al menos tres celdas de texto; lo que
    haya por encima (títulos, fechas de descarga) se salta.
    """
    if (nombre or "").lower().endswith(".csv"):
        import pandas as pd
        df = pd.read_csv(io.BytesIO(datos), sep=None, engine="python", dtype=str, header=None)
        crudas, hojas = df.fillna("").values.tolist(), []
    else:
        crudas, hojas = _leer_excel(datos, hoja)

    crudas = [[_limpia(c) for c in f] for f in crudas]
    i_cab = next((i for i, f in enumerate(crudas) if sum(1 for c in f if c and not c[0].isdigit()) >= 3), 0)
    cabecera = [c or f"col{j + 1}" for j, c in enumerate(crudas[i_cab])]
    cabecera = [c for c in cabecera if not c.lower().startswith("unnamed")][:COLUMNAS_MAX]

    filas = []
    for i, f in enumerate(crudas[i_cab + 1:], 1):
        campos = {c: v for c, v in zip(cabecera, f) if v}
        if campos:
            filas.append({"n": i, "campos": campos})
    return filas, hojas


def columnas(filas):
    """{clave: nombre de columna} para las columnas que se reconocen."""
    if not filas:
        return {}
    nombres = list(filas[0]["campos"].keys())
    for f in filas[1:20]:
        for c in f["campos"]:
            if c not in nombres:
                nombres.append(c)
    salida = {}
    for clave, pistas in PISTAS.items():
        # Las pistas van de más a menos específica: "denominaci" antes que
        # "acción formativa", que también casa con "Tipo de Acción Formativa".
        for pista in pistas:
            c = next((c for c in nombres if pista in c.lower() and c not in salida.values()), None)
            if c:
                salida[clave] = c
                break
    if "denominacion" not in salida:
        # la columna de texto más largo
        medias = {c: sum(len(f["campos"].get(c, "")) for f in filas[:200]) for c in nombres}
        salida["denominacion"] = max(medias, key=medias.get)
    return salida


def agrupa(filas):
    """Cursos: una entrada por denominación, con todas sus ediciones."""
    cols = columnas(filas)
    c_den = cols["denominacion"]
    grupos, orden = {}, []
    for f in filas:
        den = f["campos"].get(c_den, "").strip()
        if not den:
            continue
        clave = normaliza(den)
        if clave not in grupos:
            grupos[clave] = {
                "n": len(orden) + 1, "denominacion": den,
                "tipo": f["campos"].get(cols.get("tipo", ""), ""),
                "codigo_esp": f["campos"].get(cols.get("codigo_esp", ""), ""),
                "ediciones": [],
            }
            orden.append(clave)
        g = grupos[clave]
        g["ediciones"].append({
            "fila": f["n"],
            "codigo": f["campos"].get(cols.get("codigo", ""), ""),
            "centro": f["campos"].get(cols.get("centro", ""), ""),
            "municipio": f["campos"].get(cols.get("municipio", ""), ""),
            "cp": f["campos"].get(cols.get("cp", ""), ""),
            "modalidad": f["campos"].get(cols.get("modalidad", ""), ""),
            "inicio": f["campos"].get(cols.get("inicio", ""), ""),
            "fin": f["campos"].get(cols.get("fin", ""), ""),
        })
    cursos = [grupos[k] for k in orden]
    for g in cursos:
        g["ediciones"].sort(key=lambda e: e["inicio"] or "9999")
    return cursos


def texto_curso(curso):
    return " ".join([curso["denominacion"], curso.get("tipo", ""), curso.get("codigo_esp", "")])


def preselecciona(cursos, perfil, n=250):
    """Si hay más de n cursos, los n que más palabras comparten con el perfil.

    Es solo para no desbordar a la IA con catálogos enormes: la elección de
    verdad la hace ella. Se conserva el orden original.
    """
    if len(cursos) <= n:
        return cursos
    claves = _palabras(perfil)
    puntuados = []
    for c in cursos:
        propias = _palabras(texto_curso(c))
        comunes = len(claves & propias)
        parciales = sum(1 for a in claves for b in propias
                        if a != b and len(a) > 3 and (b.startswith(a) or a.startswith(b)))
        puntuados.append((comunes * 2 + parciales * 0.5, c["n"], c))
    puntuados.sort(key=lambda x: (-x[0], x[1]))
    elegidos = {c["n"] for _, _, c in puntuados[:n]}
    return [c for c in cursos if c["n"] in elegidos]


def _edicion_corta(e):
    piezas = [e["municipio"] or e["centro"], e["modalidad"].lower() if e["modalidad"] else "",
              f"inicio {e['inicio']}" if e["inicio"] else ""]
    return " · ".join(p for p in piezas if p)


def lista_para_ia(cursos, max_ediciones=4):
    lineas = []
    for c in cursos:
        eds = c["ediciones"]
        resumen = "; ".join(_edicion_corta(e) for e in eds[:max_ediciones])
        if len(eds) > max_ediciones:
            resumen += f"; y {len(eds) - max_ediciones} ediciones más"
        cabecera = " | ".join(x for x in (c["denominacion"], c.get("tipo"), c.get("codigo_esp")) if x)
        lineas.append(f"[{c['n']}] {cabecera} || {resumen}")
    return "\n".join(lineas)


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
            "edicion": str(r.get("edicion", "")).strip(),
        })
    return salida, descartadas


def hoy():
    return date.today().strftime("%Y-%m-%d")


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
                          ("Permiso de conducir", "permiso"), ("Disponibilidad", "disponibilidad"),
                          ("Localidad", "localidad")):
        if cv.get(clave):
            partes.append(f"- {rotulo}: {cv[clave]}")
    return "\n".join(partes)
