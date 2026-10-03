"""
Dónde enviar el CV: la Guía de empleo de Madrid con buscador propio.

Hasta ahora la guía solo salía plegada dentro de otras herramientas. Aquí es
la pantalla entera: se empieza por los sectores de lo que hay en la mesa (la
ocupación del codificador y las experiencias del currículo), se puede buscar
por nombre o actividad o abrir cualquier otro sector, y cada empresa lleva
una casilla. Lo marcado es «su lista»: se imprime sola y sale también en la
hoja aparte del paso 4 del generador de CV.

Todo eso va sin IA. Debajo, «Más empresas con IA» es un botón aparte para
los oficios que la guía no cubre: Gemini busca en Google empresas de Madrid y
alrededores y salen como fichas iguales, etiquetadas «sin comprobar»
(`modelo.py` pregunta; `motor.py` decide qué enlaces se enseñan). Lo
encontrado se guarda en el Gist por puesto, para no gastar cupo dos veces.

La lógica vive en `comun/guia.py` (las fichas, el PDF), en `motor.py` (el
buscador y las fichas de la IA) y en `comun/mesa.py` (lo marcado); aquí solo
se pinta.
"""

import hashlib
import re

import streamlit as st

from datetime import date

from comun import estilo, gist, guia, ia, mesa
from herramientas.cv import estado as cv_estado
from herramientas.cv import motor as cv_motor
from herramientas.guia import modelo, motor

TOPE = 60      # fichas con casilla por pantalla: más allá, el buscador o el PDF
ARCHIVO_IA = "empresas_ia.json"   # en el Gist: lo que la IA ya ha buscado, por puesto

estilo.aplica()
st.markdown("""
<style>
/* Cada ficha, una tarjeta como las del codificador: la casilla es el nombre */
[class*="st-key-gf_"]{
  background:#fff; border:1px solid var(--linea); border-left:4px solid #CBD5E1; border-radius:4px;
  padding:.4rem .7rem .5rem; box-shadow:0 1px 3px rgba(0,0,0,.03);
}
[class*="st-key-gf_"]:has(input:checked){ border-left-color:var(--rojo); background:#FFFBFB; }
[class*="st-key-gf_"]{ gap:0 !important; }
[class*="st-key-gf_"] div[data-testid="stVerticalBlock"]{ gap:0; }
[class*="st-key-gf_"] div[data-testid="stCheckbox"]{ min-height:0; }
[class*="st-key-gf_"] div[data-testid="stMarkdownContainer"]{ margin-bottom:0 !important; }
[class*="st-key-gf_"] label p{ font-size:.88rem; line-height:1.25; }
.st-key-ia_regenerar{ flex-wrap:nowrap !important; align-items:center; }
.st-key-ia_regenerar > div:first-child{ flex:1 1 auto !important; min-width:0; }
.st-key-ia_regenerar > div:last-child{ flex:0 0 auto !important; width:auto !important; }
.st-key-ia_regenerar div[data-testid="stMarkdownContainer"]{ margin-bottom:0 !important; }
.gu-cuerpo{ padding-left:1.75rem; }
.gu-ia{ padding-left:1.75rem; margin-top:.2rem; } .gu-ia .chip{ margin-left:0; }
/* Su lista: una línea por empresa con su aspa */
.st-key-su_lista{ background:#fff; border:1px solid var(--linea); border-radius:var(--radio); padding:.35rem .7rem; }
.st-key-su_lista{ gap:0 !important; }
.st-key-su_lista div[data-testid="stMarkdownContainer"]{ margin-bottom:0 !important; }
.st-key-su_lista > div:first-child [class*="st-key-quita_fila_"]{ border-top:0; }
[class*="st-key-quita_fila_"]{ flex-wrap:nowrap !important; align-items:center; border-top:1px solid var(--gris); }
[class*="st-key-quita_fila_"] > div:first-child{ flex:1 1 auto !important; min-width:0; }
[class*="st-key-quita_fila_"] > div:last-child{ flex:0 0 auto !important; width:auto !important; }
[class*="st-key-quita_fila_"] button{ min-height:0 !important; height:26px; padding:0 .5rem !important; border:0 !important;
  background:transparent !important; color:var(--suave) !important; }
[class*="st-key-quita_fila_"] button:hover{ color:var(--rojo) !important; }
.su-nombre{ font-size:.84rem; font-weight:600; line-height:1.3; }
</style>
""", unsafe_allow_html=True)

def nueva_busqueda():
    """Empezar otra vez: fuera lo escrito, el sector abierto y el filtro.

    Su lista y lo que la IA ya buscó no se tocan: lo primero es de la persona
    y lo segundo está guardado para no gastar cupo dos veces."""
    st.session_state["guia_consulta"] = ""
    st.session_state["guia_otro"] = None
    st.session_state["guia_empezar"] = False


