"""
La Guía de empleo de Madrid dentro de la app. Python puro, sin Streamlit.

Las fichas son una copia de la guía (`comun/datos/guia/`, la saca
`scripts/traer_guia.py`); lo único que se escribe aquí a mano es qué
capítulos le tocan a cada ocupación del catálogo SISPE
(`comun/datos/ocupaciones_sectores.csv`).

    destinos(codigo)          (capítulo, apartado) de una ocupación, el principal primero
    secciones(codigos)        lo que hay que enseñar para una o varias ocupaciones, con los
                              centros especiales de empleo aparte
    seccion(capitulo)         un capítulo entero (o algunos apartados) con la misma forma
    busca(texto)              las fichas de los sectores que nombran eso, las mejores primero
    lista(fichas)             las empresas marcadas a mano, con la forma de una sección
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

from comun.texto import esc, normaliza

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


def secciones(codigos, generales=True, cee=True):
    """Lo que hay que enseñar para una o varias ocupaciones.

    Cada sección es un capítulo con los apartados que tocan, ordenadas por
    cuántas ocupaciones apuntan a él y, a igualdad, por el orden en que
    salen. Si ninguna ocupación tiene sector y `generales` es verdadero,
    salen los portales generalistas y las grandes ETT, marcadas así.

    Con `cee`, los centros especiales de empleo salen de su sector y van a
    una sección aparte (ver `aparta_cee`).
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
    return aparta_cee(salida) if cee else salida


# ---------------------------------------------------------------------------
# Los centros especiales de empleo, aparte
# ---------------------------------------------------------------------------
# Lo pidió Álvaro el 03/10/2026: si alguien busca limpieza, los centros que
# contratan sobre todo a personas con discapacidad tienen que salir en su
# propio apartado y no mezclados con el resto de empresas. Quien no tiene el
# certificado pierde el tiempo con ellos, y quien lo tiene los busca a propósito.

CEE = "cee"     # la clave de la sección aparte; no es un capítulo de la guía

# La nota «Qué es un centro especial de empleo» del capítulo 9 de la guía.
NOTA_CEE = ("Al menos el 70 % de la plantilla son personas con discapacidad. Para entrar hay "
            "que tener reconocido un grado de discapacidad igual o superior al 33 % y estar "
            "inscrita o inscrito como demandante de empleo.")

# Qué centros del capítulo 9 («Centros especiales de empleo») trabajan en cada
# sector, por lo que dice su ficha que hacen. Hecho a mano: un sector que no
# esté aquí solo enseña los centros que ya tiene en su propio capítulo.
CEE_ACTIVIDAD = {
    "13-limpieza": r"limpieza|conserjer",
    "36-jardineria": r"jardiner",
    "42-servicios-tecnicos": r"lavander|arreglo de ropa",
    "12-logistica": r"log[ií]stica|almac[eé]n|manipulad|envasad",
    "35-mensajeria": r"mensajer|reparto",
    "18-administracion": r"contact center|telemarketing|administrativ|gesti[oó]n documental",
    "45-publicidad": r"artes gr[aá]ficas|impresi[oó]n",
    "11-hosteleria": r"restauraci[oó]n|catering",
    "40-eventos": r"catering|eventos",
    "37-alimentacion": r"alimentaci[oó]n",
    "43-movilidad": r"aparcamiento",
    "22-tecnologia": r"inform[aá]tic",
    "30-industria": r"fabricaci[oó]n|manipulad|industrial",
}

_TIENE_CEE = re.compile(r"(?i:centro especial de empleo)|\bCEE\b")


def es_cee(f):
    """La ficha es un centro especial de empleo (así la clasifica la guía)."""
    return f.get("tipo") == "centro especial de empleo"


def tiene_cee(f):
    """Una empresa corriente que dice tener además su centro especial («Serlingo»)."""
    return not es_cee(f) and bool(_TIENE_CEE.search(f"{f['nombre']} {f.get('que', '')} {f.get('como', '')}"))


