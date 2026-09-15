"""
Motor del generador de informes de orientación. Python puro: no importa Streamlit.

    limpia_datos_personales(texto)    tacha identificadores y dice qué encontró
    en_horario_laboral(ahora)         lunes a viernes, de 8:30 a 14:30
    nombre_archivo(rasgo)             Preparacion_sesion_<rasgo>
    documento_pdf(ficha)              el documento de dos páginas A4, en bytes
    texto_de_la_sesion(datos)         lo recogido en la sala, en texto para la IA
    fila_calibracion(datos)           la fila de la hoja de calibración, en CSV

El documento sale SIEMPRE en dos páginas: si el contenido se pasa, se baja la
letra hasta que quepa, igual que hace el generador de CV con su página única.
"""

import csv
import io
import os
import re
from datetime import datetime

from comun.texto import normaliza

# ---------------------------------------------------------------------------
# Lo que no debe salir de la sala
# ---------------------------------------------------------------------------
# El protocolo pide el CV ya anonimizado —y en la Comunidad de Madrid el CV
# solo puede subirse a Teams—, pero llega como llega. Los identificadores se
# tachan antes de que el texto salga hacia la IA; la direccion solo se avisa,
# porque tacharla se llevaria por delante la localidad, y la localidad es
# diagnostico. El nombre propio no hay forma de detectarlo: eso se avisa aparte.

PERSONALES = (
    ("correo electrónico", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), True),
    ("teléfono", re.compile(
        r"(?<!\d)(?:\+34[\s.-]?)?[6-9]\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)"), True),
    ("DNI o NIE", re.compile(
        r"(?<![\w-])(?:\d{8}[-\s]?[A-Za-z]|[XYZxyz][-\s]?\d{7}[-\s]?[A-Za-z])(?![\w-])"), True),
    ("dirección postal", re.compile(
        r"(?i)\b(?:c/|calle|avda\.?|avenida|paseo|plaza|pza\.?|travesía|carretera)\b"
        r"[^\n]{0,40}?\bn?[ºo]?\s?\d{1,3}\b"), False),
)

TACHADO = "[dato retirado]"


def limpia_datos_personales(texto):
    """(texto sin identificadores, [qué se encontró]).

    Las fechas, las empresas, las localidades y las titulaciones se quedan:
    de ahi sale el diagnostico.
    """
    limpio, hallazgos = texto or "", []
    for etiqueta, patron, borrar in PERSONALES:
        if not patron.search(limpio):
            continue
        hallazgos.append(etiqueta)
        if borrar:
            limpio = patron.sub(TACHADO, limpio)
    return limpio, hallazgos


def en_horario_laboral(ahora=None):
    """Lunes a viernes de 8:30 a 14:30, hora de Madrid."""
    if ahora is None:
        try:
            from zoneinfo import ZoneInfo
            ahora = datetime.now(ZoneInfo("Europe/Madrid"))
        except Exception:  # noqa: BLE001
            ahora = datetime.now()
    if ahora.weekday() > 4:
        return False
    return 510 <= ahora.hour * 60 + ahora.minute < 870


def nombre_archivo(rasgo):
    """El documento se nombra por el rasgo del perfil, nunca por la persona.

    Y sin sufijo de version: se sustituye el fichero entero.
    """
    base = re.sub(r"[^a-z0-9]+", "_", normaliza(rasgo or "")).strip("_")
    return f"Preparacion_sesion_{base or 'perfil'}"


# ---------------------------------------------------------------------------
# Lo que se recoge en la sala
# ---------------------------------------------------------------------------