de_la_mesa = mesa.secciones(cee=True)
ocupacion = mesa.ocupacion()
puesto = cv_motor.a_oracion(ocupacion[1]) if ocupacion else ""

with estilo.banda(
    "guia", "Dónde enviar el CV",
    "Las empresas de la Guía de empleo de Madrid, por sector. Lo que marques es su lista: "
    "se imprime aparte y sale en el paso 4 del generador de CV.",
):
    c_busca, c_otro, c_nueva = st.columns([6, 4, 2.4], gap="small")
    consulta = c_busca.text_input(
        "Buscar en la guía", key="guia_consulta", label_visibility="collapsed",
        placeholder="Busca una empresa o una actividad: «hoteles», «limpieza de oficinas»",
    )
    otro = c_otro.selectbox(
        "Otro sector de la guía", guia.sectores(), index=None, key="guia_otro",
        format_func=lambda c: guia.CAPITULOS[c]["corto"], placeholder="O abre otro sector de la guía",
        label_visibility="collapsed",
    )
    c_nueva.button("↺ Nueva búsqueda", key="guia_nueva", on_click=nueva_busqueda, use_container_width=True,
                   help="Borra lo escrito, el sector abierto y el filtro. Su lista se queda.")
    empezar = st.toggle(
        "Para empezar a trabajar: sin experiencia ni titulación", key="guia_empezar",
        help="Solo los sectores donde lo corriente es entrar sin experiencia previa ni título. "
             "Lo que se busque, también con IA, se limita a eso.",
    )
    if empezar:
        opciones = {s["capitulo"]: s for s in guia.para_empezar()}
        rotulo_pildoras, clave_pildoras = "Sectores para empezar", "guia_sector_empezar"
    else:
        opciones = {s["capitulo"]: s for s in de_la_mesa}
        rotulo_pildoras = "Sectores de la mesa"
        clave_pildoras = "guia_sector_mesa_" + hashlib.md5("|".join(opciones).encode()).hexdigest()[:8]
    elegido = None
    if opciones:
        elegido = estilo.pildoras(
            rotulo_pildoras, list(opciones), default=next(iter(opciones)),
            format_func=lambda c: f"{opciones[c]['corto']} · {opciones[c]['n']}", key=clave_pildoras,
            help=None if empezar else
            "Los sectores de la ocupación del codificador y de las experiencias del currículo.",
        )

# Qué se enseña: lo buscado manda; luego el sector abierto a mano; luego el de
# las píldoras (los de la mesa o, con el filtro, los de empezar a trabajar).
consulta = (consulta or "").strip()
if consulta:
    hallazgos = motor.busca(consulta, tope=TOPE)
    if empezar:
        hallazgos = [(a, [f for f in fs if guia.es_para_empezar(f)]) for a, fs in hallazgos]
        hallazgos = [(re.sub(r"^\d+ fichas", f"{len(fs)} fichas", a), fs) for a, fs in hallazgos if fs]
    seccion = {
        "capitulo": "busqueda", "titulo": f"«{consulta}»", "corto": consulta, "entero": False,
        "apartados": hallazgos, "n": sum(len(fs) for _, fs in hallazgos), "general": False,
    } if hallazgos else None
    rotulo = f"Buscando «{consulta}»" + (" entre lo que no pide experiencia" if empezar else "")
elif otro:
    seccion = guia.seccion(otro)
    if empezar and seccion:
        suyos = [(a, [f for f in fs if guia.es_para_empezar(f)]) for a, fs in seccion["apartados"]]
        suyos = [(a, fs) for a, fs in suyos if fs]
        seccion = {**seccion, "apartados": suyos, "n": sum(len(fs) for _, fs in suyos)} if suyos else None
    rotulo = guia.CAPITULOS[otro]["titulo"]
elif elegido:
    seccion = opciones[elegido]
    rotulo = seccion["titulo"]
else:
    seccion, rotulo = None, ""
if empezar and seccion:
    seccion = {**seccion, "nota_empezar": guia.NOTA_EMPEZAR}

izq, der = st.columns([5, 3], gap="medium")


def pinta_fichas(fichas, desde=0):
    """Las fichas de dos en dos, cada una con su casilla. Devuelve cuántas van."""
    for i in range(0, len(fichas), 2):
        cols = st.columns(2, gap="small")
        for j, (col, f) in enumerate(zip(cols, fichas[i:i + 2])):
            with col, estilo.caja(f"gf_{desde + i + j}"):
                mesa.casilla(f, "guia", detalle=False)
                st.markdown(
                    guia.ficha_html(f, nombre=False, caja=False)
                    + ('<div class="gu-ia"><span class="chip naranja">IA · sin comprobar</span></div>'
                       if f.get("ia") else ""),
                    unsafe_allow_html=True)
    return desde + len(fichas)


