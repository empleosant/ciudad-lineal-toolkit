"""
Batería de «Dónde enviar el CV»: la guía de empleo dentro de la app.

Las fichas son una copia de la Guía de empleo de Madrid (`comun/datos/guia/`,
la saca `scripts/traer_guia.py`) y lo único hecho a mano es la tabla que une
cada ocupación del catálogo SISPE con sus capítulos
(`comun/datos/ocupaciones_sectores.csv`). Lo que se comprueba:

  · que la copia está entera: cada ficha en un capítulo y un apartado que existen;
  · que la tabla no apunta a nada que no exista, ni lleva prefijos que no casan
    con ninguna ocupación del catálogo;
  · los casos de `casos_guia.csv`: el sector que tiene que salir primero;
  · que la mayoría del catálogo tiene sector, y que lo que no lo tiene cae en lo general;
  · que juntar varias ocupaciones (las de un currículo) ordena bien;
  · que los centros especiales de empleo salen aparte del resto de empresas;
  · que la lista para imprimir se construye y lleva lo que tiene que llevar;
  · y las pantallas: el desplegable del codificador, el paso 4 del CV, el
    cierre de los informes (que pide las empresas a la guía), y lo plegado
    en formación y extranjería.

`casos_guia.csv` SOLO SE EDITA A MANO: el código y la denominación se copian
del catálogo y el capítulo se decide leyendo la guía, nunca copiándolo de lo
que conteste `comun/guia.py`.

USO
    python3 guia.py                     # los datos y la tabla, con el python3 del sistema
    ~/.venvs/sispe/bin/python guia.py   # también el PDF y las pantallas (AppTest)

No llama a la IA ni gasta cuota.
"""

import csv
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from comun import guia  # noqa: E402

CATALOGO = os.path.join(RAIZ, "herramientas", "sispe", "datos", "ocupaciones_sispe_ultraligero.txt")
CASOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "casos_guia.csv")
COBERTURA_MINIMA = 0.80      # hoy, 1.865 de 2.218 (84 %): lo que falta es campo, minas, mar y ciencia

RESUMEN = []


def informe(nombre, fallos, total):
    pasa = not fallos
    RESUMEN.append((nombre, pasa))
    print(f"[{' OK ' if pasa else 'MAL'}] {nombre:52} {max(0, total - len(fallos)):4}/{total}")
    for f in fallos[:12]:
        print(f"          · {f}")
    if len(fallos) > 12:
        print(f"          · … y {len(fallos) - 12} más")
    return pasa


def catalogo():
    with open(CATALOGO, encoding="utf-8") as f:
        return dict(l.strip().split(":", 1) for l in f if ":" in l)


def _todas():
    return [f for c in guia.CAPITULOS for f in guia.fichas(c)]


def p_la_copia_esta_entera():
    fallos = []
    todas = _todas()
    if len(todas) != guia.EDICION["fichas"]:
        fallos.append(f"edicion.json dice {guia.EDICION['fichas']} fichas y se leen {len(todas)}")
    for f in todas:
        cap = guia.CAPITULOS.get(f["capitulo"])
        if cap is None:
            fallos.append(f"{f['id']}: capítulo {f['capitulo']} que no existe")
        elif f["apartado"] not in cap["apartados"]:
            fallos.append(f"{f['id']}: apartado «{f['apartado']}» que no está en {f['capitulo']}")
        if not f["nombre"]:
            fallos.append(f"{f['id']}: sin nombre")
        if not any(f.get(k) for k in ("web", "web_empleo", "correo", "telefono", "direccion")):
            fallos.append(f"{f['id']}: sin ninguna forma de contacto")
    return informe("La copia de la guía está entera", fallos, len(todas))


def p_la_tabla_apunta_a_lo_que_existe():
    fallos = []
    codigos = list(catalogo())
    filas = 0
    for prefijo, destinos in guia._TABLA.items():
        filas += len(destinos)
        if not prefijo.isdigit() or len(prefijo) > 8:
            fallos.append(f"prefijo raro: {prefijo!r}")
        if not any(c.startswith(prefijo) for c in codigos):
            fallos.append(f"{prefijo}: no casa con ninguna ocupación del catálogo")
        if len(set(destinos)) != len(destinos):
            fallos.append(f"{prefijo}: filas repetidas")
        for capitulo, apartado in destinos:
            if capitulo == "-":
                continue
            cap = guia.CAPITULOS.get(capitulo)
            if cap is None:
                fallos.append(f"{prefijo}: capítulo {capitulo} que no existe")
            elif apartado and apartado not in cap["apartados"]:
                fallos.append(f"{prefijo}: «{apartado}» no es un apartado de {capitulo}")
    return informe("La tabla apunta a capítulos y apartados que existen", fallos, filas)


def p_los_casos():
    fallos = []
    nombres = catalogo()
    with open(CASOS, encoding="utf-8", newline="") as f:
        casos = list(csv.DictReader(l for l in f if not l.startswith("#")))
    for c in casos:
        if nombres.get(c["codigo"]) != c["denominacion"]:
            fallos.append(f"{c['codigo']}: en el catálogo es «{nombres.get(c['codigo'])}»")
            continue
        secs = guia.secciones([c["codigo"]])
        primero = "" if not secs or secs[0]["general"] else secs[0]["capitulo"]
        if primero != c["capitulo"]:
            fallos.append(f"{c['codigo']} {c['denominacion'][:40]}: sale «{primero or 'lo general'}» "
                          f"y debe salir «{c['capitulo'] or 'lo general'}»")
    return informe("Cada ocupación de casos_guia.csv, su sector", fallos, len(casos))


