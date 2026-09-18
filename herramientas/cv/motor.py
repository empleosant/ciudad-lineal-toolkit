"""
Motor del generador de CV. Python puro: no importa Streamlit.

El currículo es un diccionario plano (ver `nuevo()`), con dos listas de
fichas: experiencias y formación. Aquí vive todo lo que no dibuja:

    a_oracion(denominacion)   nombre de catálogo -> nombre para el currículo
    compone(texto, ...)       los botones de «Otros datos», escritos en el texto
    ordena_por_fechas(fichas) más reciente primero
    texto_plano(cv)           vista previa en texto
    documento_docx(cv)        el Word sobre el modelo de la oficina (ver plantilla.py)
    documento_pdf(cv)         el PDF, réplica del modelo, una página
"""

import io
import re



def nuevo():
    return {
        "nombre": "", "telefono": "", "email": "", "localidad": "",
        "permiso": "", "disponibilidad": "",
        "objetivo": "",
        "experiencias": [],
        "formacion": [],
        "idiomas": "", "informatica": "", "otros": "",
        "todas_experiencias": False,   # forzar que entren todas aunque baje la letra
    }


def experiencia(codigo="", denominacion="", motivo=""):
    """Una ficha de experiencia. `codigo` es el SISPE si viene del codificador."""
    return {
        "codigo": codigo,
        "denominacion": denominacion,
        "motivo": motivo,
        "sector": "",
        "puesto": a_oracion(denominacion) if denominacion else "",
        "contexto": "",
        "funciones": "",
        "desde": "",
        "hasta": "",
    }


def formacion(titulo="", centro="", anio=""):
    return {"titulo": titulo, "centro": centro, "anio": anio}

# ---------------------------------------------------------------------------
# BOTONES DE «OTROS DATOS»
# ---------------------------------------------------------------------------
# Los apartados de «Otros datos de interés» -permiso, idiomas, informática,
# disponibilidad- son campos de texto libre, y así siguen siendo: es lo que se
# imprime. Lo que hacen los botones de la pantalla es ESCRIBIR EN ESE TEXTO las
# frases de siempre, para no tener que teclear «Carnet de conducir B.» veinte
# veces al día ni discutir cada vez si se escribe «carnet» o «carné».
#
# Por eso no hay un dato nuevo que guardar ni que exportar: el texto sigue
# siendo la única fuente: lo que está marcado se deduce de lo que hay escrito
# (`marcadas`), y al marcar o desmarcar se recompone (`compone`). Quien
# prefiera escribirlo a mano puede seguir haciéndolo, y lo que escriba no se
# toca.

PERMISOS = ["B", "A (moto)", "C (camión)", "C+E (tráiler)", "D (autobús)", "Vehículo propio"]

IDIOMAS = ["Español", "Inglés", "Francés", "Árabe", "Rumano", "Ucraniano",
           "Portugués", "Chino"]
NIVELES_IDIOMA = ["nativo", "alto", "medio", "básico"]

INFORMATICA = ["correo electrónico", "internet", "Word", "Excel",
               "aplicaciones del móvil", "redes sociales", "TPV (caja registradora)",
               "ofimática a nivel usuario"]

DISPONIBILIDAD = [
    "Incorporación inmediata.",
    "Disponibilidad horaria completa.",
    "Disponibilidad para turnos rotativos.",
    "Disponibilidad para trabajar los fines de semana.",
    "Preferencia por la jornada de mañana.",
    "Preferencia por la jornada de tarde.",
]

OTROS_DATOS = [
    "Certificado de manipulador de alimentos.",
    "Carné de carretillero.",
    "Formación en prevención de riesgos laborales.",
    "Certificado de discapacidad.",
    "Certificado de delitos de naturaleza sexual.",
]


def frase_permiso(etiqueta):
    """«B» -> «Carnet de conducir B.»; «Vehículo propio» va tal cual."""
    if etiqueta == "Vehículo propio":
        return "Vehículo propio."
    return f"Carnet de conducir {etiqueta.split(' ')[0]}."


def frase_idioma(idioma, nivel):
    """«Inglés» + «básico» -> «Inglés básico.», como el modelo de la oficina."""
    return f"{idioma} {nivel}."


def frase_informatica(elegidas):
    """Una sola frase con la lista, que es como está escrito el modelo:
    «Manejo de correo electrónico, Word y Excel.»"""
    partes = [e for e in INFORMATICA if e in elegidas]
    if not partes:
        return ""
    if len(partes) == 1:
        cuerpo = partes[0]
    else:
        cuerpo = ", ".join(partes[:-1]) + " y " + partes[-1]
    return f"Manejo de {cuerpo}."


