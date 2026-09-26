"""
Motor del codificador de extranjería. Python puro: no importa Streamlit.

Traduce las fórmulas de la hoja IDENTIFICAR del Excel de códigos de
autorizaciones de septiembre de 2026 (el documento de la oficina; sus datos
están en `datos/`, extraídos con `scripts/extraer_extranjeria.py`):

    codifica(documento, opcion, ...)      qué código y qué fecha fin se graban
    opciones(documento)                   lo que puede poner ese documento
    consulta(codigo)                      la ficha de un código de la tabla
    plazos_demanda(hoy, fin, solicitud)   cuándo toca renovar la demanda
    edate(fecha, meses)                   la suma de meses de Excel

Las fechas entran como `datetime.date` o `None`. `hoy` es un parámetro y no
`date.today()`: el Excel usa HOY() y eso hace imposible probar la caducidad;
aquí la batería fija la fecha. Lo prueba `pruebas/extranjeria.py`.

Cada resultado lleva los avisos en una lista y no en un solo texto, como en
el Excel, para que la pantalla los pinte cada uno en su color; el orden es
el de la fórmula original.
"""

import calendar
import csv
import json
import math
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")

# Fechas que la normativa fija y las fórmulas comparan.
RD_1155 = date(2025, 5, 20)      # entra en vigor el RD 1155/2024
RD_316 = date(2026, 4, 16)       # regularización extraordinaria (RD 316/2026)
SIN_CADUCIDAD = date(2200, 1, 1)
NO_SE_INSCRIBE = "NO SE INSCRIBE"
CODIGO_ANTERIOR = "El código de su autorización anterior"
DOC_RESOLUCION = "Resolución de concesión (todavía sin TIE)"

# Umbrales de duración de la tarjeta, en años (la tarjeta se expide después
# de la concesión, así que una de 1 año puede durar 1,2).
UN_ANO = 1.3
DOS_ANOS = 2.5
CUATRO_ANOS = 4.5