def p_cobertura_y_lo_general():
    fallos = []
    codigos = list(catalogo())
    con = [c for c in codigos if guia.destinos(c)]
    parte = len(con) / len(codigos)
    print(f"          {len(con)} de {len(codigos)} ocupaciones con sector ({parte:.0%})")
    if parte < COBERTURA_MINIMA:
        fallos.append(f"solo el {parte:.0%} del catálogo tiene sector (mínimo {COBERTURA_MINIMA:.0%})")
    sin = next(c for c in codigos if not guia.destinos(c))
    secs = guia.secciones([sin])
    if not secs or not all(s["general"] for s in secs):
        fallos.append(f"{sin}: sin sector no cae en lo general")
    elif [s["capitulo"] for s in secs] != [c for c, _ in guia.GENERALES]:
        fallos.append(f"lo general sale como {[s['capitulo'] for s in secs]}")
    if guia.secciones([sin], generales=False):
        fallos.append("con generales=False, una ocupación sin sector devuelve algo")
    if guia.secciones([]):
        fallos.append("sin ocupaciones devuelve algo")
    return informe("La mayoría tiene sector; lo demás cae en lo general", fallos, 4)


def p_un_curriculo_con_varias():
    """Lo que hace el paso 4 del CV: varias ocupaciones, un solo listado."""
    fallos = []
    camarero, dependiente, reponedor = "51201038", "52201079", "98201011"
    secs = guia.secciones([camarero, dependiente, reponedor])
    caps = [s["capitulo"] for s in secs]
    if caps[:2] != ["10-comercio", "11-hosteleria"]:
        fallos.append(f"comercio (dos ocupaciones) tiene que ir antes que hostelería (una): {caps[:3]}")
    if len(caps) != len(set(caps)):
        fallos.append("un capítulo sale dos veces")
    comercio = secs[0]
    if not comercio["entero"]:
        fallos.append("el dependiente pide el capítulo de comercio entero y sale recortado")
    n_entero = len(guia.fichas("10-comercio"))
    if comercio["n"] != n_entero:
        fallos.append(f"comercio entero son {n_entero} fichas y salen {comercio['n']}")
    hoste = secs[1]
    if hoste["entero"] or [a for a, _ in hoste["apartados"]] != ["Cadenas de restauración", "Hoteles"]:
        fallos.append(f"hostelería del camarero: {[a for a, _ in hoste['apartados']]}")
    if any(s["general"] for s in secs):
        fallos.append("con sector, no tiene que salir lo general")
    return informe("Varias ocupaciones: un listado, ordenado por votos", fallos, 6)


def p_los_cee_van_aparte():
    """Pedido el 03/10/2026: buscando limpieza, los centros especiales de empleo
    salen en su propio apartado y no mezclados con el resto de empresas."""
    fallos = []
    secs = guia.secciones(["92101050"])                 # personal de limpieza
    por = {s["capitulo"]: s for s in secs}
    cee = por.get(guia.CEE)
    if not cee:
        return informe("Los centros especiales de empleo, aparte", ["limpieza no tiene sección aparte"], 9)
    nombres = lambda s: [f["nombre"] for _, fs in s["apartados"] for f in fs]  # noqa: E731
    limpieza, aparte = nombres(por["13-limpieza"]), nombres(cee)
    if "Grupo Osga" in limpieza or "Grupo Osga" not in aparte:
        fallos.append("Grupo Osga (centro especial) sigue mezclado con las empresas de limpieza")
    if "Serlingo" not in limpieza or "Serlingo" not in aparte:
        fallos.append("Serlingo (empresa corriente con centro especial) tiene que estar en los dos sitios")
    if "Ceelimp" in aparte:
        fallos.append("Ceelimp no es un centro especial: «Cee» no es «CEE»")
    if aparte.count("Grupo SIFU") != 1:
        fallos.append(f"Grupo SIFU sale {aparte.count('Grupo SIFU')} veces (está en limpieza y en el cap. 9)")
    if "Apadis" not in aparte:
        fallos.append("faltan los centros del capítulo 9 que trabajan en limpieza (Apadis)")
    if not cee.get("nota") or "33 %" not in cee["nota"]:
        fallos.append("la sección aparte no explica qué hace falta para entrar")
    camarero = [s["capitulo"] for s in guia.secciones(["51201038"])]
    if camarero.index(guia.CEE) > camarero.index("24-portales"):
        fallos.append(f"la sección aparte tiene que ir antes de los portales: {camarero}")
    if any(s["capitulo"] == guia.CEE for s in guia.secciones(["25111040"])):
        fallos.append("un abogado no tiene centros especiales en su sector y le sale la sección")
    sin = {s["capitulo"]: s for s in guia.secciones(["92101050"], cee=False)}
    if "Grupo Osga" not in nombres(sin["13-limpieza"]) or guia.CEE in sin:
        fallos.append("con cee=False tiene que salir todo junto, como antes")
    return informe("Los centros especiales de empleo, aparte", fallos, 9)