def catalogo_permisos():
    return [frase_permiso(p) for p in PERMISOS]


def catalogo_idiomas():
    """Todas las combinaciones. Hacen falta enteras para poder LIMPIAR: si el
    nivel cambia de «básico» a «medio», hay que quitar la frase anterior."""
    return [frase_idioma(i, n) for i in IDIOMAS for n in NIVELES_IDIOMA]


def catalogo_informatica():
    """Lo mismo, pero aquí la frase es una lista y las combinaciones son
    demasiadas: se limpia por el principio, que es fijo."""
    return []


def marcadas(texto, catalogo):
    """Las frases del catálogo que ya están escritas, en el orden del catálogo."""
    texto = texto or ""
    return [f for f in catalogo if f in texto]


def _limpia(texto):
    """Espacios y saltos sobrantes de haber quitado frases por el medio."""
    texto = re.sub(r"[ \t]+", " ", texto or "")
    texto = re.sub(r" *\n{2,} *", "\n", texto)
    return texto.strip(" \n")


def compone(texto, elegidas, catalogo, salto=False):
    """Deja en el texto EXACTAMENTE las frases `elegidas` del catálogo.

    Lo que la persona haya escrito a mano y no esté en el catálogo se conserva
    intacto y se queda detrás. Marcar y desmarcar es reversible, y volver a
    componer con lo mismo no cambia nada.

    `salto` separa por líneas en vez de por espacios: «Otros datos» es un
    apartado por línea (así lo lee `texto_plano` y así lo pinta la plantilla).
    """
    resto = texto or ""
    for frase in catalogo:
        resto = resto.replace(frase, "")
    resto = _limpia(resto)
    piezas = [f for f in elegidas if f]
    if resto:
        piezas.append(resto)
    return ("\n" if salto else " ").join(piezas)


def nivel_de(texto, idioma):
    """El nivel con el que está escrito ese idioma, o None si no está.

    Se mira de más específico a menos para que «Español nativo» no se confunda
    con nada: los niveles no comparten palabras, pero el orden fijo evita
    sorpresas si algún día se añade uno compuesto.
    """
    for nivel in NIVELES_IDIOMA:
        if frase_idioma(idioma, nivel) in (texto or ""):
            return nivel
    return None


def idiomas_de(texto):
    """[(idioma, nivel), ...] tal como están escritos ahora."""
    return [(i, nivel_de(texto, i)) for i in IDIOMAS if nivel_de(texto, i)]


def informatica_de(texto):
    """Las piezas de la frase de informática que ya están escritas."""
    return [e for e in INFORMATICA if e in (texto or "")]


def compone_informatica(texto, elegidas):
    """Rehace la frase de informática conservando lo escrito a mano.

    No se puede limpiar por catálogo como los demás -las combinaciones de la
    lista son demasiadas-, así que se quita la frase entera que empieza por
    «Manejo de» y se vuelve a montar.
    """
    resto = re.sub(r"Manejo de [^.]*\.", "", texto or "")
    resto = _limpia(resto)
    frase = frase_informatica(elegidas)
    return " ".join(x for x in (frase, resto) if x)




SUELTAS_ES = ("r", "n", "l", "d", "s", "z", "j")


def a_oracion(denom):
    """Pasa la denominación oficial a algo que se pueda poner en un CV.

    El catálogo va en MAYÚSCULAS y en plural ("CAMAREROS DE PISO"), porque así
    consta oficialmente y así debe verse en el codificador. Pero un currículo
    se escribe en singular y en tipo oración ("Camarero de piso"). El singular
    es aproximado a propósito: el campo queda editable y la persona lo ajusta.
    """
    base = re.sub(r"\s*\([^)]*\)", "", denom or "").strip().lower()
    base = re.sub(r",?\s*(en general|en gral\.?|n\.c\.o\.p\.?)\s*$", "", base).strip()
    base = base.strip(" ,;")
    if not base:
        return ""

    def singular(palabra):
        if palabra.endswith("es") and len(palabra) > 4 and palabra[-3] in SUELTAS_ES:
            return palabra[:-2]
        if palabra.endswith("s") and len(palabra) > 3:
            return palabra[:-1]
        return palabra

    piezas = base.split()
    piezas[0] = "-".join(singular(x) for x in piezas[0].split("-"))
    return " ".join(piezas).capitalize()


def anio(texto):
    """El último año de cuatro cifras que aparezca en el texto, o 0."""
    m = re.findall(r"(?:19|20)\d{2}", texto or "")
    return int(m[-1]) if m else 0