def _lee(nombre):
    with open(os.path.join(DATOS, nombre), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


REGLAS = _lee("reglas.csv")
DOCUMENTOS = _lee("documentos.csv")
CODIGOS = _lee("codigos.csv")
DURACIONES = {r["codigo"]: r for r in _lee("duraciones.csv")}
TRAMITE = _lee("tramite.csv")
PLAZOS = _lee("plazos.csv")
BAJAS = _lee("bajas.csv")
DURACIONES_TARJETA = _lee("duraciones_tarjeta.csv")
TEXTOS_TIE = _lee("textos_tie.csv")
ENLACES = _lee("enlaces.csv")
NOVEDADES = _lee("novedades.csv")
with open(os.path.join(DATOS, "notas.json"), encoding="utf-8") as _f:
    NOTAS = json.load(_f)

_LISTA_DE = {d["documento"]: d["lista"] for d in DOCUMENTOS}
_DONDE = {d["documento"]: d["donde_mirar"] for d in DOCUMENTOS}
_REGLA = {(r["lista"], r["opcion"]): r for r in REGLAS}
_FICHA = {c["codigo"]: c for c in CODIGOS}
NOMBRES_DOCUMENTOS = [d["documento"] for d in DOCUMENTOS]
NOMBRES_CODIGOS = [c["codigo"] for c in CODIGOS]


# ---------------------------------------------------------------------------
# Fechas, como las calcula Excel
# ---------------------------------------------------------------------------

def _fecha(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        for formato in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(v.strip(), formato).date()
            except ValueError:
                pass
    raise ValueError(f"fecha no reconocida: {v!r}")


def edate(fecha, meses):
    """EDATE de Excel: suma meses y, si el día no existe, el último del mes."""
    mes0 = fecha.year * 12 + fecha.month - 1 + meses
    ano, mes = divmod(mes0, 12)
    mes += 1
    dia = min(fecha.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def anos_entre(desde, hasta):
    """DATEDIF(desde, hasta, "y"): años completos."""
    n = hasta.year - desde.year
    if (hasta.month, hasta.day) < (desde.month, desde.day):
        n -= 1
    return n


def meses_entre(desde, hasta):
    """DATEDIF(desde, hasta, "m"): meses completos."""
    n = (hasta.year - desde.year) * 12 + hasta.month - desde.month
    if hasta.day < desde.day:
        n -= 1
    return n


def _redondea(x):
    """ROUND(x, 1) de Excel: el medio se aleja de cero."""
    return math.floor(x * 10 + 0.5) / 10


def _anos_texto(duracion):
    r = _redondea(duracion)
    if r == 1:
        return "1 año"
    return f"{r:g}".replace(".", ",") + " años"


def fmt(fecha):
    """d/m/aaaa, como lo concatena el Excel en los avisos."""
    return f"{fecha.day}/{fecha.month}/{fecha.year}"


def fecha_texto(valor):
    """Lo que se enseña como fecha fin: dd/mm/aaaa si es fecha; si no, el texto."""
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return valor or ""


# ---------------------------------------------------------------------------
# El árbol de decisión
# ---------------------------------------------------------------------------

@dataclass
class Resultado:
    documento: str = ""
    opcion: str = ""
    valido: bool = False
    mensaje: str = ""            # si no es válido: qué falta
    codigo: str = ""             # lo que sale en grande (puede ser un «Probable…»)
    puede_trabajar: str = ""
    restriccion: str = ""
    colectivo: str = ""
    se_inscribe_con: str = ""
    ojo: str = ""
    fecha_fin: object = ""       # date, o un texto cuando faltan fechas
    avisos: list = field(default_factory=list)   # lo que hay que mirar (rojo/ámbar)
    notas: list = field(default_factory=list)    # el «a tener en cuenta» de la regla
    datos: list = field(default_factory=list)    # edad, meses, duración de la tarjeta
    regla: dict = field(default_factory=dict)
    ficha: dict = field(default_factory=dict)

    @property
    def fecha_fin_texto(self):
        return fecha_texto(self.fecha_fin)

    @property
    def se_inscribe(self):
        return self.valido and self.codigo != NO_SE_INSCRIBE


def opciones(documento):
    lista = _LISTA_DE.get(documento)
    return [r["opcion"] for r in REGLAS if r["lista"] == lista]


def donde_mirar(documento):
    return _DONDE.get(documento, "")


def consulta(codigo):
    return _FICHA.get(codigo)


def codifica(documento, opcion, emision=None, valido_hasta=None, nacimiento=None,
             solicitud_renovacion=None, sin_alta_ss=False, hoy=None):
    """La hoja IDENTIFICAR: de lo que trae la persona al código y la fecha."""
    emision, valido_hasta = _fecha(emision), _fecha(valido_hasta)
    nacimiento, solicitud = _fecha(nacimiento), _fecha(solicitud_renovacion)
    hoy = _fecha(hoy) or date.today()
    r = Resultado(documento=documento or "", opcion=opcion or "")

    if not documento:
        r.mensaje = "Empieza por el documento"
        return r
    regla = _REGLA.get((_LISTA_DE.get(documento), opcion))
    if not opcion or regla is None:
        r.mensaje = "Elige qué pone el documento"
        return r
    r.valido, r.regla = True, regla
    tipo, cod1, cod2, vig, marca = (regla["tipo"], regla["cod1"], regla["cod2"],
                                    regla["vigencia"], regla["marca"])

    # Lo que se deduce de las fechas (L15-L18).
    edad = anos_entre(nacimiento, hoy) if nacimiento else None
    edad_emision = anos_entre(nacimiento, emision) if nacimiento and emision else None
    meses = meses_entre(emision, hoy) if emision else None
    duracion = ((valido_hasta - emision).days / 365.25
                if emision and valido_hasta else None)
    if edad is not None:
        r.datos.append(f"Edad: {edad} años")
    if meses is not None:
        r.datos.append(f"Desde la emisión: {meses} meses")
    if duracion is not None:
        r.datos.append(f"Duración de la tarjeta: {_anos_texto(duracion)}")

    # El código (L19).
    if documento == DOC_RESOLUCION and sin_alta_ss:
        codigo = "IC"
    elif tipo == "GEN":
        if duracion is None:
            codigo = "Mira la resolución (faltan fechas)"
        elif duracion <= UN_ANO:
            codigo = "Probable R5 o T0/T1 · mira la resolución"
        elif duracion <= DOS_ANOS:
            codigo = "Probable M3, R5 ex-MENA o R7 · mira la resolución"
        elif duracion <= CUATRO_ANOS:
            codigo = "Probable T2 · mira la resolución"
        else:
            codigo = "Probable R0, R5 o R7 · mira la resolución"
    elif tipo == "FIX":
        codigo = cod1
    elif tipo == "DUR":
        if duracion is None:
            codigo = f"¿{cod1} o {cod2}? (faltan fechas)"
        else:
            codigo = cod1 if duracion <= UN_ANO else cod2
    elif tipo == "EDAD18":
        if edad is None:
            codigo = f"¿{cod1} o {cod2}? (falta fecha de nacimiento)"
        else:
            codigo = cod1 if edad < 18 else cod2
    elif tipo == "REAG":
        if edad_emision is not None and edad is not None and edad_emision < 16 <= edad:
            codigo = cod2
        else:
            codigo = cod1
    elif tipo == "PIMES":
        if meses is None:
            codigo = "¿C1 o A1? (falta fecha de presentación)"
        elif meses < 1:
            codigo = NO_SE_INSCRIBE
        elif meses < 6:
            codigo = "C1"
        else:
            codigo = "A1"
    elif tipo == "NO":
        codigo = NO_SE_INSCRIBE
    elif tipo == "PREV":
        codigo = CODIGO_ANTERIOR
    else:                                   # MSG
        codigo = cod1
    r.codigo = codigo

    # La ficha del código en la tabla (F7, F9, C17, C18).
    ficha = _FICHA.get(codigo) if codigo != NO_SE_INSCRIBE else None
    if ficha:
        r.ficha = ficha
        r.puede_trabajar = ficha["puede_trabajar"]
        r.restriccion = ficha["restriccion"]
        r.colectivo = ficha["colectivo"]
        r.se_inscribe_con = ficha["se_inscribe_con"]
        r.ojo = ficha["ojo"]
    if tipo == "GEN":
        r.puede_trabajar = "SÍ (según la tarjeta)"

    # La fecha fin a grabar (L20).
    if codigo == "IC":
        fin = edate(emision, 6) if emision else "Fecha de resolución + 6 meses"
    elif codigo == NO_SE_INSCRIBE:
        fin = "—"
    elif vig == "DOC":
        fin = valido_hasta or "La del documento (rellena «Válido hasta»)"
    elif vig == "2200":
        fin = SIN_CADUCIDAD
    elif vig == "E2M":
        fin = edate(emision, 2) if emision else "Fecha de presentación + 2 meses"
    elif vig == "E3M":
        fin = edate(emision, 3) if emision else "Fecha de emisión/admisión + 3 meses"
    elif vig == "E5Y":
        fin = edate(emision, 60) if emision else "Fecha de resolución + 5 años"
    elif vig == "H180":
        fin = hoy + timedelta(days=180)
    elif vig == "NAC":
        fin = (edate(nacimiento, 216) + timedelta(days=90) if nacimiento
               else "Fecha de nacimiento + 18 años + 90 días")
    elif vig == "V1M":
        fin = edate(valido_hasta, 1) if valido_hasta else "Validez de la tarjeta + 1 mes"
    elif vig == "PREV":
        fin = "La de su autorización anterior (y anota la fecha de solicitud de renovación)"
    else:
        fin = "—"
    r.fecha_fin = fin

    # Los avisos (L23), en el orden de la fórmula.
    avisos = r.avisos
    fin_es_fecha = isinstance(fin, date)
    if fin_es_fecha and fin < hoy and fin < SIN_CADUCIDAD and vig not in ("E2M", "E3M"):
        texto = f"⚠ CADUCADO el {fmt(fin)}. "
        if codigo.startswith("P1"):
            texto += ("La larga duración no se extingue: con cita previa, anota la cita como "
                      "fecha de solicitud de renovación (cita + 100 días); sin cita, hoy + 1 mes.")
        elif solicitud is None:
            texto += ("Pide el resguardo de renovación (60 días antes o 90 después de caducar) "
                      "o el certificado de silencio positivo: sin eso no se inscribe.")
        elif fin - timedelta(days=61) <= solicitud <= fin + timedelta(days=90):
            texto += (f"Renovación pedida en plazo: se inscribe con este código; anota el "
                      f"{fmt(solicitud)} como fecha de solicitud de renovación.")
            if hoy > edate(solicitud, 3):
                texto += (" Han pasado más de 3 meses: certificado de silencio positivo "
                          "o consulta del expediente.")
        else:
            texto += "Renovación pedida FUERA de plazo: no sirve para inscribir."
        avisos.append(texto)
    if vig in ("E2M", "E3M") and fin_es_fecha and fin < hoy:
        avisos.append("Ese plazo ya ha pasado: si sigue en trámite se prorroga por periodos "
                      "iguales; comprueba el expediente y graba la fecha siguiente.")
    if marca == "PLAZO":
        if valido_hasta and solicitud:
            if (valido_hasta - timedelta(days=61) <= solicitud
                    <= valido_hasta + timedelta(days=90)):
                texto = (f"Solicitud en plazo. Graba fecha fin de vigencia {fmt(valido_hasta)} "
                         f"y fecha de solicitud de renovación {fmt(solicitud)}.")
                if hoy > edate(solicitud, 3):
                    texto += (" Más de 3 meses desde la solicitud: certificado de silencio "
                              "positivo o consulta del expediente.")
                avisos.append(texto)
            else:
                avisos.append("Solicitud FUERA de plazo (60 días antes / 90 después de "
                              "caducar): no sirve para inscribir.")
        else:
            avisos.append("Rellena «Válido hasta» y «Solicitud de renovación» para "
                          "comprobar el plazo.")
    if edad is not None:
        if edad < 16:
            avisos.append("⚠ Menor de 16 años: no se puede inscribir.")
        elif edad < 18 and not codigo.startswith("M"):
            avisos.append(f"Tiene {edad} años: se puede inscribir. Si está tutelado por "
                          "la CM, el código sería M1 o M2.")
    if marca == "RE" and emision and emision >= RD_316:
        avisos.append("Concedida después del 16/04/2026: si viene de la regularización "
                      "extraordinaria (RD 316/2026) es RE, no R5. Mira la resolución.")
    if codigo == "R6" and emision and emision >= RD_1155:
        avisos.append("R6 solo existe para autorizaciones anteriores al 20/05/2025: "
                      "revisa el documento.")
    if marca == "OLD17" and emision and emision < RD_1155 and codigo in ("R1", "RF"):
        avisos.append("Concedida antes del 20/05/2025: añade el Col. 17"
                      + (" hasta que acredite la formación" if codigo == "RF" else "") + ".")
    if sin_alta_ss and documento != DOC_RESOLUCION:
        avisos.append("La pregunta del alta en SS solo cuenta para resoluciones.")

    # La duración rara (L24).
    rango = DURACIONES.get(codigo)
    if duracion is not None and tipo != "GEN" and rango:
        if duracion < float(rango["minimo"]) or duracion > float(rango["maximo"]):
            avisos.append(f"⚠ La tarjeta dura {_anos_texto(duracion)}: no es habitual en "
                          f"{codigo} (lo normal: {rango['normal']}). Revisa el texto o "
                          "pide la resolución.")

    # Las notas (L25).
    if codigo == "IC":
        r.notas.append("Se graba IC mientras no conste el alta en SS; con el alta o con "
                       "la TIE, cambia al código de su autorización.")
    if regla["aviso"]:
        r.notas.append(regla["aviso"])
    if tipo == "PIMES" and meses is not None:
        r.notas.append(f"Han pasado {meses} meses desde la fecha de registro o presentación.")
    return r


# ---------------------------------------------------------------------------
# La calculadora de la hoja FECHAS
# ---------------------------------------------------------------------------

@dataclass
class Plazos:
    proxima: date
    tipo: str                 # «Normal» o «ESPECIAL: …»
    limite: date              # lo que permite la autorización
    en_plazo: object = None   # True/False, o None si no hay solicitud
    mas_de_tres_meses: object = None


def plazos_demanda(hoy, fin_vigencia, solicitud_renovacion=None):
    """Cuándo toca la próxima renovación de la demanda.

    La menor de (hoy + 91 días) y el límite de la autorización, que es la
    mayor de (fin de vigencia + 7 días) y (solicitud de renovación + 100
    días). Si la de los 91 días llega a ese límite, la renovación es
    especial: presencial y con la autorización en vigor.
    """
    hoy, fin = _fecha(hoy), _fecha(fin_vigencia)
    solicitud = _fecha(solicitud_renovacion)
    limite = fin + timedelta(days=7)
    if solicitud:
        limite = max(limite, solicitud + timedelta(days=100))
    normal = hoy + timedelta(days=91)
    p = Plazos(proxima=min(normal, limite), limite=limite,
               tipo=("ESPECIAL: presencial, hay que traer autorización en vigor"
                     if normal >= limite else "Normal"))
    if solicitud:
        p.en_plazo = fin - timedelta(days=61) <= solicitud <= fin + timedelta(days=90)
        p.mas_de_tres_meses = hoy > edate(solicitud, 3)
    return p