def aparta_cee(secciones_):
    """Saca los centros especiales de empleo de cada sector a una sección propia.

    - Los que la guía clasifica como centro especial salen de su sector y solo
      están en la sección aparte.
    - Las empresas corrientes que además tienen su centro especial se quedan
      en su sector y salen también en la sección aparte: contratan a todo el
      mundo, y quien tiene el certificado tiene que saber que ahí hay sitio.
    - Se añaden los centros del capítulo 9 cuya actividad es la del sector.

    La sección aparte va después de los sectores y antes de los portales.
    """
    vistos, del_sector, salida = set(), [], []
    for s in secciones_:
        if s.get("general") or s["capitulo"] == "24-portales":
            salida.append(s)
            continue
        apartados = []
        for nombre, fs in s["apartados"]:
            for f in fs:
                if (es_cee(f) or tiene_cee(f)) and normaliza(f["nombre"]) not in vistos:
                    vistos.add(normaliza(f["nombre"]))
                    del_sector.append(f)
            resto = [f for f in fs if not es_cee(f)]
            if resto:
                apartados.append((nombre, resto))
        if apartados:
            salida.append({**s, "apartados": apartados, "n": sum(len(x) for _, x in apartados),
                           "entero": s["entero"] and len(apartados) == len(s["apartados"])})

    patrones = [CEE_ACTIVIDAD[s["capitulo"]] for s in secciones_ if s["capitulo"] in CEE_ACTIVIDAD]
    otros = []
    if patrones:
        actividad = re.compile("|".join(patrones), re.I)
        for f in fichas("09-insercion", "Centros especiales de empleo"):
            if actividad.search(f"{f.get('que', '')} {f.get('como', '')}") \
                    and normaliza(f["nombre"]) not in vistos:
                vistos.add(normaliza(f["nombre"]))
                otros.append(f)
    if not (del_sector or otros):
        return salida

    apartados = []
    if del_sector:
        apartados.append(("En este sector", del_sector))
    if otros:
        apartados.append(("Otros que también trabajan en él", otros))
    aparte = {
        "capitulo": CEE, "titulo": "Centros especiales de empleo (personas con discapacidad)",
        "corto": "Con discapacidad (CEE)", "entero": False, "apartados": apartados,
        "n": len(del_sector) + len(otros), "general": False, "cee": True, "nota": NOTA_CEE,
    }
    donde = next((i for i, s in enumerate(salida) if s["capitulo"] == "24-portales" or s.get("general")),
                 len(salida))
    return salida[:donde] + [aparte] + salida[donde:]


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
# Para empezar a trabajar: sin experiencia ni titulación
# ---------------------------------------------------------------------------
# Lo pidió Álvaro el 03/10/2026: es lo que pregunta a menudo quien acaba de
# llegar a España y quiere empezar a trabajar cuanto antes. La guía no marca
# qué empresas contratan sin experiencia, así que esto es una selección HECHA
# A MANO de apartados donde lo corriente es entrar sin experiencia previa ni
# título: se queda fuera lo que pide habilitación (seguridad, socorrismo),
# certificado de profesionalidad (residencias, ayuda a domicilio) o carné
# profesional. En el orden en que se enseña. Si la guía renombra un apartado,
# `pruebas/guia.py` lo canta.
# La misma selección es el PDF «Empezar a trabajar en Madrid» de la guía
# (guia-empleo-madrid, datos/selecciones.toml): si cambia aquí, cambiarla allí.
PARA_EMPEZAR = [
    ("01-oficina-de-empleo", ["Trámites por internet y por teléfono", "Oficinas de empleo de Madrid capital"]),
    ("24-portales", ["Generalistas"]),
    ("08-ett", ["Grandes redes", "Generalistas", "Especializadas por sector"]),
    ("07-agencias-de-colocacion", ["Generalistas", "Entidades sociales", "Empleo de hogar y cuidados"]),
    ("09-insercion", ["Empresas de inserción", "Entidades sociales con programas de empleo"]),
    ("33-colectivos", ["Si vienes de otro país"]),
    ("06-formacion", ["Centros de formación de la Comunidad de Madrid", "Buscadores de cursos gratuitos", "Carnés y acreditaciones que abren puertas"]),
    ("13-limpieza", ["Grandes empresas de servicios", "Empresas de limpieza", "Limpieza viaria y residuos", "Conserjería y servicios auxiliares"]),
    ("11-hosteleria", ["Cadenas de restauración", "Hoteles", "Bolsas y portales del sector"]),
    ("15-monitores", ["Comedores escolares y restauración colectiva"]),
    ("46-hogar", ["Agencias de empleo de hogar", "Bolsas gratuitas de entidades y parroquias", "Asesoría y defensa de tus derechos"]),
    ("40-eventos", ["Azafatas, auxiliares y personal de eventos", "Catering y restauración de eventos"]),
    ("17-ocio-y-cultura", ["Parques de ocio", "Cines y teatros"]),
    ("10-comercio", ["Supermercados e hipermercados", "Grandes almacenes y moda", "Hogar, bricolaje y electrónica", "Deporte, ocio y cultura", "Perfumería y otros"]),
    ("37-alimentacion", ["Panadería, pastelería y obradores", "Mercamadrid, mayoristas y mercados", "Envasado y plataformas de alimentación", "Formación y carnés"]),
    ("12-logistica", ["Operadores logísticos", "Paquetería y reparto", "Comercio electrónico y distribución"]),
    ("35-mensajeria", ["Mensajería y paquetería", "Reparto a domicilio y plataformas"]),
    ("28-aeropuerto", ["Handling y servicios en pista", "Tiendas, restauración y servicios al pasajero", "Acreditaciones y acceso"]),
    ("43-movilidad", ["Aparcamientos y grúas", "Estaciones de servicio y lavado"]),
    ("21-construccion", ["Constructoras", "Formación y tarjeta profesional"]),
    ("36-jardineria", ["Empresas de jardinería y parques", "Residuos, reciclaje y medio ambiente", "Viveros y centros de jardinería"]),
    ("42-servicios-tecnicos", ["Lavanderías industriales y tintorerías"]),
    ("18-administracion", ["Contact center", "Atención al cliente y televenta"]),
]
# Fichas de esos apartados que no entran: perfiles cualificados o de otro oficio.
EMPEZAR_FUERA = {
    "Hays",
    "Michael Page",
    "DyaDigital",
    "Exclusivas Imanara",
    "Agencia Penélope",
    "Infotree Global",
    "UPTA (Unión de Profesionales y Trabajadores Autónomos)",
}
NOTA_EMPEZAR = ("Sectores donde lo corriente es entrar sin experiencia previa ni título. Es una "
                "selección de la oficina, no una garantía: cada oferta dice lo que pide. Para "
                "trabajar hace falta, en todos, autorización de trabajo en vigor.")