def p_las_direcciones_se_leen_como_en_la_guia():
    fallos = []
    esperado = {
        "https://europe.alsea.net/talento": "europe.alsea.net/talento",
        "https://www.ejemplo.com/": "ejemplo.com",
        "https://empleo.ejemplo.es/ofertas?utm=1#arriba": "empleo.ejemplo.es/ofertas",
        "https://portal.ejemplo.com/una/ruta/muy/larga/que/no/cabe/Candidatos": "portal.ejemplo.com/…/Candidatos",
    }
    for url, debe in esperado.items():
        if guia.vista(url) != debe:
            fallos.append(f"{url} -> {guia.vista(url)!r}, debe {debe!r}")
    f = {"telefono": "915221101;611672682", "direccion": "C/ Fuencarral, 43", "cp": "28004",
         "municipio": "Madrid", "web": "https://a.es", "web_empleo": ""}
    if guia.telefonos(f) != "915 221 101 · 611 672 682":
        fallos.append(f"teléfonos: {guia.telefonos(f)!r}")
    if guia.direccion(f) != "C/ Fuencarral, 43 · 28004 Madrid":
        fallos.append(f"dirección: {guia.direccion(f)!r}")
    if guia.enlace(f) != ("https://a.es", "Web"):
        fallos.append(f"sin web de empleo, el enlace es la web: {guia.enlace(f)}")
    return informe("Direcciones, teléfonos y enlaces, como en la guía", fallos, len(esperado) + 3)


def p_la_lista_para_imprimir():
    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("[ -- ] La lista para imprimir: sin reportlab no se prueba (usa ~/.venvs/sispe)")
        return True
    fallos = []
    secs = guia.secciones(["51201038"])
    datos = guia.pdf(secs, "Dónde enviar tu currículum", "Camarero de sala",
                     puesto="camarero de sala", nombre="Lucía")
    if not datos.startswith(b"%PDF"):
        fallos.append("no es un PDF")
    try:
        import pypdfium2
    except ImportError:
        print("          (sin pypdfium2 no se lee el texto: solo se comprueba que se construye)")
        return informe("La lista para imprimir se construye", fallos, 1)
    doc = pypdfium2.PdfDocument(datos)
    texto = " ".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
    texto = " ".join(texto.split())
    for debe in ("Busco trabajo de camarero de sala", "me llamo Lucía", "Alsea",
                 "europe.alsea.net/talento", "Portales de empleo", guia.EDICION["verificado"]):
        if debe not in texto:
            fallos.append(f"no aparece «{debe}»")
    if not 2 <= len(doc) <= 6:
        fallos.append(f"{len(doc)} páginas para un camarero (se esperan de 2 a 6)")
    general = guia.pdf(guia.secciones(["95111016"]), "Dónde enviar tu currículum")
    doc = pypdfium2.PdfDocument(general)
    texto = " ".join(" ".join(doc[i].get_textpage().get_text_range() for i in range(len(doc))).split())
    if "La guía no tiene un sector" not in texto or "[tu nombre]" not in texto:
        fallos.append("sin sector ni nombre, la lista no lo dice o no deja los huecos")
    return informe("La lista para imprimir lleva lo que tiene que llevar", fallos, 9)


# ---------------------------------------------------------------------------
# Las pantallas
# ---------------------------------------------------------------------------

ENVOLTORIO = """
import os, sys
RAIZ = {raiz!r}
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
DeltaGenerator.page_link = lambda self, *a, **k: None
st.page_link = lambda *a, **k: None
ruta = os.path.join(RAIZ, {pagina!r})
exec(compile(open(ruta, encoding="utf-8").read(), ruta, "exec"),
     {{"__name__": "__main__", "__file__": ruta}})
"""


def abre(pagina, estado=None):
    from streamlit.testing.v1 import AppTest
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(ENVOLTORIO.format(raiz=RAIZ, pagina=pagina))
    tmp.close()
    at = AppTest.from_file(tmp.name, default_timeout=120)
    for k, v in (estado or {}).items():
        at.session_state[k] = v
    at.run()
    return at


def _hay_streamlit(nombre):
    try:
        import streamlit  # noqa: F401
        return True
    except ImportError:
        print(f"[ -- ] {nombre}: sin Streamlit no se prueba (usa ~/.venvs/sispe)")
        return False


def p_pantalla_codificador():
    """Buscar sin IA un camarero: bajo las tarjetas salen los sectores y sus fichas."""
    nombre = "Codificador: tarjetas, «+ CV» y «Dónde enviar el CV»"
    if not _hay_streamlit(nombre):
        return True
    fallos = []
    at = abre("herramientas/sispe/vista.py", {"sispe_usar_ia": False})
    at.text_input(key="consulta").input("camarero de sala").run()
    if at.exception:
        fallos.append(f"excepción: {str(at.exception[0].value)[:100]}")
        return informe(nombre, fallos, 5)
    pildoras = [b for b in at.get("button_group") if (b.key or "").startswith("sispe_guia_sec_")]
    if not pildoras:
        fallos.append("no están las píldoras de sectores")
    elif not pildoras[0].options or not pildoras[0].options[0].startswith("Hostelería"):
        fallos.append(f"el primer sector no es Hostelería: {pildoras[0].options[:2]}")
    # Las empresas del sector van en el panel de la derecha, cada una con su casilla
    casillas = [c for c in at.checkbox if (c.key or "").startswith("mesa_c_sispe_11-hosteleria/")]
    if not casillas:
        fallos.append("no salen las empresas de hostelería con su casilla")
    else:
        casillas[0].check().run()
        marcadas = list(at.session_state["mesa_empresas"]) if "mesa_empresas" in at.session_state else []
        if len(marcadas) != 1 or not marcadas[0].startswith("11-hosteleria/"):
            fallos.append(f"marcar una empresa no la lleva a la lista ({marcadas})")
    if not any("imprimir" in b.proto.label for b in at.get("download_button")):
        fallos.append("falta el botón de la lista para imprimir")
    # El «+ CV» pequeño de la cabecera de la tarjeta sigue mandando la ocupación al CV
    at.text_input(key="consulta").input("51201038").run()
    boton = [x for x in at.button if x.key == "addcv_51201038"]
    if not boton:
        fallos.append("la tarjeta no lleva el botón «+ CV»")
    else:
        boton[0].click().run()
        en_cv = [e["codigo"] for e in at.session_state["cv_datos"]["experiencias"]]
        ahora = [x for x in at.button if x.key == "addcv_51201038"]
        if en_cv != ["51201038"] or not ahora or not ahora[0].disabled:
            fallos.append(f"«+ CV» no pasa la ocupación al currículo ({en_cv})")
    return informe(nombre, fallos, 5)