def ordena_por_fechas(fichas):
    """Más reciente primero, que es como se lee un currículo.

    Las que no tienen ningún año se quedan al final y conservan el orden en
    que se añadieron, para poder colocarlas a mano con las flechas.
    """
    fichas.sort(
        key=lambda e: (
            0 if (anio(e.get("hasta")) or anio(e.get("desde"))) else 1,
            -(anio(e.get("hasta")) or anio(e.get("desde"))),
            -anio(e.get("desde")),
        ),
    )


def titulo_experiencia(e):
    return e.get("puesto") or a_oracion(e.get("denominacion", "")) or "Experiencia sin nombre"


def periodo(e):
    if not (e.get("desde") or e.get("hasta")):
        return ""
    rango = " - ".join(x for x in (e.get("desde", ""), e.get("hasta", "")) if x)
    a1, a2 = anio(e.get("desde")), anio(e.get("hasta"))
    if a1 and a2 and a2 >= a1:
        n = max(1, a2 - a1)
        return f"{n} año{'s' if n != 1 else ''} - {rango}"
    return rango


def _sectores_que_agrupan(experiencias):
    # El sector solo es un agrupador: se escribe si reúne dos o más puestos.
    # Con uno solo sería un título para una línea, que gasta espacio sin
    # aportar nada, y en un currículo de una página el espacio es el límite.
    cuenta = {}
    for e in experiencias:
        s = (e.get("sector") or "").strip().upper()
        if s:
            cuenta[s] = cuenta.get(s, 0) + 1
    return {k for k, v in cuenta.items() if v >= 2}


def experiencias_agrupadas(experiencias):
    """[(sector o None, ficha), ...] con las fichas de cada sector juntas.

    Como en el modelo de la oficina: un bloque por sector (rótulo solo en la
    primera ficha), en el orden en que aparece cada sector; dentro del bloque
    se respeta el orden de la lista (normalmente, por fechas). Las fichas de
    sectores que no agrupan van sueltas, sin rótulo, donde les toque.
    """
    agrupan = _sectores_que_agrupan(experiencias)
    salida, hechos = [], set()
    for e in experiencias:
        sector = (e.get("sector") or "").strip().upper()
        if sector not in agrupan:
            salida.append((None, e))
        elif sector not in hechos:
            hechos.add(sector)
            bloque = [x for x in experiencias if (x.get("sector") or "").strip().upper() == sector]
            salida.append((sector, bloque[0]))
            salida.extend((None, x) for x in bloque[1:])
    return salida


def contacto(cv):
    piezas = [cv.get("telefono"), cv.get("email"), cv.get("localidad")]
    return "  ·  ".join(p.strip() for p in piezas if p and p.strip())


def texto_plano(cv):
    lineas = []
    if cv.get("nombre"):
        lineas += [cv["nombre"].upper(), contacto(cv), ""]
    if cv.get("experiencias"):
        lineas.append("EXPERIENCIA LABORAL")
        for sector, e in experiencias_agrupadas(cv["experiencias"]):
            if sector:
                lineas.append(f"\n{sector}")
            p = periodo(e)
            lineas.append(f"·   {titulo_experiencia(e)}{f' ({p})' if p else ''}")
            if e.get("contexto"):
                lineas.append(e["contexto"])
            if e.get("funciones"):
                lineas.append(f"Funciones: {e['funciones']}")
        lineas.append("")
    if cv.get("formacion"):
        lineas.append("FORMACIÓN")
        for f in cv["formacion"]:
            detalle = " · ".join(x for x in (f.get("centro"), f.get("anio")) if x)
            lineas.append(f"·   {f.get('titulo', '')}{f' ({detalle})' if detalle else ''}")
        lineas.append("")
    otros = []
    if cv.get("idiomas"):
        otros.append(f"Idiomas: {cv['idiomas']}")
    if cv.get("informatica"):
        otros.append(f"Informática: {cv['informatica']}")
    otros += [x for x in (cv.get("permiso"), cv.get("disponibilidad")) if x]
    otros += [x.strip() for x in (cv.get("otros") or "").splitlines() if x.strip()]
    if cv.get("objetivo"):
        otros.append(cv["objetivo"].strip())
    if otros:
        lineas.append("OTROS DATOS DE INTERÉS")
        lineas += [f"·   {o}" for o in otros]
    return "\n".join(lineas).strip()


# ---------------------------------------------------------------------------
# PDF: réplica del modelo de la oficina, con reportlab
# ---------------------------------------------------------------------------
# Trebuchet MS es de Microsoft y no está en el servidor: el PDF usa DejaVu
# Sans, parecida en espíritu. El Word lleva la fuente exacta del modelo.

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate
from xml.sax.saxutils import escape as _esc