# Los cuatro primeros condicionan todo lo demas: sin ellos, cualquier
# itinerario que se dibuje encima puede ser inviable.
BLOQUES_SESION = (
    ("documental", "Situación documental", True,
     "Nacionalidad, autorización de trabajo, trámite en curso y plazos, "
     "homologación de titulaciones. Tipo de demanda dada de alta."),
    ("economica", "Situación económica", True,
     "Prestación o subsidio y fecha de fin, u otros ingresos. Fija el horizonte "
     "de planificación y decide si hace falta un empleo puente."),
    ("duros", "Condicionantes duros", True,
     "Cargas de cuidado, salud y limitaciones físicas, discapacidad reconocida, "
     "situación habitacional."),
    ("marco", "Marco real de la búsqueda", True,
     "Disponibilidad horaria verdadera, no la declarada. Turnos que acepta, radio "
     "de desplazamiento, carné y vehículo, idiomas funcionales."),
    ("digital", "Competencia digital real", False,
     "Correo funcional o solo móvil, capacidad de inscribirse en portales, de usar "
     "la sede electrónica. Decide qué se le puede pedir que haga."),
    ("herramientas", "Herramientas con nombre y apellidos", False,
     "Sistemas de gestión, nivel real de Excel, maquinaria, carnés. Sin esto no se "
     "puede reescribir un CV que compita."),
    ("busqueda", "Búsqueda hasta ahora", False,
     "Cuántas candidaturas, por qué canal, con qué respuesta, y cómo consiguió sus "
     "empleos anteriores. Si todos salieron por contacto personal, ese es el canal "
     "a reforzar y no los portales."),
)

MOTIVACIONES = ("Sin anotar", "Activa", "Desgastada", "Desenganchada")
ENCAJES = ("Sin anotar", "Sí", "A medias", "No")

ENTREGABLES = (
    ("cv", "Reescritura del CV",
     "Versiones completas, listas para copiar y pegar, una por dirección "
     "profesional u organización destinataria."),
    ("empresas", "Listado de empresas de Madrid para autocandidatura",
     "Por dirección profesional."),
    ("formacion", "Formación",
     "Solo si el objetivo ya está fijado y la formación es corta, acreditada y con "
     "retorno claro. Se ofrece el buscador y cómo inscribirse, no un curso elegido "
     "por nosotros."),
    ("proximidad", "Recursos de proximidad y programas de colectivo",
     "Verificados y con plazo abierto."),
)


def texto_de_la_sesion(datos):
    """Lo anotado en la fase 2, en texto corrido para mandárselo a la IA."""
    piezas = []
    for clave, rotulo, _, _ in BLOQUES_SESION:
        valor = (datos.get(clave) or "").strip()
        if valor:
            piezas.append(f"{rotulo}: {valor}")
    motivacion = datos.get("motivacion") or MOTIVACIONES[0]
    if motivacion != MOTIVACIONES[0]:
        piezas.append(f"Motivación observada: {motivacion.lower()}")
    for clave, rotulo in (("objetivo1", "Objetivo principal elegido"),
                          ("objetivo2", "Objetivo secundario")):
        valor = (datos.get(clave) or "").strip()
        if valor:
            piezas.append(f"{rotulo}: {valor}")
    return "\n".join(piezas)


def trayectoria_desde_cv(cv):
    """El currículo en curso pasado a texto, sin nombre ni contacto.

    La lectura de la fase 1 necesita cronologia con fechas, sitios y
    titulaciones; lo que no necesita, y no puede llevar, es quien es la
    persona. El asesor de formacion arma su propio perfil con otro enfasis:
    aqui manda la trayectoria, alli los intereses y las limitaciones.
    """
    partes = []
    if cv.get("objetivo"):
        partes.append(f"Objetivo declarado: {cv['objetivo']}")
    if cv.get("localidad"):
        partes.append(f"Localidad: {cv['localidad']}")
    partes.append("\nExperiencia, de lo más reciente a lo más antiguo:")
    for e in cv.get("experiencias", []):
        puesto = (e.get("puesto") or e.get("denominacion") or "").strip()
        if not puesto:
            continue
        fechas = " - ".join(x for x in (e.get("desde"), e.get("hasta")) if x)
        linea = f"- {puesto}" + (f" ({fechas})" if fechas else " (sin fechas)")
        if e.get("sector"):
            linea += f". Sector: {e['sector']}"
        if e.get("contexto"):
            linea += f". Dónde: {e['contexto']}"
        if e.get("funciones"):
            linea += f". Funciones: {e['funciones']}"
        partes.append(linea)
    formacion = [f for f in cv.get("formacion", []) if f.get("titulo")]
    if formacion:
        partes.append("\nFormación:")
        for f in formacion:
            cola = ", ".join(x for x in (f.get("centro"), f.get("anio")) if x)
            partes.append(f"- {f['titulo']}" + (f" ({cola})" if cola else ""))
    otros = [(r, cv.get(c)) for r, c in (
        ("Idiomas", "idiomas"), ("Informática", "informatica"),
        ("Permiso de conducir", "permiso"), ("Disponibilidad", "disponibilidad"),
        ("Otros datos", "otros"),
    ) if cv.get(c)]
    if otros:
        partes.append("")
        partes += [f"{rotulo}: {valor}" for rotulo, valor in otros]
    return "\n".join(partes).strip()