def p_el_buscador_de_la_guia():
    """`guia.busca`: sin acentos, el nombre por delante, y nada si no hay nada."""
    nombre = "El buscador de la guía y la lista de marcadas"
    fallos = []
    barcelo = guia.busca("barcelo hotel")
    if not barcelo or not barcelo[0]["nombre"].startswith("Barceló"):
        fallos.append(f"«barcelo hotel» no encuentra primero a Barceló: {[f['nombre'] for f in barcelo[:3]]}")
    limpieza = guia.busca("limpieza oficinas")
    if not limpieza or any(f["capitulo"] not in guia.sectores() + ["09-insercion"] for f in limpieza):
        fallos.append("«limpieza oficinas» no da fichas, o las da de fuera de los sectores")
    if guia.busca("zzzzqq") or guia.busca("") or guia.busca("  a "):
        fallos.append("busca algo donde no hay nada que buscar")
    if len(guia.busca("hotel", tope=5)) != 5:
        fallos.append("el tope no se respeta")
    # Palabras parecidas, misma búsqueda: Álvaro vio 1 resultado con «limpiador» y 60 con «limpieza»
    cuentas = {p: len(guia.busca(p, tope=999)) for p in ("limpiador", "limpiadora", "limpieza", "limpiar")}
    if min(cuentas.values()) < 50 or max(cuentas.values()) - min(cuentas.values()) > 5:
        fallos.append(f"palabras de la misma familia dan resultados distintos: {cuentas}")
    if [f["nombre"] for f in guia.busca("soldador")] and guia.raiz("soldador") == "sold":
        fallos.append("la raíz de «soldador» se queda en «sold» y encuentra «Sold Out»")
    from herramientas.guia import motor as guia_motor
    soldador = guia_motor.busca("soldador")
    if not soldador or "Industria" not in soldador[0][0]:
        fallos.append(f"«soldador» no lleva al sector de su ocupación: {[a for a, _ in soldador]}")
    if guia_motor.busca("zzzzqq") or len(guia_motor.busca("barcelo")) != 1:
        fallos.append("el sector de la ocupación se cuela donde no toca")
    claves = [guia.clave(f) for fs in guia._FICHAS.values() for f in fs]
    if len(claves) != len(set(claves)):
        fallos.append("hay dos fichas con la misma clave: las casillas chocarían")
    if guia.lista([]) is not None:
        fallos.append("una lista vacía no es None")
    lista = guia.lista(barcelo[:2])
    if not lista or lista["n"] != 2 or [f for _, fs in lista["apartados"] for f in fs] != barcelo[:2]:
        fallos.append("la lista de marcadas no tiene forma de sección")
    return informe(nombre, fallos, 10)


RESPUESTA_IA = """```json
{"empresas": [
 {"nombre": "Estudio Comprobado", "que": "Estudio de videojuegos [1]", "donde": "Madrid",
  "como": "Portal de empleo propio", "dominio": "https://www.estudiocomprobado.com/jobs"},
 {"nombre": "Estudio Nombrado", "que": "Estudio independiente", "donde": "Alcobendas", "dominio": "nombrado.es"},
 {"nombre": "Inventada SL", "que": "No sale en ninguna página", "dominio": "inventada.es"},
 {"nombre": "Barceló Hotel Group", "que": "Lo que diga el modelo"},
 {"nombre": "estudio comprobado", "que": "repetida"}
]}
```"""
FUENTES_IA = [("estudiocomprobado.com", "https://vertexaisearch.example/a"),
              ("listado.org", "https://vertexaisearch.example/b")]
APOYOS_IA = [("Estudio Nombrado es un estudio de Alcobendas", [1])]


