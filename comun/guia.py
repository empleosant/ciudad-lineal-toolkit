"""
La Guía de empleo de Madrid dentro de la app. Python puro, sin Streamlit.

Las fichas son una copia de la guía (`comun/datos/guia/`, la saca
`scripts/traer_guia.py`); lo único que se escribe aquí a mano es qué
capítulos le tocan a cada ocupación del catálogo SISPE
(`comun/datos/ocupaciones_sectores.csv`).

    destinos(codigo)          (capítulo, apartado) de una ocupación, el principal primero
    secciones(codigos)        lo que hay que enseñar para una o varias ocupaciones
    seccion(capitulo)         un capítulo entero (o algunos apartados) con la misma forma
    pdf(secciones, ...)       la lista para imprimir, en blanco y negro
    apartados_html(...)       las mismas fichas en pantalla (las clases .gu-* de comun/estilo.py)

Lo usan el codificador SISPE («Dónde enviar el CV», bajo las tarjetas) y el
generador de CV (la hoja aparte del paso 4). Lo prueba `pruebas/guia.py`.
"""

import csv
import io
import json
import os
import re
from xml.sax.saxutils import escape as _esc

from comun.texto import esc

DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
GUIA = os.path.join(DATOS, "guia")
TABLA = os.path.join(DATOS, "ocupaciones_sectores.csv")

with open(os.path.join(GUIA, "edicion.json"), encoding="utf-8") as _f:
    EDICION = json.load(_f)

# Para las píldoras de la pantalla: el título entero de algunos capítulos
# pasa de cincuenta letras. Lo que no está aquí usa lo que va antes de «:».
CORTOS = {
    "08-ett": "Trabajo temporal",
    "10-comercio": "Comercio",
    "11-hosteleria": "Hostelería",
    "12-logistica": "Logística",
    "13-limpieza": "Limpieza y conserjería",
    "15-monitores": "Monitores",
    "16-deporte": "Deporte",
    "17-ocio-y-cultura": "Ocio y cultura",
    "18-administracion": "Atención al cliente y oficina",
    "20-transporte": "Transporte de viajeros",
    "21-construccion": "Construcción",
    "22-tecnologia": "Tecnología",
    "24-portales": "Portales de empleo",
    "25-empleo-publico": "Empleo público",
    "27-sanidad": "Sanidad",
    "28-aeropuerto": "Aeropuerto",
    "30-industria": "Industria y talleres",
    "32-banca": "Banca y seguros",
    "34-instalaciones": "Instalaciones",
    "35-mensajeria": "Mensajería y camión",
    "36-jardineria": "Jardinería",
    "37-alimentacion": "Alimentación",
    "38-inmobiliarias": "Inmobiliarias y fincas",
    "39-asesorias": "Asesorías y despachos",
    "40-eventos": "Eventos",
    "41-farmacias": "Farmacias y ópticas",
    "42-servicios-tecnicos": "Reparaciones y lavanderías",
    "43-movilidad": "Movilidad y gasolineras",
    "44-animales": "Animales",
    "45-publicidad": "Artes gráficas y medios",
    "46-hogar": "Empleo de hogar",
    "47-tercer-sector": "Tercer sector",
}

# Cuando la ocupación no tiene sector en la guía: los portales generalistas y
# las grandes redes de trabajo temporal, que cubren casi cualquier puesto.
GENERALES = [("24-portales", "Generalistas"), ("08-ett", "Grandes redes")]