def guardadas_ia(clave):
    """(fichas, fecha) de lo que la IA ya buscó para ese puesto, o None.

    Primero lo de esta sesión; si no, lo del Gist, que es de toda la oficina:
    la segunda persona que busca el mismo oficio no gasta cupo.
    """
    memoria = st.session_state.setdefault("guia_ia", {})
    if clave not in memoria and gist.activo():
        fichas, fecha = motor.desempaqueta(gist.lee(ARCHIVO_IA).get(clave, ""))
        if fecha:
            memoria[clave] = (fichas, fecha)
    return memoria.get(clave)


def busca_con_ia(puesto_, clave, sector_, ya, para_empezar=False):
    """Pregunta a Gemini con búsqueda en Google y guarda lo que encuentre.

    `clave` es con qué nombre se guarda: el puesto y, si la búsqueda es solo
    de puestos de entrada, la marca que la distingue de la corriente."""
    try:
        with st.spinner("Buscando en Google empresas de Madrid y alrededores…"):
            texto, fuentes, apoyos = modelo.busca(puesto_, sector_, ya, para_empezar=para_empezar)
    except Exception as e:  # noqa: BLE001
        st.session_state["guia_ia_aviso"] = (
            "Ahora no se puede buscar con IA (lo normal es que se haya acabado el cupo gratuito "
            f"de búsquedas de hoy). {type(e).__name__}: {str(e)[:160]}")
        return
    fichas, descartadas = motor.interpreta(texto, fuentes, apoyos)
    hoy = date.today().strftime("%d/%m/%Y")
    st.session_state.setdefault("guia_ia", {})[clave] = (fichas, hoy)
    if descartadas:
        st.session_state["guia_ia_aviso"] = (
            f"Se {'ha' if descartadas == 1 else 'han'} descartado {descartadas} "
            f"{'empresa que no aparecía' if descartadas == 1 else 'empresas que no aparecían'} "
            "en ninguna página de la búsqueda.")
    if gist.activo() and fichas:
        try:
            todo = dict(gist.lee(ARCHIVO_IA))
            todo[clave] = motor.empaqueta(fichas, hoy)
            gist.escribe(ARCHIVO_IA, todo)
        except Exception:  # noqa: BLE001
            pass        # sin Gist se pierde al cerrar la sesión, nada más