def fila_calibracion(datos):
    """La fila para la hoja de calibración de la matriz, en CSV.

    Sin esto la matriz no mejora: hace falta saber qué casilla se acabó
    asignando y si el caso encajaba de verdad en esa tipología.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(["casilla", "motivacion", "encajaba", "objetivo"])
    escritor.writerow([
        (datos.get("casilla") or "").strip(),
        datos.get("motivacion") or "",
        datos.get("encaje") or "",
        (datos.get("objetivo1") or "").strip(),
    ])
    return buffer.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------------
# El documento de dos páginas, con reportlab
# ---------------------------------------------------------------------------
# Las medidas son las del protocolo: caja de texto de 178 mm, márgenes de
# 16 mm, 17 mm arriba y 13 mm abajo, cuerpo de 9,2 pt con interlineado 1,48.
#
# El anexo del protocolo describe la otra cadena, HTML -> wkhtmltopdf, con su
# factor de 1,307 para compensar que wkhtmltopdf maquete a 1038 px en vez de a
# 794. Aqui NO se aplica y no debe aplicarse: reportlab dibuja en puntos y los
# milimetros son milimetros. Con el factor, el documento saldria un tercio mas
# grande y en cuatro paginas.
#
# Caladea y Carlito son las del protocolo, pero no estan en el servidor: si no
# aparecen se usa DejaVu (serif para titulos, sans para texto), como hace el
# generador de CV con Trebuchet. DejaVu es mas ancha, asi que el texto corre
# mas; para eso esta el ajuste a dos paginas.

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, PageBreak, PageTemplate, Paragraph, Spacer,
    Table, TableStyle,
)
from xml.sax.saxutils import escape as _esc

VERDE = colors.HexColor("#2E5E4E")
TEXTO = colors.HexColor("#26251F")
SECUNDARIO = colors.HexColor("#55524A")
FILETE = colors.HexColor("#D6D2C6")
ALTERNA = colors.HexColor("#F7F5EF")
AVISO_FONDO = colors.HexColor("#FBF2EC")
AVISO_FILETE = colors.HexColor("#B15A2B")

MARGEN_LADO, MARGEN_ALTO, MARGEN_PIE = 16 * mm, 17 * mm, 13 * mm
ANCHO_UTIL = A4[0] - MARGEN_LADO * 2        # 178 mm
CUERPO = 9.2
INTERLINEADO = 1.48
FACTOR_MINIMO = 0.78        # por debajo de esto ya no se lee cómodo en papel

_FAMILIAS = {
    "titulo": (
        ("Caladea", "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf",
                    "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"),
        ("DejaVuSerif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    ),
    "texto": (
        ("Carlito", "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
                    "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
}
_RESERVA = {"titulo": ("Times-Roman", "Times-Bold"), "texto": ("Helvetica", "Helvetica-Bold")}


def _registra(papel):
    """(regular, negrita) de la primera familia que esté instalada."""
    for nombre, regular, negrita in _FAMILIAS[papel]:
        if not (os.path.exists(regular) and os.path.exists(negrita)):
            continue
        try:
            pdfmetrics.registerFont(TTFont(nombre, regular))
            pdfmetrics.registerFont(TTFont(f"{nombre}-B", negrita))
            return nombre, f"{nombre}-B"
        except Exception:  # noqa: BLE001
            continue
    return _RESERVA[papel]


TITULO_R, TITULO_B = _registra("titulo")
TEXTO_R, TEXTO_B = _registra("texto")


def _estilo(pt, fuente=None, color=TEXTO, antes=0, despues=0, mult=INTERLINEADO,
            primera=0, **k):
    return ParagraphStyle(
        "x", fontName=fuente or TEXTO_R, fontSize=pt, leading=pt * mult,
        textColor=color, spaceBefore=antes, spaceAfter=despues,
        firstLineIndent=primera, **k,
    )


def _p(texto, estilo):
    return Paragraph(_esc(str(texto if texto is not None else "")), estilo)


def _titulo_seccion(texto, f):
    """Rótulo de sección con su filete debajo."""
    return [
        _p(texto, _estilo(11.4 * f, TITULO_B, VERDE, antes=5 * mm, despues=1.4 * mm)),
        HRFlowable(width="100%", thickness=0.5, color=FILETE, spaceAfter=2 * mm),
    ]


def _recuadro(rotulo, texto, f):
    """Recuadro de aviso: fondo claro y filete grueso a la izquierda."""
    if not texto:
        return []
    dentro = [
        [_p(rotulo.upper(), _estilo(7.8 * f, TEXTO_B, AVISO_FILETE, mult=1.25, despues=0.8 * mm))],
        [_p(texto, _estilo(CUERPO * f, color=TEXTO))],
    ]
    tabla = Table(dentro, colWidths=[ANCHO_UTIL - 6.8 * mm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AVISO_FONDO),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, AVISO_FILETE),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.4 * mm),
        ("TOPPADDING", (0, 0), (0, 0), 2.6 * mm),
        ("BOTTOMPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2.6 * mm),
    ]))
    return [Spacer(1, 3 * mm), tabla]


def _tabla(cabeceras, filas, anchos, f, resaltadas=()):
    """Tabla con cabecera verde, fila alterna y filete fino entre filas.

    `resaltadas` son los índices de las filas de datos que van en gris y
    cursiva: los huecos de la trayectoria, que son el dato más importante.
    """
    est_cab = _estilo(8.6 * f, TEXTO_B, colors.white, mult=1.25)
    est_cel = _estilo(CUERPO * f, color=TEXTO, mult=1.34)
    est_hueco = _estilo(CUERPO * f, color=SECUNDARIO, mult=1.34)
    datos = [[_p(c, est_cab) for c in cabeceras]]
    for i, fila in enumerate(filas):
        est = est_hueco if i in resaltadas else est_cel
        datos.append([
            # Una celda puede traer ya varios parrafos apilados (el rotulo del
            # papel encima del puesto): eso se pasa tal cual.
            c if isinstance(c, (list, tuple)) or hasattr(c, "wrap") else _p(c, est)
            for c in fila
        ])

    tabla = Table(datos, colWidths=anchos, repeatRows=1)
    orden = [
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.3 * mm),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, FILETE),
    ]
    for i in range(1, len(datos)):
        if i % 2 == 0:
            orden.append(("BACKGROUND", (0, i), (-1, i), ALTERNA))
    tabla.setStyle(TableStyle(orden))
    return tabla


def _raya():
    """Línea de puntos para escribir a mano durante la entrevista."""
    return HRFlowable(width="100%", thickness=0.5, color=FILETE, dash=(1, 2),
                      spaceBefore=4.4 * mm, spaceAfter=0)


def _flujo(ficha, f):
    """Los dos folios, como lista de elementos de reportlab."""
    elementos = [
        _p("Preparación de la sesión", _estilo(16 * f, TITULO_B, VERDE, mult=1.2, despues=2 * mm)),
        _p(ficha.get("entradilla"), _estilo(CUERPO * f, color=SECUNDARIO, despues=2 * mm)),
    ]

    filas, huecos = [], set()
    for t in ficha.get("trayectoria") or []:
        if t.get("hueco"):
            huecos.add(len(filas))
        filas.append([t.get("periodo"), t.get("duracion"), t.get("que")])
    if filas:
        elementos += _titulo_seccion("1. La trayectoria en una lectura", f)
        elementos.append(_tabla(
            ("Periodo", "Duración", "Puesto y dónde"), filas,
            [32 * mm, 24 * mm, ANCHO_UTIL - 56 * mm], f, huecos,
        ))

    elementos += _recuadro("La tensión central", ficha.get("tension"), f)

    if ficha.get("hipotesis"):
        elementos += _titulo_seccion("2. Hipótesis de partida", f)
        elementos.append(_p(ficha["hipotesis"], _estilo(CUERPO * f)))

    filas = []
    est_papel = _estilo(7.8 * f, TEXTO_B, VERDE, mult=1.3)
    est_dir = _estilo(CUERPO * f, color=TEXTO, mult=1.34)
    for d in ficha.get("direcciones") or []:
        primera = []
        if d.get("papel"):
            primera.append(_p(str(d["papel"]).upper(), est_papel))
        primera.append(_p(d.get("direccion"), est_dir))
        filas.append([primera, d.get("sostiene"), d.get("hace_falta")])
    if filas:
        elementos += _titulo_seccion("3. Direcciones posibles", f)
        elementos.append(_tabla(
            ("Dirección", "Qué la sostiene", "Qué hace falta para entrar"), filas,
            [47 * mm, 50 * mm, ANCHO_UTIL - 97 * mm], f,
        ))

    elementos.append(PageBreak())

    bloques = ficha.get("preguntas") or []
    if bloques:
        elementos += _titulo_seccion("4. Lo que hay que preguntar", f)
        est_rotulo = _estilo(CUERPO * f, TEXTO_B, VERDE, mult=1.35, despues=0.6 * mm)
        est_punto = _estilo(CUERPO * f, color=SECUNDARIO, mult=1.35, leftIndent=3 * mm)
        for b in bloques:
            elementos.append(_p(b.get("bloque"), est_rotulo))
            for punto in b.get("puntos") or []:
                elementos.append(_p(f"· {punto}", est_punto))
            # Dos lineas de puntos por bloque: el documento se lleva impreso y
            # se escribe encima durante la entrevista.
            elementos += [_raya(), _raya(), Spacer(1, 2.6 * mm)]

    acciones = ficha.get("acciones") or []
    if acciones:
        elementos += _titulo_seccion("5. Acciones de arranque", f)
        # Sangria francesa: la segunda linea entra debajo del texto, no del numero.
        est_accion = _estilo(CUERPO * f, leftIndent=9 * mm, primera=-4 * mm,
                             despues=1.2 * mm)
        for i, a in enumerate(acciones, 1):
            elementos.append(Paragraph(
                f"{i}. {_esc(str(a))}", est_accion,
            ))

    elementos += _recuadro("El riesgo a evitar", ficha.get("riesgo"), f)
    return elementos


def documento_pdf(ficha):
    """El documento de preparación en PDF. Devuelve bytes. Dos páginas.

    Sin firma, sin logotipo, sin mención institucional y sin nombre de la
    persona: es material de trabajo, no un documento de la oficina. Los
    metadatos van sin autoría por lo mismo.
    """
    f = 1.0
    while True:
        salida = io.BytesIO()
        doc = BaseDocTemplate(
            salida, pagesize=A4,
            leftMargin=MARGEN_LADO, rightMargin=MARGEN_LADO,
            topMargin=MARGEN_ALTO, bottomMargin=MARGEN_PIE,
            title="Preparación de la sesión", author="", subject="", creator="",
        )
        # El marco va sin relleno propio: SimpleDocTemplate le pone 6 pt por
        # cada lado y los margenes acababan siendo 18 mm en vez de 16.
        doc.addPageTemplates([PageTemplate(id="hoja", frames=[Frame(
            MARGEN_LADO, MARGEN_PIE, ANCHO_UTIL, A4[1] - MARGEN_ALTO - MARGEN_PIE,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="hoja",
        )])])
        doc.build(_flujo(ficha, f))
        if doc.page <= 2 or f <= FACTOR_MINIMO:
            return salida.getvalue()
        f = round(f - 0.02, 2)