def p_las_sugeridas_por_ia():
    """`motor.interpreta`: enlaces solo si la búsqueda los vio, y sin fuente no hay ficha."""
    nombre = "Empresas sugeridas por IA: solo lo que la búsqueda respalda"
    from herramientas.guia import motor as guia_motor
    fallos = []
    fichas, descartadas = guia_motor.interpreta(RESPUESTA_IA, FUENTES_IA, APOYOS_IA)
    por_nombre = {f["nombre"]: f for f in fichas}
    if list(por_nombre) != ["Estudio Comprobado", "Estudio Nombrado", "Barceló Hotel Group"] or descartadas != 1:
        fallos.append(f"quedan {list(por_nombre)} y se descartan {descartadas}")
        return informe(nombre, fallos, 8)
    comprobado, nombrado, barcelo = por_nombre.values()
    if comprobado["web"] != "https://estudiocomprobado.com" or "[1]" in comprobado["que"]:
        fallos.append(f"la web comprobada no sale limpia: {comprobado['web']} / {comprobado['que']}")
    if nombrado["web"] or "listado.org" not in nombrado["como"]:
        fallos.append("una empresa cuyo dominio no vio la búsqueda sale con enlace, o sin decir dónde se la vio")
    if not (comprobado.get("ia") and nombrado.get("ia")) or barcelo.get("ia") or barcelo["capitulo"] != "11-hosteleria":
        fallos.append("no se distingue lo de la IA de lo de la guía (Barceló debe salir con su ficha de la guía)")
    if "vertexaisearch" in " ".join(str(v) for f in fichas for v in f.values()):
        fallos.append("se cuela la dirección de salto de Google, que caduca")
    sin_apoyos, d = guia_motor.interpreta(RESPUESTA_IA, FUENTES_IA, [])
    if d or any(f["web"] for f in sin_apoyos if f["nombre"] == "Inventada SL"):
        fallos.append("sin apoyos no se puede descartar, pero tampoco dar enlace")
    if guia_motor.interpreta("no es json", [], []) != ([], 0) or guia_motor.interpreta('{"empresas": "x"}') != ([], 0):
        fallos.append("una respuesta rota tumba el intérprete")
    ida = guia_motor.desempaqueta(guia_motor.empaqueta(fichas, "03/10/2026"))
    if ida != (fichas, "03/10/2026") or guia_motor.desempaqueta("roto") != ([], ""):
        fallos.append("lo guardado en el Gist no vuelve igual")
    lista = guia.lista(fichas)
    rotulos = [a for a, _ in lista["apartados"]]
    if len(rotulos) != 2 or "sin comprobar" not in rotulos[1] or [f["nombre"] for f in lista["apartados"][0][1]] != ["Barceló Hotel Group"]:
        fallos.append(f"en la lista para imprimir no van aparte: {rotulos}")
    try:
        if bytes(guia.pdf([lista], "Dónde enviar tu currículum", puesto="programador")[:4]) != b"%PDF":
            fallos.append("la lista con sugeridas no da un PDF")
    except Exception as e:  # noqa: BLE001
        fallos.append(f"la lista con sugeridas no se imprime: {type(e).__name__}: {e}")
    return informe(nombre, fallos, 8)


BUSCADOR_DE_MENTIRA = """
import comun.ia as ia
import herramientas.guia.modelo as modelo_guia
ia.tiene_clave = lambda prov: True
LLAMADAS = []
def _busca(puesto, sector="", ya=(), al_relevar=None, para_empezar=False):
    LLAMADAS.append((puesto, para_empezar))
    if {falla!r}:
        raise RuntimeError("429 cupo de búsquedas agotado")
    return {respuesta!r}, {fuentes!r}, {apoyos!r}
modelo_guia.busca = _busca
"""


def p_pantalla_empresas_con_ia():
    """El botón «Buscar más empresas con IA», con un buscador de mentira que contesta o se cae."""
    nombre = "Dónde enviar el CV: más empresas con IA, marcarlas y el cupo agotado"
    if not _hay_streamlit(nombre):
        return True
    from streamlit.testing.v1 import AppTest
    fallos = []
    for falla in (False, True):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
        tmp.write(ENVOLTORIO.format(raiz=RAIZ, pagina="herramientas/guia/vista.py").replace(
            "ruta = os.path.join", BUSCADOR_DE_MENTIRA.format(
                falla=falla, respuesta=RESPUESTA_IA, fuentes=FUENTES_IA, apoyos=APOYOS_IA) + "\nruta = os.path.join"))
        tmp.close()
        at = AppTest.from_file(tmp.name, default_timeout=120)
        at.run()
        at.text_input(key="guia_consulta").input("programador de videojuegos").run()
        boton = [b for b in at.button if b.key == "guia_ia_buscar"]
        if at.exception or not boton or boton[0].disabled:
            fallos.append("no sale el botón de buscar con IA para un oficio escrito a mano")
            continue
        boton[0].click().run()
        if at.exception:
            fallos.append(f"excepción al buscar: {str(at.exception[0].value)[:120]}")
            continue
        casillas = [c for c in at.checkbox if (c.key or "").startswith("mesa_c_guia_ia/")]
        if falla:
            if casillas or not any("cupo" in w.value for w in at.warning):
                fallos.append("con el cupo agotado no se avisa, o salen fichas de la nada")
            continue
        html = " ".join(m.value for m in at.markdown)
        if len(casillas) != 2 or "sin comprobar" not in html:
            fallos.append(f"las sugeridas no salen con casilla y etiqueta ({len(casillas)} casillas)")
            continue
        casillas[0].check().run()
        marcadas = list(at.session_state["mesa_empresas"].values())
        if at.exception or len(marcadas) != 1 or not marcadas[0].get("ia"):
            fallos.append("una sugerida marcada no llega a su lista")
        # Con resultados, el botón pasa a ser «Regenerar», arriba y activo
        regenerar = [b for b in at.button if b.key == "guia_ia_buscar"]
        if not regenerar or "Regenerar" not in regenerar[0].label or regenerar[0].disabled:
            fallos.append("tras buscar no queda a la vista el botón de regenerar")
        else:
            regenerar[0].click().run()
            if at.exception or len([c for c in at.checkbox if (c.key or "").startswith("mesa_c_guia_ia/")]) != 2:
                fallos.append("regenerar rompe la pantalla o pierde las fichas")
    return informe(nombre, fallos, 5)


