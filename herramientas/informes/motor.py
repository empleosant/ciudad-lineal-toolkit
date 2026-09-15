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
# Las medidas y los colores estan tomados midiendo los documentos que se
# venian haciendo a mano: caja de texto de 177,7 mm, margenes de 16 mm y 17 mm
# arriba, cuerpo Carlito de 9,22 pt con interlineado 1,43, titulos Caladea, y
# las dos tablas con sus anchos de columna exactos.
#
# El anexo del protocolo describe la otra cadena, HTML -> wkhtmltopdf, con su
# factor de 1,307 para compensar que wkhtmltopdf maquete a 1038 px en vez de a
# 794. Aqui NO se aplica y no debe aplicarse: reportlab dibuja en puntos y los
# milimetros son milimetros. Con el factor, el documento saldria un tercio mas
# grande y en cuatro paginas. Los tamanos de esta seccion son los YA escalados
# que se midieron en los PDF buenos, no los del anexo.
#
# Caladea y Carlito no estan en el servidor: si no aparecen se usa DejaVu
# (serif para titulos, sans para texto), como hace el generador de CV con
# Trebuchet. DejaVu es mas ancha, asi que el texto corre mas; para eso esta el
# ajuste a dos paginas.

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, HRFlowable, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from xml.sax.saxutils import escape as _esc

VERDE = colors.HexColor("#2E5E4E")
TEXTO = colors.HexColor("#26251F")
PROSA = colors.HexColor("#3B3930")
SECUNDARIO = colors.HexColor("#55524A")
TENUE = colors.HexColor("#7A756A")
FILETE = colors.HexColor("#D6D2C6")
FILETE_FINO = colors.HexColor("#EAE7DD")
ALTERNA = colors.HexColor("#F7F5EF")
PUNTEADO = colors.HexColor("#B0AB9C")
AVISO_FONDO = colors.HexColor("#FBF2EC")
AVISO_FILETE = colors.HexColor("#B15A2B")

MARGEN_LADO, MARGEN_ALTO, MARGEN_PIE = 16 * mm, 17 * mm, 13 * mm
ANCHO_UTIL = A4[0] - MARGEN_LADO * 2        # 178 mm
CUERPO = 9.22
TABLA = 8.64
INTERLINEADO = 1.43
FACTOR_MINIMO = 0.82        # por debajo de esto ya no se lee cómodo en papel.
                            # El peor caso que el prompt permite necesita 0,88,
                            # así que sobra margen; medido, no estimado.

# La frase no la escribe la IA: es la misma en todos los documentos y cierra
# siempre la entradilla, para que nadie confunda una hipotesis con un informe.
CAUTELA = ("Lectura hecha únicamente a partir del currículum: todo lo que sigue "
           "es hipótesis hasta la entrevista.")

# Caladea y Carlito son las del protocolo, y son las que hay que tener: los
# tamanos y los anchos de columna de esta seccion estan medidos con ellas.
# Se instalan con `packages.txt` (fonts-crosextra-caladea y -carlito), que es
# como Streamlit Cloud instala paquetes del sistema. Si faltan se sigue
# dibujando, con DejaVu o Liberation, pero esas son mas anchas: el texto corre
# mas y el ajuste a dos paginas tiene que encoger la letra.
_CROSEXTRA = "/usr/share/fonts/truetype/crosextra"
_DEJAVU = "/usr/share/fonts/truetype/dejavu"
_LIBERATION = "/usr/share/fonts/truetype/liberation"

_FAMILIAS = {
    "titulo": (
        ("Caladea", f"{_CROSEXTRA}/Caladea-Regular.ttf", f"{_CROSEXTRA}/Caladea-Bold.ttf",
                    f"{_CROSEXTRA}/Caladea-Italic.ttf", f"{_CROSEXTRA}/Caladea-BoldItalic.ttf"),
        ("DejaVuSerif", f"{_DEJAVU}/DejaVuSerif.ttf", f"{_DEJAVU}/DejaVuSerif-Bold.ttf"),
    ),
    "texto": (
        ("Carlito", f"{_CROSEXTRA}/Carlito-Regular.ttf", f"{_CROSEXTRA}/Carlito-Bold.ttf",
                    f"{_CROSEXTRA}/Carlito-Italic.ttf", f"{_CROSEXTRA}/Carlito-BoldItalic.ttf"),
        ("DejaVuSans", f"{_DEJAVU}/DejaVuSans.ttf", f"{_DEJAVU}/DejaVuSans-Bold.ttf",
                       f"{_DEJAVU}/DejaVuSans-Oblique.ttf"),
        ("LiberationSans", f"{_LIBERATION}/LiberationSans-Regular.ttf",
                           f"{_LIBERATION}/LiberationSans-Bold.ttf",
                           f"{_LIBERATION}/LiberationSans-Italic.ttf",
                           f"{_LIBERATION}/LiberationSans-BoldItalic.ttf"),
    ),
}
_RESERVA = {"titulo": ("Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic"),
            "texto": ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique",
                      "Helvetica-BoldOblique")}