_AZUL = colors.HexColor("#3366FF")
_FUENTE, _FUENTE_B = "Helvetica", "Helvetica-Bold"
try:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    _FUENTE, _FUENTE_B = "DejaVu", "DejaVu-Bold"
except Exception:  # noqa: BLE001
    pass

_MARGEN = 567 / 20   # 1 cm, como el modelo


def _estilo(pt, negrita=False, izq=0, primera=0, antes=0, despues=0, mult=1.0, **k):
    return ParagraphStyle(
        "x", fontName=_FUENTE_B if negrita else _FUENTE, fontSize=pt, leading=pt * 1.17 * mult,
        leftIndent=izq, firstLineIndent=primera, spaceBefore=antes, spaceAfter=despues, **k,
    )


def _pdf_bloques(bloques, f):
    from herramientas.cv.plantilla import _METRICA
    flujo, primera_cabecera = [], True
    for tipo, datos in bloques:
        pt, negrita, sangria, antes, despues, mult = _METRICA[tipo]
        if tipo == "cabecera" and primera_cabecera:
            antes, primera_cabecera = _METRICA["cabecera1"][3], False
        pt *= f
        if tipo == "nombre":
            flujo.append(Paragraph(_esc(datos), _estilo(pt, True, despues=despues, mult=mult)))
        elif tipo == "contacto":
            flujo.append(Paragraph(_esc(datos), _estilo(pt, izq=sangria, mult=mult)))
        elif tipo == "cabecera":
            flujo.append(Paragraph(
                f'<font color="white">{_esc(datos)}</font>',
                _estilo(pt, antes=antes, despues=despues, mult=mult, backColor=_AZUL, borderPadding=(1, 2, 2, 2)),
            ))
        elif tipo == "sector":
            flujo.append(Paragraph(f"<u>{_esc(datos)}</u>", _estilo(pt, izq=sangria, antes=antes, despues=despues, mult=mult)))
        elif tipo == "experiencia":
            titulo, (a, fechas, c) = datos
            cola = f" {_esc(a)}<i>{_esc(fechas)}</i>{_esc(c)}" if fechas else ""
            flujo.append(Paragraph(
                f"<b>{_esc(titulo)}</b>{cola}",
                _estilo(pt, izq=sangria, antes=antes, mult=mult, bulletIndent=sangria - 18, bulletFontSize=pt),
                bulletText="•",
            ))
        elif tipo == "empresa":
            flujo.append(Paragraph(_esc(datos), _estilo(pt, izq=0, primera=35.45, mult=mult, alignment=4)))
        elif tipo == "funciones":
            flujo.append(Paragraph(_esc(datos), _estilo(pt, izq=sangria, mult=mult, alignment=4)))
        elif tipo == "formacion":
            titulo, centro, anio = datos
            texto = f"<b>{_esc(titulo)}" + (" –</b>" if (centro or anio) else "</b>")
            if centro:
                texto += f" <i>{_esc(centro)}{',' if anio else ''}</i>"
            if anio:
                texto += f" {_esc(anio)}."
            flujo.append(Paragraph(texto, _estilo(pt, izq=sangria, antes=antes, mult=mult,
                                                  bulletIndent=sangria - 18, bulletFontSize=pt), bulletText="•"))
        elif tipo == "otros":
            flujo.append(Paragraph(_esc(datos), _estilo(pt, izq=sangria, antes=antes, mult=mult,
                                                        bulletIndent=sangria - 16, bulletFontSize=pt * 0.75), bulletText="•"))
    return flujo


def documento_pdf(cv):
    """El currículo en PDF, réplica del modelo. Devuelve bytes. Una página."""
    from herramientas.cv import plantilla
    decision = plantilla.decide(cv)
    bloques, f = decision["bloques"], decision["factor"]
    while True:
        salida = io.BytesIO()
        doc = SimpleDocTemplate(
            salida, pagesize=A4, leftMargin=_MARGEN, rightMargin=_MARGEN,
            topMargin=_MARGEN, bottomMargin=_MARGEN,
            title=(cv.get("nombre") or "Currículo").strip(), author="", subject="Currículo",
        )
        doc.build(_pdf_bloques(bloques, f))
        if doc.page <= 1 or f <= plantilla.FACTOR_MINIMO:
            return salida.getvalue()
        f = round(f - 0.02, 2)


def documento_docx(cv):
    """El currículo en Word sobre el modelo de la oficina. Devuelve bytes."""
    from herramientas.cv import plantilla
    return plantilla.genera(cv)[0]