def p_para_empezar_a_trabajar():
    """El filtro «sin experiencia ni titulación»: la selección a mano y la pantalla."""
    nombre = "Para empezar a trabajar: la selección existe y la pantalla la enseña"
    fallos = []
    for capitulo, apartados in guia.PARA_EMPEZAR:
        cap = guia.CAPITULOS.get(capitulo)
        for a in apartados:
            if cap is None or a not in cap["apartados"] or not guia.fichas(capitulo, a):
                fallos.append(f"{capitulo} / {a}: no existe en la guía o no tiene fichas")
    secs = guia.para_empezar()
    if len(secs) != len(guia.PARA_EMPEZAR) or any(len(s["corto"]) > 30 for s in secs):
        fallos.append("falta algún sector, o su nombre no cabe en una píldora")
    nombres = {f["nombre"] for c, aps in guia.PARA_EMPEZAR for ap in aps for f in guia.fichas(c, ap)}
    if guia.EMPEZAR_FUERA - nombres:
        fallos.append(f"se excluyen fichas que no existen: {sorted(guia.EMPEZAR_FUERA - nombres)}")
    if any(f["nombre"] in guia.EMPEZAR_FUERA for s in secs for _, fs in s["apartados"] for f in fs):
        fallos.append("las fichas excluidas siguen saliendo")
    fuera = [f for f in guia.fichas("19-seguridad") + guia.fichas("14-cuidados") if guia.es_para_empezar(f)]
    if fuera or not guia.es_para_empezar(guia.fichas("13-limpieza", "Empresas de limpieza")[0]):
        fallos.append("se cuela lo que pide habilitación o certificado, o falta la limpieza")
    from herramientas.guia import modelo as guia_modelo
    if "SIN experiencia" not in guia_modelo.entrada("mozo", para_empezar=True) \
            or "SIN experiencia" in guia_modelo.entrada("mozo"):
        fallos.append("la IA no recibe (o recibe siempre) la condición de puestos de entrada")
    if not _hay_streamlit(nombre):
        return informe(nombre, fallos, 10)
    at = abre("herramientas/guia/vista.py", dict(MESA))
    at.toggle(key="guia_empezar").set_value(True).run()
    pildoras = [b for b in at.get("button_group") if b.key == "guia_sector_empezar"]
    if at.exception or not pildoras or not pildoras[0].options[0].startswith("Limpieza"):
        fallos.append("con el filtro puesto no salen los sectores para empezar")
    if not [c for c in at.checkbox if "13-limpieza/" in (c.key or "")]:
        fallos.append("con el filtro puesto no salen las fichas de limpieza")
    at.text_input(key="guia_consulta").input("seguridad").run()
    if at.exception or [c for c in at.checkbox if "19-seguridad/" in (c.key or "")]:
        fallos.append("buscando con el filtro salen fichas de fuera de la selección")
    at.button(key="guia_nueva").click().run()
    if at.exception or at.session_state["guia_consulta"] or at.session_state["guia_empezar"]:
        fallos.append("«Nueva búsqueda» no deja el buscador limpio")
    return informe(nombre, fallos, 10)


MESA = {
    "sispe_actual": ("camarero de sala", {"ocupaciones": [
        {"codigo": "51201038", "denominacion": "CAMAREROS DE SALA O JEFES DE RANGO"}]}),
}


def p_pantalla_donde_enviar():
    """La pestaña de la guía: sectores de la mesa, casillas, buscador y vaciado."""
    nombre = "Dónde enviar el CV: sectores de la mesa, su lista y «Vaciar»"
    if not _hay_streamlit(nombre):
        return True
    fallos = []
    at = abre("herramientas/guia/vista.py", dict(MESA))
    if at.exception:
        fallos.append(f"excepción: {str(at.exception[0].value)[:100]}")
        return informe(nombre, fallos, 6)
    pildoras = [b for b in at.get("button_group") if (b.key or "").startswith("guia_sector_mesa_")]
    if not pildoras or not pildoras[0].options[0].startswith("Hostelería"):
        fallos.append("no salen los sectores de la ocupación que hay en la mesa")
    if "En la mesa" not in " ".join(m.value for m in at.markdown):
        fallos.append("no se pinta la franja «En la mesa»")
    casillas = [c for c in at.checkbox if (c.key or "").startswith("mesa_c_guia_")]
    if not casillas:
        fallos.append("las fichas no llevan casilla")
        return informe(nombre, fallos, 6)
    casillas[0].check().run()
    imprimir = [b for b in at.get("download_button") if "su lista" in b.proto.label]
    if len(at.session_state["mesa_empresas"]) != 1 or not imprimir or imprimir[0].proto.disabled:
        fallos.append("marcar una empresa no deja imprimir su lista")
    at.text_input(key="guia_consulta").input("limpieza de oficinas").run()
    if at.exception or not [c for c in at.checkbox if "13-limpieza/" in (c.key or "")]:
        fallos.append("el buscador no enseña las fichas que encuentra")
    if len(at.session_state["mesa_empresas"]) != 1:
        fallos.append("buscar pierde lo que estaba marcado")
    vaciar = [b for b in at.button if b.key == "vaciar_mesa"]
    if not vaciar:
        fallos.append("falta el botón de vaciar la mesa")
    else:
        vaciar[0].click().run()
        quedan = at.session_state["mesa_empresas"] if "mesa_empresas" in at.session_state else {}
        if at.exception or quedan or at.session_state["sispe_actual"]:
            fallos.append("«Vaciar» no deja la mesa limpia")
    return informe(nombre, fallos, 6)