def _registra(papel):
    """(regular, negrita, cursiva) de la primera familia que esté instalada.

    La cursiva importa: los documentos ponen en cursiva los terminos en otro
    idioma (facility services, back office) y sin ella se pierden. La que falte
    se sustituye por la variante mas cercana que si este.
    """
    for familia in _FAMILIAS[papel]:
        nombre, rutas = familia[0], list(familia[1:])
        if not all(os.path.exists(r) for r in rutas[:2]):
            continue
        try:
            variantes = {}
            for sufijo, i, respaldo in (("", 0, ""), ("-B", 1, ""),
                                        ("-I", 2, ""), ("-BI", 3, "-B")):
                if i < len(rutas) and os.path.exists(rutas[i]):
                    pdfmetrics.registerFont(TTFont(f"{nombre}{sufijo}", rutas[i]))
                    variantes[sufijo] = f"{nombre}{sufijo}"
                else:
                    variantes[sufijo] = variantes.get(respaldo, nombre)
            pdfmetrics.registerFontFamily(
                nombre, normal=variantes[""], bold=variantes["-B"],
                italic=variantes["-I"], boldItalic=variantes["-BI"],
            )
            return variantes[""], variantes["-B"], variantes["-I"]
        except Exception:  # noqa: BLE001
            continue
    return _RESERVA[papel][:3]


TITULO_R, TITULO_B, _ = _registra("titulo")
TEXTO_R, TEXTO_B, TEXTO_I = _registra("texto")
CON_FUENTES_DEL_PROTOCOLO = TEXTO_R.startswith("Carlito")


# ---------------------------------------------------------------------------
# Texto con un poco de formato
# ---------------------------------------------------------------------------
# Los documentos ponen en negrita las casillas de la matriz (A3, B1, D1) y los
# datos que sostienen el argumento, y en cursiva los terminos en otro idioma.
# Se le deja a la IA marcarlo con **negrita** y *cursiva*, que es como escribe,
# y aqui se traduce a lo que entiende reportlab. Todo lo demas se escapa: si el
# CV trae un & o un <, el parrafo entero dejaria de pintarse.

_NEGRITA = re.compile(r"\*\*(.+?)\*\*", re.S)
_CURSIVA = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)


def rico(texto):
    """Texto escapado, con **negrita** y *cursiva* pasadas a marcado."""
    salida = _esc(str(texto if texto is not None else ""))
    salida = _NEGRITA.sub(r"<b>\1</b>", salida)
    return _CURSIVA.sub(r"<i>\1</i>", salida)


def _p(texto, estilo):
    return Paragraph(rico(texto), estilo)


def _con_rotulo(rotulo, texto, estilo, vineta=None):
    """«**Rótulo.** El texto que sigue», que es como se abren los bloques."""
    rotulo = (str(rotulo or "")).strip().rstrip(".")
    cuerpo = rico(texto)
    if rotulo:
        cuerpo = f"<b>{rico(rotulo)}.</b> {cuerpo}"
    # La viñeta va en el constructor: puesta despues, no se pinta.
    return Paragraph(cuerpo, estilo, bulletText=vineta)


def _estilo(pt, fuente=None, color=TEXTO, antes=0, despues=0, mult=INTERLINEADO,
            primera=0, **k):
    return ParagraphStyle(
        "x", fontName=fuente or TEXTO_R, fontSize=pt, leading=pt * mult,
        textColor=color, spaceBefore=antes, spaceAfter=despues,
        firstLineIndent=primera, **k,
    )


