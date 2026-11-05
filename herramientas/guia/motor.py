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


# ---------------------------------------------------------------------------
# Lista a medida: varios intereses, un solo PDF
# ---------------------------------------------------------------------------
# Lo pidió Álvaro el 05/11/2026: una persona que busca conserjería, almacén y
# control de accesos tiene que salir de la cita con una sola hoja, no con tres
# sectores enteros ni con veinte casillas marcadas a mano. Sin IA: cada
# interés pasa por el buscador del codificador y la tabla ocupación → sector.

TOPE_INTERESES = 6


def intereses(texto):
    """«conserje, mozo de almacén y control de accesos» -> los tres, sin repetir."""
    trozos = re.split(r"[,;\n/]+|\s+y\s+|\s+o\s+", texto or "")
    vistos, salida = set(), []
    for t in trozos:
        t = re.sub(r"\s+", " ", t).strip(" .-")
        if len(t) > 2 and normaliza(t) not in vistos:
            vistos.add(normaliza(t))
            salida.append(t)
    return salida[:TOPE_INTERESES]


def _nombra(interes, denominacion):
    """La ocupación nombra todas las palabras con contenido de lo escrito
    («mozo de almacén» en «MOZOS DE CARGA Y DESCARGA, ALMACÉN…»), por el
    principio de la palabra para que valgan plurales y femeninos."""
    d = normaliza(denominacion)
    return all(normaliza(p)[:min(5, len(p) - 1)] in d for p in interes.split() if len(p) > 3)


def destinos_de(interes):
    """Dónde mirar para un interés: (denominación, [(capítulo, apartado o None)]), hasta tres.

    Votan dos cosas, sin IA:

    - Las tres primeras ocupaciones del codificador (6, 4 y 2 puntos), pero
      solo las que nombran lo escrito: «conserjería» daba «conserjes de hotel»
      y «control de accesos», «técnicos en control de calidad». Si ninguna lo
      nombra, vale la primera, como en el codificador.
    - Los apartados donde hay fichas que lo nombran (tres cuartos de punto por
      ficha, hasta seis): es lo que lleva «control de accesos», que no tiene
      ocupación con sector, a conserjería y a auxiliares de eventos.

    Sale lo que tiene al menos el 40 % de los puntos del primero, y un
    capítulo entero se come sus apartados.
    """
    from herramientas.sispe import motor as sispe

    puntos = {}
    halladas = sispe.busca(interes, tope=3) if len(normaliza(interes)) > 2 else []
    buenas = [h for h in halladas if _nombra(interes, h[2])] or halladas[:1]
    for peso, (_, codigo, _) in zip((6, 4, 2), buenas):
        for n, destino in enumerate(guia.destinos(codigo)):
            if destino[0] in guia.CAPITULOS:
                puntos[destino] = puntos.get(destino, 0) + peso / (n + 1)
    cuenta = {}
    for f in guia.busca(interes, tope=40):
        if f["capitulo"] in guia.sectores() or f["capitulo"] == "08-ett":
            par = (f["capitulo"], f["apartado"])
            cuenta[par] = cuenta.get(par, 0) + 1
    for (capitulo, apartado), n in cuenta.items():
        destino = (capitulo, None) if (capitulo, None) in puntos else (capitulo, apartado)
        puntos[destino] = puntos.get(destino, 0) + min(n, 6) * .75
    if not puntos:
        return (buenas[0][2] if buenas else None), []
    enteros = {c for c, a in puntos if a is None}
    orden = [d for d in sorted(puntos, key=lambda d: -puntos[d]) if d[1] is None or d[0] not in enteros]
    primero = puntos[orden[0]]
    return (buenas[0][2] if buenas else None), [d for d in orden if puntos[d] >= .4 * primero][:3]


def rotulo(destino):
    """(capítulo, apartado) -> «Conserjería y servicios auxiliares» o el capítulo entero."""
    capitulo, apartado = destino
    return apartado or guia.CAPITULOS[capitulo]["corto"]


def _primero_con_via(fichas):
    """Delante las que dejan mandar el currículum ya (correo o página de empleo)."""
    return sorted(fichas, key=lambda f: not (f.get("correo") or f.get("web_empleo")))


def a_medida(elegidos, generales=True):
    """Las secciones del PDF a medida. `elegidos`: [(interés, [(capítulo, apartado)])].

    Una sección por interés, con sus apartados; una empresa que ya ha salido
    en un interés anterior no se repite. Los centros especiales de empleo van
    aparte, como en el resto de la app, y al final los portales generalistas
    y las grandes ETT, que sirven para todo lo que busca.
    """
    vistas, salida = set(), []
    for interes, destinos in elegidos:
        apartados = []
        for destino in destinos:
            capitulo, apartado = destino
            s = guia.seccion(capitulo, [apartado] if apartado else None)
            if not s:
                continue
            for nombre, fs in s["apartados"]:
                suyas = [f for f in fs if normaliza(f["nombre"]) not in vistas]
                vistas.update(normaliza(f["nombre"]) for f in suyas)
                if suyas:
                    apartados.append((f"{s['corto']} · {nombre}", _primero_con_via(suyas)))
        if apartados:
            salida.append({
                "capitulo": destinos[0][0], "titulo": interes[:1].upper() + interes[1:],
                "corto": interes, "entero": False, "apartados": apartados,
                "n": sum(len(fs) for _, fs in apartados), "general": False,
            })
    salida = guia.aparta_cee(salida)
    if generales and salida:
        apartados = []
        for capitulo, apartado in guia.GENERALES:
            s = guia.seccion(capitulo, [apartado])
            if s:
                suyas = [f for _, fs in s["apartados"] for f in fs if normaliza(f["nombre"]) not in vistas]
                vistas.update(normaliza(f["nombre"]) for f in suyas)
                if suyas:
                    apartados.append((f"{s['corto']} · {apartado}", suyas))
        if apartados:
            salida.append({
                "capitulo": "generales", "titulo": "Para todo lo que buscas: portales y grandes ETT",
                "corto": "Portales y ETT", "entero": False, "apartados": apartados,
                "n": sum(len(fs) for _, fs in apartados), "general": False,
            })
    return salida