def p_pantalla_portada():
    """La portada: una columna por momento con todas las herramientas del registro."""
    nombre = "Portada: los momentos de la cita y todas las herramientas"
    if not _hay_streamlit(nombre):
        return True
    from comun import registro
    fallos = []
    at = abre("inicio.py")
    if at.exception:
        fallos.append(f"excepción: {str(at.exception[0].value)[:100]}")
        return informe(nombre, fallos, 4)
    html = " ".join(m.value for m in at.markdown)
    for _, rotulo, _ in registro.por_momento():
        if f"</i>{rotulo}</div>" not in html:
            fallos.append(f"falta la columna «{rotulo}»")
    faltan = [h["titulo"] for h in registro.HERRAMIENTAS if h["titulo"] not in html]
    if faltan:
        fallos.append(f"herramientas sin tarjeta: {faltan}")
    en_grupos = [h["id"] for _, _, hs in registro.por_momento() for h in hs]
    if sorted(en_grupos) != sorted(h["id"] for h in registro.HERRAMIENTAS):
        fallos.append("por_momento() pierde o repite herramientas")
    if not [t for t in at.text_input if t.key == "portada_consulta"]:
        fallos.append("falta el buscador de la portada")
    return informe(nombre, fallos, 4)


IA_DE_MENTIRA = """
import json
import comun.ia as ia
import herramientas.sispe.modelo as modelo
ia.cliente = lambda *a, **k: object()
modelo.interpreta_consulta = lambda *a, **k: []
def _flujo(cli, texto, candidatos, al_relevar=None):
    if {falla!r}:
        raise RuntimeError("el modelo de mentira se ha caído")
    codigos = [l.split(":")[0] for l in candidatos.splitlines()[:3]]
    yield json.dumps({{"ocupaciones": [{{"codigo": c, "motivo": "Elegida por la IA de mentira."}} for c in codigos]}})
modelo.flujo_modelo = _flujo
"""


def p_pantalla_codificador_con_ia():
    """El camino con IA, con un modelo de mentira que contesta o se cae.

    Ahí la pantalla pinta primero las tarjetas del catálogo («afinando…») y
    después las definitivas, en la misma pasada. Si las claves de los
    contenedores se repiten entre una pintada y otra, Streamlit para la página
    con StreamlitDuplicateElementKey: pasó en producción el 03/10/2026 con
    «camarero de videojuegos» y en local no se veía porque no hay claves de IA.
    """
    nombre = "Codificador con IA: pinta dos veces sin repetir claves"
    if not _hay_streamlit(nombre):
        return True
    fallos = []
    for falla in (False, True):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
        tmp.write(ENVOLTORIO.format(raiz=RAIZ, pagina="herramientas/sispe/vista.py").replace(
            "ruta = os.path.join", IA_DE_MENTIRA.format(falla=falla) + "\nruta = os.path.join"))
        tmp.close()
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(tmp.name, default_timeout=120)
        at.session_state["sispe_usar_ia"] = True
        at.run()
        at.text_input(key="consulta").input("programador de videojuegos").run()
        caso = "con el modelo caído" if falla else "con el modelo contestando"
        if at.exception:
            fallos.append(f"{caso}: {str(at.exception[0].value)[:120]}")
            continue
        botones = [b for b in at.button if (b.key or "").startswith("addcv_")]
        if len(botones) < 2:
            fallos.append(f"{caso}: no quedan las tarjetas pintadas ({len(botones)} «+ CV»)")
    return informe(nombre, fallos, 2)


def p_pantalla_curriculo():
    """El paso 4 del CV saca los sectores de las experiencias, también de las escritas a mano."""
    nombre = "Generador de CV: «Dónde enviarlo» en el paso 4"
    if not _hay_streamlit(nombre):
        return True
    from herramientas.cv import motor as cv_motor
    cv = cv_motor.nuevo()
    cv["nombre"] = "Lucía Pérez"
    cv["experiencias"].append(cv_motor.experiencia("51201038", "CAMAREROS DE SALA O JEFES DE RANGO"))
    for i, puesto in enumerate(["Dependienta de comercio", "Reponedora de hipermercado"], 1):
        e = cv_motor.experiencia()
        e.update(codigo=f"mano-{i}", puesto=puesto)
        cv["experiencias"].append(e)
    fallos = []
    at = abre("herramientas/cv/vista.py", {"cv_datos": cv, "cv_paso": 3})
    if at.exception:
        fallos.append(f"excepción: {str(at.exception[0].value)[:100]}")
        return informe(nombre, fallos, 3)
    pildoras = [b for b in at.get("button_group") if (b.key or "").startswith("cv_w_sectores_")]
    if not pildoras:
        fallos.append("no están las píldoras de sectores")
    else:
        valor = list(pildoras[0].value or [])
        if valor[:2] != ["10-comercio", "11-hosteleria"]:
            fallos.append(f"marcados de entrada: {valor} (comercio, con dos experiencias a mano, va primero)")
    if not any("Dónde enviar" in b.proto.label for b in at.get("download_button")):
        fallos.append("falta el botón «Dónde enviar este CV»")
    # Con empresas marcadas en la mesa, su lista va delante y ya elegida
    marcadas = guia.busca("barcelo hotel")[:1] + guia.busca("limpieza oficinas")[:1]
    at = abre("herramientas/cv/vista.py", {"cv_datos": cv, "cv_paso": 3,
                                             "mesa_empresas": {guia.clave(f): f for f in marcadas}})
    pildoras = [b for b in at.get("button_group") if (b.key or "").startswith("cv_w_sectores_")]
    if at.exception or not pildoras or list(pildoras[0].value or [])[:1] != ["lista"]:
        fallos.append("las empresas marcadas no salen delante en el paso 4")
    try:
        hoja = guia.pdf([guia.lista(marcadas)], "Dónde enviar tu currículum", puesto="camarera")
        if bytes(hoja[:4]) != b"%PDF":
            fallos.append("la lista de marcadas no da un PDF")
    except Exception as e:  # noqa: BLE001
        fallos.append(f"la lista de marcadas no se imprime: {type(e).__name__}: {e}")
    return informe(nombre, fallos, 5)