class _Numero(Flowable):
    """El número de sección, en blanco dentro de un círculo verde."""

    def __init__(self, n, diametro, pt):
        super().__init__()
        self.n, self.d, self.pt = str(n), diametro, pt

    def wrap(self, *_):
        return self.d, self.d

    def draw(self):
        c = self.canv
        c.setFillColor(VERDE)
        c.circle(self.d / 2, self.d / 2, self.d / 2, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(TEXTO_B, self.pt)
        c.drawCentredString(self.d / 2, self.d / 2 - self.pt * 0.35, self.n)


def _seccion(n, texto, f, antes=6 * mm):
    """Número en su círculo, título en verde y filete debajo."""
    diametro = 4.2 * mm * f
    hueco = diametro + 2.4 * mm * f
    fila = Table(
        [[_Numero(n, diametro, 6.4 * f),
          _p(texto, _estilo(12.1 * f, TITULO_B, VERDE, mult=1.15))]],
        colWidths=[hueco, ANCHO_UTIL - hueco],
    )
    fila.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [
        Spacer(1, antes * f), fila,
        HRFlowable(width="100%", thickness=0.5, color=FILETE,
                   spaceBefore=1.6 * mm * f, spaceAfter=2.2 * mm * f),
    ]


def _recuadro(rotulo, texto, f):
    """Recuadro de aviso: fondo claro, filete grueso a la izquierda.

    El rotulo no es una etiqueta aparte sino la primera frase en negrita, que
    cambia con el caso: «El desajuste que explica el bloqueo», «Las dos cosas
    que ordenan esta sesión», «El riesgo a evitar».
    """
    if not texto:
        return []
    dentro = [[_con_rotulo(rotulo, texto, _estilo(CUERPO * f, color=TEXTO))]]
    tabla = Table(dentro, colWidths=[ANCHO_UTIL])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AVISO_FONDO),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, AVISO_FILETE),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.6 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.6 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.8 * mm * f),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.8 * mm * f),
    ]))
    return [Spacer(1, 3.4 * mm * f), tabla]


def _ancho_periodos(filas, f):
    """La columna de periodos, ajustada a la fuente que haya de verdad.

    Con Carlito caben los 21 mm del documento original; con la de reserva, mas
    ancha, «02/2020 – 12/2022» se partiria en dos lineas y la tabla perderia la
    lectura de un vistazo que es su razon de ser.
    """
    pt = TABLA * f
    anchos = [pdfmetrics.stringWidth(str(t.get("periodo") or ""), TEXTO_B, pt)
              for t in filas]
    return min(max(21 * mm, max(anchos or [0]) + 2 * mm), 34 * mm)


def _tabla_trayectoria(filas, f):
    """Sin cabecera y sin fondos: periodo, qué pasó y cuánto duró.

    La columna de la derecha lleva la duracion, y en las lineas de formacion,
    la edad aproximada: de ahi sale la edad de la persona.
    """
    est_periodo = _estilo(TABLA * f, TEXTO_B, SECUNDARIO, mult=1.34)
    est_que = _estilo(TABLA * f, color=TEXTO, mult=1.34)
    est_dur = _estilo(TABLA * f, color=TENUE, mult=1.34, alignment=2)
    datos = [[_p(t.get("periodo"), est_periodo), _p(t.get("que"), est_que),
              _p(t.get("duracion"), est_dur)] for t in filas]
    periodo = _ancho_periodos(filas, f)
    tabla = Table(datos, colWidths=[periodo, ANCHO_UTIL - periodo - 31 * mm, 31 * mm])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-2, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm * f),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm * f),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, FILETE_FINO),
    ]))
    return tabla


def _tabla_direcciones(filas, f):
    """Cabecera verde y tres columnas de 47, 50 y 80 mm."""
    est_cab = _estilo(8.07 * f, TEXTO_B, colors.white, mult=1.25)
    est_papel = _estilo(TABLA * f, TEXTO_B, VERDE, mult=1.34)
    est_cel = _estilo(TABLA * f, color=TEXTO, mult=1.34)
    datos = [[_p(c, est_cab) for c in
              ("Dirección", "Qué acredita ya", "Qué falta y por dónde entrar")]]
    for d in filas:
        papel = " — ".join(x for x in (d.get("papel"), d.get("familia")) if x)
        primera = [_p(papel, est_papel)]
        if d.get("variantes"):
            primera.append(_p(d["variantes"], est_cel))
        datos.append([primera, d.get("acredita"), d.get("falta")])

    cuerpo = _estilo(TABLA * f, color=TEXTO, mult=1.34)
    datos[1:] = [[c if isinstance(c, list) else _p(c, cuerpo) for c in fila]
                 for fila in datos[1:]]
    tabla = Table(datos, colWidths=[47 * mm, 50 * mm, ANCHO_UTIL - 97 * mm],
                  repeatRows=1)
    orden = [
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6 * mm * f),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 * mm * f),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, FILETE),
    ]
    for i in range(1, len(datos)):
        if i % 2 == 0:
            orden.append(("BACKGROUND", (0, i), (-1, i), ALTERNA))
    tabla.setStyle(TableStyle(orden))
    return tabla


def _raya(antes):
    """Línea de puntos para escribir a mano durante la entrevista."""
    return HRFlowable(width="100%", thickness=0.58, color=PUNTEADO,
                      dash=(0.58, 0.58), spaceBefore=antes, spaceAfter=0)