with izq:
    pintadas = 0
    if seccion is None:
        if consulta:
            st.info("Ninguna ficha de la guía nombra eso ni hay un sector para ese oficio"
                    + (" entre lo que no pide experiencia" if empezar else "") + ". "
                    "Prueba con otra palabra, abre un sector o búscalo con IA aquí debajo.")
        else:
            st.info("Busca una empresa o abre un sector. Si antes buscas la ocupación en el "
                    "codificador, aquí salen ya los sectores que le tocan.")
    else:
        st.markdown(f'<div class="seccion">{guia.esc(rotulo)} · {seccion["n"]} fichas</div>',
                    unsafe_allow_html=True)
        if seccion.get("nota"):
            st.caption(f"**Centros especiales de empleo.** {seccion['nota']}")
        if seccion.get("nota_empezar"):
            st.caption(f"**Para empezar a trabajar.** {seccion['nota_empezar']}")
        for apartado, fichas in seccion["apartados"]:
            if pintadas >= TOPE:
                break
            st.markdown(f'<div class="gu-apartado">{guia.esc(apartado)}</div>', unsafe_allow_html=True)
            pintadas = pinta_fichas(fichas[:TOPE - pintadas], pintadas)
        if seccion["n"] > pintadas:
            st.caption(f"Salen las {pintadas} primeras de {seccion['n']}: afina con el buscador, "
                       "o descarga el sector entero en PDF.")
        st.caption(f"De la guía «{guia.EDICION['titulo_empresas']}» ({guia.EDICION['edicion'].lower()}), "
                   f"comprobada en {guia.EDICION['verificado']}. Que una empresa salga aquí no "
                   "garantiza que tenga vacantes.")

    # Más empresas con IA: para el oficio que se ha escrito o, si no se ha
    # escrito nada, para la ocupación que hay en la mesa. Con el filtro de
    # empezar a trabajar y sin nada escrito, para el sector que se está viendo.
    if consulta:
        puesto_ia = consulta
    elif empezar:
        puesto_ia = f"puestos de entrada en {seccion['corto'].lower()}" if seccion else ""
    else:
        puesto_ia = puesto
    if puesto_ia:
        clave_ia = motor.clave_consulta(puesto_ia + (" · para empezar" if empezar else ""))
        st.markdown(f'<div class="seccion">Más empresas con IA · {guia.esc(puesto_ia)} · '
                    + ("sin experiencia · " if empezar else "") + 'Madrid y alrededores</div>',
                    unsafe_allow_html=True)
        aviso = st.session_state.pop("guia_ia_aviso", "")
        if aviso:
            st.warning(aviso)
        hechas = guardadas_ia(clave_ia)
        ya = [f["nombre"] for _, fs in (seccion["apartados"] if seccion else []) for f in fs]
        argumentos = (puesto_ia, clave_ia, "" if consulta else (seccion or {}).get("corto", ""), ya, empezar)
        hay_clave = ia.tiene_clave("gemini")
        # En línea y no en un `on_click`: dentro de un callback no se ve la espera.
        if hechas is None:
            st.caption("La IA busca en Google empresas del oficio con centro en Madrid capital o su "
                       "área metropolitana. No están comprobadas como las de la guía: salen "
                       "etiquetadas y, en el papel, en un apartado propio.")
            if st.button("Buscar más empresas con IA", key="guia_ia_buscar", icon=":material/travel_explore:",
                         type="primary", disabled=not hay_clave,
                         help=None if hay_clave else "Hace falta la clave de Gemini."):
                busca_con_ia(*argumentos)
                st.rerun()
        else:
            fichas_ia, fecha_ia = hechas
            # El botón de regenerar, arriba y a la vista: antes iba al final,
            # debajo de las fichas, y no se encontraba.
            with estilo.fila("ia_regenerar", vertical_alignment="center"):
                st.markdown(f'<div class="nota">Buscadas el {fecha_ia} con Google. <b>Sin comprobar</b>: '
                            'confirma en la web de cada empresa antes de enviar.</div>',
                            unsafe_allow_html=True, **estilo._ancho("stretch"))
                regenerar = st.button("Regenerar con IA", key="guia_ia_buscar", icon=":material/refresh:",
                                      disabled=not hay_clave,
                                      help="Vuelve a buscar en Google y sustituye estas empresas."
                                      if hay_clave else "Hace falta la clave de Gemini.")
            if regenerar:
                busca_con_ia(*argumentos)
                st.rerun()
            if fichas_ia:
                pinta_fichas(fichas_ia, 1000)
            else:
                st.caption("La búsqueda no encontró empresas seguras para este oficio en Madrid.")

with der:
    marcadas = mesa.empresas()
    st.markdown(f'<div class="seccion">Su lista · {len(marcadas)} '
                f'empresa{"s" if len(marcadas) != 1 else ""}</div>', unsafe_allow_html=True)
    if not marcadas:
        st.caption("Marca las empresas que le interesen y aquí se va haciendo su lista.")
    else:
        with estilo.caja("su_lista"):
            for n, f in enumerate(marcadas):
                with estilo.fila(f"quita_fila_{n}", vertical_alignment="center"):
                    st.markdown(f'<div class="su-nombre">{guia.esc(f["nombre"])}</div>',
                                unsafe_allow_html=True, **estilo._ancho("stretch"))
                    st.button("✕", key=f"quita_{n}", help="Quitar de la lista",
                              on_click=mesa.marca, args=(f, False))
    archivo = re.sub(r"[^0-9A-Za-z]+", "_", puesto).strip("_") or "lista"
    en_minuscula = puesto[:1].lower() + puesto[1:]
    st.download_button(
        "Imprimir su lista (PDF)", icon=":material/print:", on_click="ignore", type="primary",
        data=lambda: guia.pdf([guia.lista(marcadas)], "Dónde enviar tu currículum",
                              puesto, puesto=en_minuscula),
        file_name=f"Donde_enviar_CV_{archivo}.pdf", mime="application/pdf",
        use_container_width=True, disabled=not marcadas,
        help="Solo las empresas marcadas, en blanco y negro y a dos columnas, con el guion para llamar.",
    )
    if seccion is not None and not consulta:
        st.download_button(
            "El sector entero (PDF)", icon=":material/print:", on_click="ignore",
            data=lambda: guia.pdf([seccion], "Dónde enviar tu currículum",
                                  " · ".join(x for x in [puesto, seccion["corto"]] if x),
                                  puesto=en_minuscula),
            file_name=f"Donde_enviar_CV_{re.sub(r'[^0-9A-Za-z]+', '_', seccion['corto']).strip('_')}.pdf",
            mime="application/pdf", use_container_width=True,
        )
    if marcadas:
        st.page_link(cv_estado.PAGINA, label="Seguir en el generador de CV →")
        st.caption("En el paso 4 su lista ya está marcada para la hoja aparte.")