def p_pantalla_informes():
    """El cierre de los informes: el sector sale del objetivo y el correo lleva las webs."""
    nombre = "Informes: el correo con las empresas de la guía"
    if not _hay_streamlit(nombre):
        return True
    from herramientas.informes import motor as inf
    _, fichas = inf.empresas_de_la_guia(guia.secciones(["51201038"]))
    correo = ("Hola:\n\n**Dónde ir.**\n- **Alsea** — restauración.\n- **Bar Manolo** — barrio."
              "\n\nUn saludo,\nÁlvaro")
    fallos = []
    at = abre("herramientas/informes/vista.py", {
        "inf_w_objetivo1": "Camarero de sala", "inf_correo": correo, "inf_correo_guia": fichas,
    })
    if at.exception:
        fallos.append(f"excepción: {str(at.exception[0].value)[:100]}")
        return informe(nombre, fallos, 4)
    sectores = [m for m in at.multiselect if (m.key or "").startswith("inf_w_sectores_")]
    if not sectores or not sectores[0].value or sectores[0].value[0] != "11-hosteleria":
        fallos.append(f"el sector del camarero no sale marcado: {sectores[0].value if sectores else '—'}")
    texto = " ".join(m.value for m in at.markdown)
    if "https://europe.alsea.net/talento" not in texto:
        fallos.append("el correo no lleva la web de empleo de Alsea")
    if not any("Bar Manolo" in w.value for w in at.warning):
        fallos.append("no avisa de que «Bar Manolo» no está en la guía")
    at.session_state["inf_w_situaciones"] = ["Más de 45 años"]
    at.run()
    recursos = [m for m in at.multiselect if m.key == "inf_w_recursos"]
    if not recursos or not recursos[0].options:
        fallos.append("al marcar «Más de 45 años» no salen entidades que elegir")
    return informe(nombre, fallos, 4)


def p_pantalla_formacion_y_extranjeria():
    """Formación abre en el sector del currículo; extranjería, con sus entidades plegadas."""
    nombre = "Formación y extranjería: lo de la guía, plegado"
    if not _hay_streamlit(nombre):
        return True
    from herramientas.cv import motor as cv_motor
    fallos = []
    at = abre("herramientas/formacion/vista.py")
    pildoras = [b for b in at.get("button_group") if b.key == "fmc_w_guia"]
    if at.exception or not pildoras or pildoras[0].value != "Buscadores de cursos gratuitos":
        fallos.append("sin currículo, formación no abre en los buscadores de cursos")
    cv = cv_motor.nuevo()
    cv["experiencias"].append(cv_motor.experiencia("84321042", "CONDUCTORES DE CAMIÓN, EN GENERAL"))
    at = abre("herramientas/formacion/vista.py", {"cv_datos": cv})
    sector = [x for x in at.selectbox if x.key == "fmc_w_guia_sector"]
    if at.exception or not sector or sector[0].value != "35-mensajeria":
        fallos.append("con un camionero en el CV, formación no abre en mensajería y camión")
    elif "Permisos y formación" not in " ".join(m.value for m in at.markdown):
        fallos.append("no se pintan los permisos y la formación del sector")
    at = abre("herramientas/extranjeria/vista.py")
    texto = " ".join(m.value for m in at.markdown)
    if at.exception or "Pueblos Unidos" not in texto:
        fallos.append("extranjería no lleva las entidades de la guía")
    return informe(nombre, fallos, 3)


PRUEBAS = [
    p_la_copia_esta_entera,
    p_la_tabla_apunta_a_lo_que_existe,
    p_los_casos,
    p_cobertura_y_lo_general,
    p_un_curriculo_con_varias,
    p_los_cee_van_aparte,
    p_las_direcciones_se_leen_como_en_la_guia,
    p_la_lista_para_imprimir,
    p_el_buscador_de_la_guia,
    p_las_sugeridas_por_ia,
    p_para_empezar_a_trabajar,
    p_pantalla_codificador,
    p_pantalla_codificador_con_ia,
    p_pantalla_curriculo,
    p_pantalla_informes,
    p_pantalla_formacion_y_extranjeria,
    p_pantalla_donde_enviar,
    p_pantalla_empresas_con_ia,
    p_pantalla_portada,
]


def main():
    print(f"«Dónde enviar el CV»: {guia.EDICION['fichas']} fichas en {len(guia.CAPITULOS)} capítulos · "
          f"{guia.EDICION['edicion']} · {len(guia._TABLA)} prefijos en la tabla\n")
    for prueba in PRUEBAS:
        try:
            prueba()
        except Exception as e:  # noqa: BLE001
            nombre = prueba.__name__.removeprefix("p_").replace("_", " ")
            RESUMEN.append((nombre, False))
            print(f"[MAL] {nombre:52} {type(e).__name__}: {e}")
    bien = sum(1 for _, ok in RESUMEN if ok)
    print(f"\n{bien} de {len(RESUMEN)} pruebas pasan")
    return 0 if bien == len(RESUMEN) else 1


if __name__ == "__main__":
    sys.exit(main())