def _flujo(ficha, f):
    """Los dos folios, como lista de elementos de reportlab."""
    entradilla = (ficha.get("entradilla") or "").strip()
    entradilla = f"{entradilla} {CAUTELA}" if entradilla else CAUTELA
    elementos = [
        _p("Preparación de sesión",
           _estilo(17.86 * f, TITULO_B, TEXTO, mult=1.18, despues=2.2 * mm * f)),
        _p(entradilla, _estilo(9.8 * f, color=SECUNDARIO, mult=1.42)),
        HRFlowable(width="100%", thickness=1.4, color=VERDE,
                   spaceBefore=3.4 * mm * f, spaceAfter=0),
    ]

    trayectoria = ficha.get("trayectoria") or []
    if trayectoria:
        elementos += _seccion(1, "La trayectoria en una lectura", f, antes=4.4 * mm)
        elementos.append(_tabla_trayectoria(trayectoria, f))

    tension = ficha.get("tension") or {}
    elementos += _recuadro(tension.get("rotulo"), tension.get("texto"), f)

    if ficha.get("hipotesis"):
        elementos += _seccion(2, "Hipótesis de partida", f)
        elementos.append(_p(ficha["hipotesis"], _estilo(CUERPO * f, color=PROSA)))

    direcciones = ficha.get("direcciones") or []
    if direcciones:
        elementos += _seccion(
            3, "Direcciones posibles: una principal y una secundaria", f)
        if ficha.get("direcciones_entradilla"):
            elementos.append(_p(
                ficha["direcciones_entradilla"],
                _estilo(CUERPO * f, color=PROSA, despues=2.4 * mm * f),
            ))
        elementos.append(_tabla_direcciones(direcciones, f))

    elementos.append(PageBreak())

    preguntas = ficha.get("preguntas") or []
    if preguntas:
        elementos += _seccion(4, "Lo que hay que preguntar", f, antes=0)
        est = _estilo(CUERPO * f, color=PROSA)
        for b in preguntas:
            elementos.append(_con_rotulo(b.get("rotulo"), b.get("texto"), est))
            # Dos lineas de puntos por bloque: el documento se lleva impreso y
            # se escribe encima durante la entrevista.
            elementos += [_raya(3.2 * mm * f), _raya(4.5 * mm * f),
                          Spacer(1, 1.2 * mm * f)]

    acciones = ficha.get("acciones") or []
    if acciones:
        elementos += _seccion(5, "Acciones de arranque", f)
        est = _estilo(CUERPO * f, color=PROSA, leftIndent=5.4 * mm,
                      despues=1.6 * mm * f, bulletIndent=1.4 * mm,
                      bulletFontName=TEXTO_R, bulletFontSize=CUERPO * f)
        for a in acciones:
            elementos.append(
                _con_rotulo(a.get("rotulo"), a.get("texto"), est, vineta="•"))

    riesgo = ficha.get("riesgo") or {}
    elementos += _recuadro(riesgo.get("rotulo") or "El riesgo a evitar",
                           riesgo.get("texto"), f)
    return elementos


def documento_pdf(ficha, con_detalle=False):
    """El documento de preparación en PDF. Devuelve bytes. Dos páginas.

    Sin firma, sin logotipo, sin mención institucional y sin nombre de la
    persona: es material de trabajo, no un documento de la oficina. Los
    metadatos van sin autoría por lo mismo.

    Con `con_detalle`, devuelve tambien (paginas, factor): lo usa la bateria
    de pruebas para medir el ajuste sin volver a abrir el PDF.
    """
    f = 1.0
    while True:
        salida = io.BytesIO()
        doc = BaseDocTemplate(
            salida, pagesize=A4,
            leftMargin=MARGEN_LADO, rightMargin=MARGEN_LADO,
            topMargin=MARGEN_ALTO, bottomMargin=MARGEN_PIE,
            title="Preparación de sesión", author="", subject="", creator="",
        )
        # El marco va sin relleno propio: SimpleDocTemplate le pone 6 pt por
        # cada lado y los margenes acababan siendo 18 mm en vez de 16.
        doc.addPageTemplates([PageTemplate(id="hoja", frames=[Frame(
            MARGEN_LADO, MARGEN_PIE, ANCHO_UTIL, A4[1] - MARGEN_ALTO - MARGEN_PIE,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="hoja",
        )])])
        doc.build(_flujo(ficha, f))
        if doc.page <= 2 or f <= FACTOR_MINIMO:
            if con_detalle:
                return salida.getvalue(), {"paginas": doc.page, "factor": f}
            return salida.getvalue()
        f = round(f - 0.02, 2)
