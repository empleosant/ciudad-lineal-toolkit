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
    html = " ".join(m.value for m in at.markdown)
    if "gu-ficha" not in html or "Alsea" not in html:
        fallos.append("no se pintan las fichas de hostelería")
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
    return informe(nombre, fallos, 3)


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
    p_pantalla_codificador,
    p_pantalla_codificador_con_ia,
    p_pantalla_curriculo,
    p_pantalla_informes,
    p_pantalla_formacion_y_extranjeria,
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