# Dos capítulos de los que solo entra un apartado y cuyo título no cabe en una píldora.
_CORTOS_EMPEZAR = {"09-insercion": "Inserción y programas", "33-colectivos": "Si vienes de otro país",
                   "18-administracion": "Contact center", "15-monitores": "Comedores",
                   "17-ocio-y-cultura": "Ocio", "43-movilidad": "Gasolineras y aparcamientos",
                   "01-oficina-de-empleo": "Oficina de empleo", "06-formacion": "Formación gratuita"}


def para_empezar():
    """Las secciones de «Para empezar a trabajar», en su orden."""
    salida = []
    for capitulo, apartados in PARA_EMPEZAR:
        s = seccion(capitulo, apartados)
        if s:
            suyos = [(a, [f for f in fs if f["nombre"] not in EMPEZAR_FUERA]) for a, fs in s["apartados"]]
            s = {**s, "apartados": suyos, "n": sum(len(fs) for _, fs in suyos), "entero": False}
            corto = _CORTOS_EMPEZAR.get(capitulo)
            salida.append({**s, "corto": corto, "titulo": corto} if corto else s)
    return salida


def es_para_empezar(f):
    """La ficha está en uno de los apartados de `PARA_EMPEZAR`."""
    return f["nombre"] not in EMPEZAR_FUERA and any(
        f["capitulo"] == c and f.get("apartado") in apartados for c, apartados in PARA_EMPEZAR)


def clave(f):
    """Lo que distingue a una ficha de todas las demás: el id se repite entre capítulos."""
    return f"{f['capitulo']}/{f['id']}"


# Terminaciones que distinguen al oficio de la actividad y de quien la hace:
# «limpiador», «limpiadora», «limpieza» y «limpiar» son la misma búsqueda. De
# la más larga a la más corta; la raíz no baja de cinco letras (con cuatro,
# «soldador» se quedaba en «sold» y encontraba «Sold Out»).
_TERMINACIONES = sorted([
    "adores", "adoras", "ador", "adora", "edores", "edoras", "edor", "edora", "idores", "idoras",
    "idor", "idora", "aciones", "acion", "iciones", "icion", "ciones", "cion", "mientos", "miento",
    "erias", "eria", "eros", "eras", "ero", "era", "istas", "ista", "ezas", "eza", "antes", "ante",
    "entes", "ente", "ajes", "aje", "icos", "icas", "ico", "ica", "ados", "adas", "ado", "ada",
    "ar", "er", "ir", "os", "as", "es", "o", "a", "e", "s",
], key=len, reverse=True)


