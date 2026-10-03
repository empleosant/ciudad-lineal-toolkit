"""
Dónde enviar el CV: la Guía de empleo de Madrid con buscador propio.

Hasta ahora la guía solo salía plegada dentro de otras herramientas. Aquí es
la pantalla entera: se empieza por los sectores de lo que hay en la mesa (la
ocupación del codificador y las experiencias del currículo), se puede buscar
por nombre o actividad o abrir cualquier otro sector, y cada empresa lleva
una casilla. Lo marcado es «su lista»: se imprime sola y sale también en la
hoja aparte del paso 4 del generador de CV.

Sin IA. La lógica vive en `comun/guia.py` (las fichas, el buscador, el PDF)
y en `comun/mesa.py` (lo marcado); aquí solo se pinta.
"""

import hashlib
import re

import streamlit as st

from comun import estilo, guia, mesa
from herramientas.cv import estado as cv_estado
from herramientas.cv import motor as cv_motor

TOPE = 60      # fichas con casilla por pantalla: más allá, el buscador o el PDF

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
.gu-cuerpo{ padding-left:1.75rem; }
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

de_la_mesa = mesa.secciones(cee=True)
ocupacion = mesa.ocupacion()
puesto = cv_motor.a_oracion(ocupacion[1]) if ocupacion else ""

with estilo.banda(
    "guia", "Dónde enviar el CV",
    "Las empresas de la Guía de empleo de Madrid, por sector. Lo que marques es su lista: "
    "se imprime aparte y sale en el paso 4 del generador de CV.",
):
    c_busca, c_otro = st.columns([3, 2], gap="small")
    consulta = c_busca.text_input(
        "Buscar en la guía", key="guia_consulta", label_visibility="collapsed",
        placeholder="Busca una empresa o una actividad: «hoteles», «limpieza de oficinas»",
    )
    otro = c_otro.selectbox(
        "Otro sector de la guía", guia.sectores(), index=None, key="guia_otro",
        format_func=lambda c: guia.CAPITULOS[c]["corto"], placeholder="O abre otro sector de la guía",
        label_visibility="collapsed",
    )
    por_capitulo = {s["capitulo"]: s for s in de_la_mesa}
    elegido = None
    if por_capitulo:
        elegido = estilo.pildoras(
            "Sectores de la mesa", list(por_capitulo), default=next(iter(por_capitulo)),
            format_func=lambda c: f"{por_capitulo[c]['corto']} · {por_capitulo[c]['n']}",
            key="guia_sector_mesa_" + hashlib.md5("|".join(por_capitulo).encode()).hexdigest()[:8],
            help="Los sectores de la ocupación del codificador y de las experiencias del currículo.",
        )

# Qué se enseña: lo buscado manda; luego el sector abierto a mano; luego el de la mesa.
consulta = (consulta or "").strip()
if consulta:
    hallazgos = guia.busca(consulta, tope=TOPE)
    seccion = guia.lista(hallazgos, f"«{consulta}»")
    if seccion:
        seccion["apartados"] = [(f"{len(hallazgos)} fichas que lo nombran", hallazgos)]
    rotulo = f"Buscando «{consulta}»"
elif otro:
    seccion = guia.seccion(otro)
    rotulo = guia.CAPITULOS[otro]["titulo"]
elif elegido:
    seccion = por_capitulo[elegido]
    rotulo = seccion["titulo"]
else:
    seccion, rotulo = None, ""

izq, der = st.columns([5, 3], gap="medium")

with izq:
    if seccion is None:
        if consulta:
            st.info("Ninguna ficha de los sectores nombra eso. Prueba con otra palabra o abre un sector.")
        else:
            st.info("Busca una empresa o abre un sector. Si antes buscas la ocupación en el "
                    "codificador, aquí salen ya los sectores que le tocan.")
    else:
        st.markdown(f'<div class="seccion">{guia.esc(rotulo)} · {seccion["n"]} fichas</div>',
                    unsafe_allow_html=True)
        if seccion.get("nota"):
            st.caption(f"**Centros especiales de empleo.** {seccion['nota']}")
        pintadas = 0
        for apartado, fichas in seccion["apartados"]:
            if pintadas >= TOPE:
                break
            fichas = fichas[:TOPE - pintadas]
            st.markdown(f'<div class="gu-apartado">{guia.esc(apartado)}</div>', unsafe_allow_html=True)
            for i in range(0, len(fichas), 2):
                cols = st.columns(2, gap="small")
                for col, f in zip(cols, fichas[i:i + 2]):
                    with col, estilo.caja(f"gf_{pintadas}"):
                        mesa.casilla(f, "guia", detalle=False)
                        st.markdown(guia.ficha_html(f, nombre=False, caja=False), unsafe_allow_html=True)
                    pintadas += 1
        if seccion["n"] > pintadas:
            st.caption(f"Salen las {pintadas} primeras de {seccion['n']}: afina con el buscador, "
                       "o descarga el sector entero en PDF.")
        st.caption(f"De la guía «{guia.EDICION['titulo_empresas']}» ({guia.EDICION['edicion'].lower()}), "
                   f"comprobada en {guia.EDICION['verificado']}. Que una empresa salga aquí no "
                   "garantiza que tenga vacantes.")

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
