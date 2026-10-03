"""
Más empresas con IA para «Dónde enviar el CV». Python puro, sin Streamlit.

La guía no cubre todos los oficios (un programador de videojuegos no tiene
capítulo). Para esos, Gemini busca en Google empresas de Madrid y alrededores
(`modelo.py`) y aquí se convierte lo que contesta en fichas con la misma forma
que las de la guía, para que se pinten, se marquen y se impriman igual.

Lo que este módulo garantiza, porque el modelo no lo garantiza:

- **Un enlace solo sale si la búsqueda lo ha visto.** La web de una ficha es
  el dominio que da el modelo únicamente cuando ese dominio está entre las
  páginas que Google ha devuelto. Si no, la ficha sale sin enlace y dice en
  qué página se la ha visto nombrada.
- **Sin fuente no hay ficha**, cuando la respuesta trae apoyos: una empresa
  que no nombra ninguna página y cuyo dominio no ha salido en la búsqueda se
  descarta. (Si la respuesta no trae apoyos no se puede saber, y se queda sin
  enlace.)
- **Lo que ya está en la guía sale con su ficha de la guía**, que está
  comprobada a mano, y no con lo que diga el modelo.
- Todas llevan `ia: True`: la pantalla y el PDF las separan y las etiquetan
  «sin comprobar».
"""

import json
import re

from comun import guia
from comun.texto import normaliza

CAPITULO = "ia"                   # el «capítulo» de estas fichas; no existe en la guía
APARTADO = "Sugeridas por IA"
TOPE = 10


def clave_consulta(puesto):
    """Con qué nombre se guarda una búsqueda: el puesto sin acentos ni espacios de más."""
    return normaliza(puesto or "").strip()


def busca(texto, tope=60):
    """Lo que enseña el buscador de la pestaña: [(rótulo, fichas)], o [].

    Dos formas de encontrar, una detrás de otra y sin repetir fichas:

    1. Las fichas que nombran lo escrito (`guia.busca`, por la raíz de la
       palabra: «limpiador» encuentra «limpieza»).
    2. Las del sector de la ocupación que el codificador entiende por eso, sin
       IA. Es lo que hace que «soldador» dé los talleres aunque ninguna ficha
       diga «soldador»: la tabla ocupación → sector está hecha a mano.
    """
    from herramientas.sispe import motor as sispe

    texto = (texto or "").strip()
    apartados, vistas = [], set()
    nombran = guia.busca(texto, tope=tope)
    if nombran:
        vistas.update(guia.clave(f) for f in nombran)
        apartados.append((f"{len(nombran)} fichas que lo nombran", nombran))
    # Con muchas fichas que lo nombran no hace falta adivinar el sector, y
    # adivinarlo mete ruido: «barcelo» acababa en los bares.
    hallada = sispe.busca(texto, tope=1) if len(normaliza(texto)) > 2 and len(nombran) < 10 else []
    if hallada:
        _, codigo, denominacion = hallada[0]
        for s in guia.secciones([codigo], generales=False, cee=False):
            suyas = [f for _, fs in s["apartados"] for f in fs if guia.clave(f) not in vistas]
            vistas.update(guia.clave(f) for f in suyas)
            if suyas:
                apartados.append((f"{s['corto']}: el sector de «{denominacion.capitalize()}»", suyas))
    return apartados


def _json(texto):
    """El objeto JSON de una respuesta que puede venir envuelta en ```json o con prosa."""
    texto = (texto or "").strip()
    a, b = texto.find("{"), texto.rfind("}")
    if a < 0 or b <= a:
        return {}
    try:
        dato = json.loads(texto[a:b + 1])
    except ValueError:
        return {}
    return dato if isinstance(dato, dict) else {}


def dominio(texto):
    """«https://www.Empresa.com/empleo» -> «empresa.com». '' si no parece un dominio."""
    d = re.sub(r"^[a-z]+://", "", (texto or "").strip().lower())
    d = re.sub(r"^www\.", "", d).split("/")[0].split("?")[0].strip(". ")
    return d if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", d) else ""


def _mismo_sitio(a, b):
    """empleo.empresa.com y empresa.com son el mismo sitio."""
    return bool(a and b) and (a == b or a.endswith("." + b) or b.endswith("." + a))


def _limpia(valor, tope):
    """Texto plano de una línea: el modelo a veces mete markdown o marcas de cita."""
    t = re.sub(r"\[\d+(,\s*\d+)*\]", "", str(valor or ""))
    t = re.sub(r"[*_`#<>]", "", t)
    return re.sub(r"\s+", " ", t).strip()[:tope].strip()


def _de_la_guia():
    """nombre normalizado -> ficha de la guía (sectores y centros especiales)."""
    indice = {}
    for capitulo in guia.sectores() + ["09-insercion"]:
        for f in guia.fichas(capitulo):
            indice.setdefault(normaliza(f["nombre"]), f)
    return indice


def interpreta(texto, fuentes=(), apoyos=()):
    """Lo que ha contestado el modelo, hecho fichas. Devuelve (fichas, descartadas).

    `fuentes` y `apoyos` son los de `ia.busca_en_la_web`.
    """
    dominios = [dominio(t) or dominio(u) for t, u in fuentes]
    conocidas = _de_la_guia()
    fichas, vistos, descartadas = [], set(), 0
    for e in _json(texto).get("empresas") or []:
        if not isinstance(e, dict):
            continue
        nombre = _limpia(e.get("nombre"), 80)
        clave = normaliza(nombre)
        if not clave or clave in vistos:
            continue
        vistos.add(clave)
        if clave in conocidas:
            fichas.append(conocidas[clave])
            continue
        suyo = dominio(e.get("dominio") or e.get("web") or "")
        comprobado = bool(suyo) and any(_mismo_sitio(suyo, d) for d in dominios)
        la_nombran = []
        for trozo, indices in apoyos:
            if clave in normaliza(trozo):
                la_nombran += [dominios[i] for i in indices if dominios[i] and dominios[i] not in la_nombran]
        if apoyos and not comprobado and not la_nombran:
            descartadas += 1
            continue
        como = _limpia(e.get("como"), 220)
        if not comprobado and la_nombran:
            como = (como + " " if como else "") + f"Vista en {', '.join(la_nombran[:2])}; busca su web antes de enviar."
        donde = _limpia(e.get("donde"), 60)
        que = _limpia(e.get("que"), 220)
        fichas.append({
            "capitulo": CAPITULO, "id": re.sub(r"[^a-z0-9]+", "-", clave).strip("-") or "empresa",
            "apartado": APARTADO, "formato": "", "nombre": nombre, "tipo": "",
            "que": que + (f" ({donde})" if donde and normaliza(donde) not in normaliza(que) else ""),
            "direccion": "", "cp": "", "municipio": "", "transporte": "", "telefono": "", "correo": "",
            "web": f"https://{suyo}" if comprobado else "", "web_empleo": "",
            "como": como, "ia": True,
        })
        if len(fichas) >= TOPE:
            break
    return fichas, descartadas


def empaqueta(fichas, fecha):
    """Para guardar en el Gist, que solo admite texto por clave."""
    return json.dumps({"fecha": fecha, "fichas": fichas}, ensure_ascii=False)


def desempaqueta(texto):
    """(fichas, fecha) de lo guardado; ([], '') si está roto o no es de las nuestras."""
    try:
        dato = json.loads(texto or "")
        fichas = [f for f in dato["fichas"] if isinstance(f, dict) and f.get("nombre") and f.get("capitulo")]
        return fichas, str(dato.get("fecha", ""))
    except (ValueError, KeyError, TypeError):
        return [], ""