def raiz(palabra):
    """«limpiador», «limpieza» -> «limpi». Sin diccionario: quita la terminación
    más larga que deje al menos cinco letras."""
    for t in _TERMINACIONES:
        if palabra.endswith(t) and len(palabra) - len(t) >= 5:
            return palabra[:-len(t)]
    return palabra


def busca(texto, tope=40):
    """Las fichas de los sectores que nombran todas las palabras de `texto`.

    Sin acentos ni mayúsculas, y por la raíz de la palabra: «limpiador» da lo
    mismo que «limpieza». Primero las que lo llevan en el nombre, luego en el
    apartado y luego en lo que hacen, y delante las que traen la palabra tal
    cual; a igualdad, en el orden de la guía. Solo se mira en los sectores que
    contratan y en los centros especiales de empleo: es el buscador de «Dónde
    enviar el CV», no el de los recursos de orientación.
    """
    palabras = [p for p in normaliza(texto or "").split() if len(p) > 1]
    if not palabras:
        return []
    raices = [raiz(p) for p in palabras]

    def peso(p, r, campos):
        """0-2 si la palabra está tal cual en el nombre, el apartado o el resto;
        3-5 si solo está su raíz al principio de alguna palabra; None si no está."""
        for n, campo in enumerate(campos):
            if p in campo:
                return n
        for n, campo in enumerate(campos):
            if any(w.startswith(r) for w in campo.split()):
                return 3 + n
        return None

    hallazgos = []
    capitulos = sectores() + ["09-insercion"]
    for orden, capitulo in enumerate(capitulos):
        for n, f in enumerate(_FICHAS.get(capitulo, [])):
            campos = (normaliza(f["nombre"]), normaliza(f.get("apartado", "")),
                      normaliza(f"{f.get('que', '')} {f.get('como', '')} {CAPITULOS[capitulo]['titulo']}"))
            pesos = [peso(p, r, campos) for p, r in zip(palabras, raices)]
            if None in pesos:
                continue
            hallazgos.append((sum(pesos), orden, n, f))
    hallazgos.sort(key=lambda h: h[:3])
    return [f for *_, f in hallazgos[:tope]]


SIN_COMPROBAR = "Sugeridas por IA, sin comprobar: confirma en su web antes de enviar"


def lista(fichas_, titulo="Tu lista"):
    """Unas fichas sueltas (las marcadas a mano) con la forma de una sección,
    para pintarlas con `apartados_html` o imprimirlas con `pdf`. None si no hay.

    Las que ha sugerido la IA (`ia: True`, ver `herramientas/guia/motor.py`)
    van en su propio apartado, que dice que nadie las ha comprobado: en el
    papel no pueden confundirse con las de la guía."""
    fichas_ = list(fichas_)
    if not fichas_:
        return None
    de_la_guia = [f for f in fichas_ if not f.get("ia")]
    de_la_ia = [f for f in fichas_ if f.get("ia")]
    apartados = ([("Empresas elegidas", de_la_guia)] if de_la_guia else []) \
        + ([(SIN_COMPROBAR, de_la_ia)] if de_la_ia else [])
    return {
        "capitulo": "lista", "titulo": titulo, "corto": titulo, "entero": False,
        "apartados": apartados, "n": len(fichas_), "general": False,
    }


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


def ficha_html(f, nombre=True, caja=True):
    """Una ficha en pantalla: nombre, a qué se dedica, cómo presentarse y el canal.

    Sin `nombre` ni `caja` queda solo el cuerpo: lo usa la pestaña «Dónde
    enviar el CV», donde el nombre es la casilla con que se marca la empresa."""
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
        ('<div class="gu-ficha">' if caja else '<div class="gu-cuerpo">')
        + (f'<div class="gu-nom">{esc(f["nombre"])}</div>' if nombre else "")
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
        trozos.append('<div class="gu-rejilla">' + "".join(ficha_html(f) for f in suyas) + "</div>")
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
        if s.get("nota"):
            cab.append(Paragraph(_esc(s["nota"]), e_texto))
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