def _lee_csv(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        lineas = [l for l in f if l.strip() and not l.lstrip().startswith("#")]
    return list(csv.DictReader(lineas))


def _carga():
    capitulos = {}
    for c in _lee_csv(os.path.join(GUIA, "capitulos.csv")):
        c["apartados"] = [a.strip() for a in c["apartados"].split("|") if a.strip()]
        c["corto"] = CORTOS.get(c["id"]) or c["titulo"].split(":")[0].strip()
        capitulos[c["id"]] = c
    fichas = {}
    for f in _lee_csv(os.path.join(GUIA, "fichas.csv")):
        fichas.setdefault(f["capitulo"], []).append(f)
    tabla = {}
    for fila in _lee_csv(TABLA):
        destino = (fila["capitulo"].strip(), fila["apartado"].strip() or None)
        tabla.setdefault(fila["prefijo"].strip(), []).append(destino)
    return capitulos, fichas, tabla


CAPITULOS, _FICHAS, _TABLA = _carga()


def fichas(capitulo, apartado=None):
    """Las fichas del capítulo (o de uno de sus apartados), en el orden de la guía."""
    todas = _FICHAS.get(capitulo, [])
    return [f for f in todas if apartado is None or f["apartado"] == apartado]


def destinos(codigo):
    """Los (capítulo, apartado) de una ocupación, el principal primero.

    Manda el prefijo más largo de la tabla que case con el código. Un
    capítulo «-» quiere decir que esa ocupación no tiene sector en la guía.
    Lista vacía si no lo tiene.
    """
    codigo = str(codigo or "").strip()
    for largo in range(len(codigo), 0, -1):
        filas = _TABLA.get(codigo[:largo])
        if filas:
            return [d for d in filas if d[0] != "-"]
    return []


def secciones(codigos, generales=True):
    """Lo que hay que enseñar para una o varias ocupaciones.

    Cada sección es un capítulo con los apartados que tocan, ordenadas por
    cuántas ocupaciones apuntan a él y, a igualdad, por el orden en que
    salen. Si ninguna ocupación tiene sector y `generales` es verdadero,
    salen los portales generalistas y las grandes ETT, marcadas así.
    """
    codigos = list(codigos)
    elegidos = {}            # capítulo -> None (entero) o lista de apartados
    votos, orden = {}, []
    for codigo in codigos:
        vistos = set()
        for capitulo, apartado in destinos(codigo):
            if capitulo not in CAPITULOS:
                continue
            if capitulo not in elegidos:
                elegidos[capitulo] = []
                orden.append(capitulo)
            if apartado is None:
                elegidos[capitulo] = None
            elif elegidos[capitulo] is not None and apartado not in elegidos[capitulo]:
                elegidos[capitulo].append(apartado)
            if capitulo not in vistos:
                votos[capitulo] = votos.get(capitulo, 0) + 1
                vistos.add(capitulo)

    general = False
    if not elegidos and generales and codigos:
        general = True
        for capitulo, apartado in GENERALES:
            elegidos.setdefault(capitulo, []).append(apartado)
            orden.append(capitulo)
            votos[capitulo] = 1

    salida = []
    for capitulo in sorted(orden, key=lambda c: (-votos[c], orden.index(c))):
        s = seccion(capitulo, elegidos[capitulo], general)
        if s:
            salida.append(s)
    return salida


def seccion(capitulo, apartados=None, general=False):
    """Un capítulo como sección: entero, o solo esos apartados (en el orden de
    la guía, no en el de la tabla). None si no tiene fichas."""
    cap = CAPITULOS.get(capitulo)
    if cap is None:
        return None
    suyos = []
    for nombre in cap["apartados"]:
        if apartados is not None and nombre not in apartados:
            continue
        suyas = fichas(capitulo, nombre)
        if suyas:
            suyos.append((nombre, suyas))
    if not suyos:
        return None
    return {
        "capitulo": capitulo, "titulo": cap["titulo"], "corto": cap["corto"],
        "entero": apartados is None, "apartados": suyos,
        "n": sum(len(f) for _, f in suyos), "general": general,
    }


def sectores():
    """Los capítulos de «Sectores que contratan» (la parte IV), en el orden de la guía."""
    return [c for c, cap in CAPITULOS.items() if cap["parte"] == "IV"]


# ---------------------------------------------------------------------------
# Cómo se escribe una ficha: lo mismo en pantalla y en el papel
# ---------------------------------------------------------------------------

def vista(url, tope=46):
    """La dirección legible: sin protocolo ni parámetros y, si es larga, el
    dominio y el último tramo. Es la función `vista()` de la guía: en el papel
    se lee lo mismo que en el PDF de la guía."""
    corta = re.sub(r"^https?://(www\.)?", "", url.strip()).rstrip("/")
    corta = corta.split("?")[0].split("#")[0].rstrip("/")
    if len(corta) <= tope:
        return corta
    dominio, _, resto = corta.partition("/")
    ultimo = resto.rsplit("/", 1)[-1]
    if ultimo and len(dominio) + len(ultimo) + 3 <= tope:
        return f"{dominio}/…/{ultimo}" if "/" in resto else f"{dominio}/{ultimo}"
    if len(dominio) + 2 <= tope:
        return f"{dominio}/…"
    return corta[:tope - 1].rstrip("/-_.") + "…"


def telefonos(f):
    salida = []
    for t in re.split(r"[|;]", f.get("telefono", "")):
        cifras = re.sub(r"\D", "", t)
        if len(cifras) == 9:
            salida.append(f"{cifras[:3]} {cifras[3:6]} {cifras[6:]}")
        elif t.strip():
            salida.append(t.strip())
    return " · ".join(salida)


def direccion(f):
    """La primera dirección, con el código postal y el municipio si no los lleva."""
    dirs = [d.strip() for d in f.get("direccion", "").split("|") if d.strip()]
    if not dirs:
        return ""
    d = dirs[0]
    if f.get("cp") and f["cp"] not in d:
        d += f" · {f['cp']} {f.get('municipio', '')}".rstrip()
    elif f.get("municipio") and f["municipio"].lower() not in d.lower():
        d += f" · {f['municipio']}"
    return d


def enlace(f):
    """(url, rótulo) por donde se presenta la candidatura: la web de empleo si
    la hay y, si no, la web de la entidad."""
    if f.get("web_empleo"):
        return f["web_empleo"], "Empleo"
    if f.get("web"):
        return f["web"], "Web"
    return "", ""


def ficha_html(f):
    """Una ficha en pantalla: nombre, a qué se dedica, cómo presentarse y el canal."""
    renglon = f.get("formato") == "renglon"
    url, _ = enlace(f)
    datos = []
    if url:
        datos.append(f'<a href="{esc(url)}" target="_blank">{esc(vista(url, 44))}</a>')
    if f.get("correo") and not renglon:
        datos.append(f'<a href="mailto:{esc(f["correo"])}">{esc(f["correo"])}</a>')
    tel = "" if renglon else telefonos(f)
    if tel:
        datos.append(esc(tel))
    return (
        f'<div class="gu-ficha"><div class="gu-nom">{esc(f["nombre"])}</div>'
        + (f'<div class="gu-que">{esc(f["que"])}</div>' if f.get("que") else "")
        + (f'<div class="gu-como"><b>Cómo:</b> {esc(f["como"])}</div>' if f.get("como") and not renglon else "")
        + (f'<div class="gu-datos">{" · ".join(datos)}</div>' if datos else "")
        + "</div>"
    )


def apartados_html(apartados):
    """[(apartado, fichas)] en pantalla, cada apartado con su rótulo."""
    trozos = []
    for apartado, suyas in apartados:
        trozos.append(f'<div class="gu-apartado">{esc(apartado)}</div>')
        trozos += [ficha_html(f) for f in suyas]
    return "".join(trozos)


# ---------------------------------------------------------------------------
# La lista para imprimir
# ---------------------------------------------------------------------------
# Se imprime a menudo en blanco y negro, como la guía: todo en negro y grises,
# sin fondos. Dos columnas para que una lista de sesenta fichas no se vaya a
# quince hojas. Los enlaces se pueden pulsar en el PDF y se leen en el papel.

AVISOS = [
    ("Primero, llama.", "Un currículum enviado a un correo general (info@, contacto@) se pierde "
     "con facilidad. Antes de enviarlo, llama y pide un correo concreto: el de recursos "
     "humanos o, mejor, el de la persona que lleva la selección."),
    ("Casi todo entra por internet.", "La mayoría de las empresas solo recoge candidaturas en "
     "su portal de empleo. Donde lo hay, la ficha te lleva a él."),
    ("Mira primero la web.", "Las direcciones y los horarios cambian: confírmalo antes de "
     "desplazarte."),
    ("Mejor diez candidaturas pensadas que cien iguales.", ""),
]

LLAMADA = ("Buenos días, me llamo {nombre}. Busco trabajo de {puesto} y me gustaría "
           "enviarles mi currículum. ¿A qué persona o a qué correo se lo puedo dirigir "
           "para que llegue a quien hace la selección?")

_FUENTES = (
    ("Carlito", "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
                "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
    ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


def _fuentes():
    """(regular, negrita): Carlito, la del protocolo, si está; si no, DejaVu o Helvetica."""
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for nombre, regular, negrita in _FUENTES:
        if os.path.exists(regular) and os.path.exists(negrita):
            try:
                if nombre not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(nombre, regular))
                    pdfmetrics.registerFont(TTFont(f"{nombre}-B", negrita))
                    # Sin esto, el <b> de los párrafos no encuentra la negrita.
                    for cursiva in (0, 1):
                        addMapping(nombre, 0, cursiva, nombre)
                        addMapping(nombre, 1, cursiva, f"{nombre}-B")
                return nombre, f"{nombre}-B"
            except Exception:  # noqa: BLE001
                continue
    return "Helvetica", "Helvetica-Bold"


def pdf(secciones_, titulo, subtitulo="", puesto="", nombre=""):
    """La lista para imprimir. Devuelve bytes.

    `puesto` y `nombre` rellenan el guion de la llamada; si faltan, quedan
    los huecos entre corchetes, como en la guía.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, FrameBreak, KeepTogether,
                                    NextPageTemplate, PageTemplate, Paragraph, Spacer)

    regular, negrita = _fuentes()
    gris = colors.HexColor("#555555")
    linea = colors.HexColor("#999999")

    def estilo(pt, fuente=regular, color=colors.black, **k):
        k.setdefault("leading", pt * 1.22)
        return ParagraphStyle("x", fontName=fuente, fontSize=pt, textColor=color, **k)

    e_titulo = estilo(17, negrita, leading=20)
    e_sub = estilo(10, color=gris, spaceAfter=6)
    e_sector = estilo(11.5, negrita, spaceBefore=4, spaceAfter=1)
    e_apartado = estilo(8.6, negrita, color=gris, spaceBefore=5, spaceAfter=2)
    e_nombre = estilo(9, negrita)
    e_texto = estilo(7.9, color=colors.HexColor("#222222"))
    e_dato = estilo(7.9)

    margen = 1.3 * cm
    ancho, alto = A4
    hueco = 0.7 * cm
    col = (ancho - 2 * margen - hueco) / 2
    pie = 1.0 * cm

    def columnas(arriba):
        return [Frame(margen + i * (col + hueco), margen + pie, col, alto - arriba - margen - pie,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
                for i in range(2)]

    def al_pie(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, 7)
        canvas.setFillColor(gris)
        canvas.drawString(margen, margen * 0.7,
                          f"Datos de «{EDICION['titulo_empresas']}», de {EDICION['autor']} · "
                          f"{EDICION['edicion'].lower()}, comprobados en {EDICION['verificado']}.")
        canvas.drawRightString(ancho - margen, margen * 0.7, f"{doc.page}")
        canvas.restoreState()

    # La cabecera (título, avisos y guion) va a todo lo ancho de la primera
    # hoja y las fichas, a dos columnas debajo. Se mide antes de montar la
    # página: con Carlito ocupa menos que con DejaVu, y un hueco fijo dejaba
    # un blanco en medio de la hoja.
    cabecera = _cabecera(titulo, subtitulo, puesto, nombre, ancho - 2 * margen,
                         estilo, e_titulo, e_sub, linea, gris)
    alto_cab = sum(f.wrap(ancho - 2 * margen, alto)[1] + f.getSpaceBefore() + f.getSpaceAfter()
                   for f in cabecera) + 6
    primera = [Frame(margen, alto - margen - alto_cab, ancho - 2 * margen, alto_cab,
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)]
    primera += columnas(margen + alto_cab + 0.5 * cm)

    salida = io.BytesIO()
    doc = BaseDocTemplate(salida, pagesize=A4, leftMargin=margen, rightMargin=margen,
                          topMargin=margen, bottomMargin=margen, title=titulo,
                          author=EDICION["autor"], subject=EDICION["titulo_empresas"])
    doc.addPageTemplates([PageTemplate("primera", primera, onPage=al_pie),
                          PageTemplate("resto", columnas(margen), onPage=al_pie)])

    flujo = [NextPageTemplate("resto")] + cabecera + [FrameBreak()]

    for s in secciones_:
        cab = [CondPageBreak(3 * cm), Paragraph(_esc(s["titulo"]), e_sector)]
        if s.get("general"):
            cab.append(Paragraph("La guía no tiene un sector para este puesto: empieza por los "
                                 "portales generalistas y las grandes redes de trabajo temporal.",
                                 e_texto))
        primera_del_sector = True
        for apartado, suyas in s["apartados"]:
            bloque = cab if primera_del_sector else []
            primera_del_sector = False
            bloque.append(Paragraph(_esc(apartado), e_apartado))
            for i, f in enumerate(suyas):
                ficha = _ficha_pdf(f, e_nombre, e_texto, e_dato)
                if i == 0:                       # el rótulo no se queda solo al pie
                    flujo.append(KeepTogether(bloque + ficha))
                else:
                    flujo.append(KeepTogether(ficha))
        flujo.append(Spacer(1, 4))

    doc.build(flujo)
    return salida.getvalue()


def _cabecera(titulo, subtitulo, puesto, nombre, ancho, estilo, e_titulo, e_sub, linea, gris):
    """Título, avisos de la guía y el guion de la llamada con el puesto ya puesto."""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    e_aviso = estilo(8.6, spaceAfter=2)
    e_modelo = estilo(8.6, leftIndent=8, spaceAfter=2)
    partes = [Paragraph(_esc(titulo), e_titulo)]
    if subtitulo:
        partes.append(Paragraph(_esc(subtitulo), e_sub))
    avisos = [Paragraph(f"<b>{_esc(t)}</b> {_esc(x)}", e_aviso) for t, x in AVISOS]
    llamada = LLAMADA.format(nombre=_esc(nombre) or "[tu nombre]",
                             puesto=_esc(puesto) or "[puesto]")
    guion = [Paragraph("<b>Qué decir por teléfono</b>", e_aviso),
             Paragraph(f"«{llamada}»", e_modelo),
             Paragraph("Apunta el nombre y el correo, y repítelos para comprobar que están bien. "
                       "Pregunta también con quién has hablado.", e_aviso)]
    tabla = Table([[avisos, guion]], colWidths=[ancho * 0.52, ancho * 0.48])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, linea),
        ("LINEBEFORE", (1, 0), (1, 0), 0.4, linea),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    partes += [tabla, Spacer(1, 3),
               Paragraph("Que una empresa salga aquí no garantiza que tenga vacantes: es el canal "
                         "por el que recoge candidaturas.", estilo(7.5, color=gris))]
    return partes


def _ficha_pdf(f, e_nombre, e_texto, e_dato):
    from reportlab.platypus import Paragraph, Spacer
    partes = [Paragraph(_esc(f["nombre"]), e_nombre)]
    if f.get("que"):
        partes.append(Paragraph(_esc(f["que"]), e_texto))
    if f.get("como") and f.get("formato") != "renglon":
        partes.append(Paragraph(f"<b>Cómo:</b> {_esc(f['como'])}", e_texto))
    datos = []
    url, rotulo = enlace(f)
    if url:
        datos.append(f'{rotulo}: <a href="{_esc(url)}">{_esc(vista(url, 52))}</a>')
    if f.get("correo") and f.get("formato") != "renglon":
        datos.append(f'<a href="mailto:{_esc(f["correo"])}">{_esc(f["correo"])}</a>')
    tel = telefonos(f) if f.get("formato") != "renglon" else ""
    if tel:
        datos.append(f"Tel. {_esc(tel)}")
    if datos:
        partes.append(Paragraph(" · ".join(datos), e_dato))
    dire = direccion(f) if f.get("formato") != "renglon" else ""
    if dire:
        transporte = f" · {f['transporte']}" if f.get("transporte") else ""
        partes.append(Paragraph(_esc(dire + transporte), e_texto))
    partes.append(Spacer(1, 4))
    return partes
