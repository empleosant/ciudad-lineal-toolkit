"""
Estilo compartido de la caja de herramientas.

Colores, tipografía y la maquetación de la cabecera y de los bloques que se
repiten (rótulos de sección, notas, preguntas). Cada página llama a
`aplica()` al principio. Lo específico de una herramienta va en su vista.
"""

import streamlit as st

ROJO = "#D1122E"
ROJO_OSCURO = "#A50E24"
NEGRO = "#0A0A0A"

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700&family=JetBrains+Mono:wght@600;700&display=swap');

:root{
  --negro:#0A0A0A;
  --rojo:#D1122E;
  --rojo-oscuro:#A50E24;
  --texto:#1A1A1A;
  --suave:#555555;
  --tenue:#8E8E93;
  --linea:#E2E8F0;
  --gris:#F1F5F9;
}

.stApp{ background:#FAFAFA; }
html,body,[class*="css"],.stMarkdown{
  font-family:'Libre Franklin',system-ui,sans-serif; color:var(--texto);
}
.block-container{ padding:0 1rem .4rem !important; max-width:1200px; }
/* Sin cabecera de Streamlit ni barra lateral: el menú de herramientas va
   dentro de la banda negra de cada página y no depende de ningún control
   interno. Antes se intentó dejar la cabecera transparente y su barra de
   herramientas seguía capturando los clics de lo que quedaba debajo. */
#MainMenu, footer, header[data-testid="stHeader"]{ display:none !important; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"]{ display:none !important; }

/* ---------- Portada: tarjetas de herramientas ---------- */
.st-key-tarjetas div[data-testid="stVerticalBlockBorderWrapper"]{
  background:#fff; border-left:4px solid var(--rojo) !important; border-radius:4px;
}
.tarjeta-titulo{ font-size:1.05rem; font-weight:700; letter-spacing:-.01em; margin:0 0 .25rem; }
.tarjeta-texto{ font-size:.86rem; color:var(--suave); line-height:1.4; margin:0 0 .6rem; }

/* ---------- Menú de herramientas, dentro de la banda negra ---------- */
.st-key-menu{ margin-bottom:.25rem; }
.st-key-menu div[data-testid="stHorizontalBlock"]{ gap:.35rem !important; flex-wrap:wrap; }
.st-key-menu div[data-testid="stColumn"]{ flex:0 0 auto !important; width:auto !important; min-width:0 !important; }
.st-key-menu a[data-testid="stPageLink-NavLink"]{
  color:#C9C9C9 !important; font-size:.78rem; font-weight:600; letter-spacing:.02em;
  padding:.18rem .55rem !important; border-radius:3px; border:1px solid transparent;
  background:transparent !important; text-decoration:none !important;
}
.st-key-menu a[data-testid="stPageLink-NavLink"] *{ color:inherit !important; }
.st-key-menu a[data-testid="stPageLink-NavLink"]:hover{ color:#fff !important; border-color:#555; }
.st-key-menu a[data-testid="stPageLink-NavLink"][disabled]{
  color:#fff !important; background:var(--rojo) !important; border-color:var(--rojo); opacity:1 !important;
}
[data-testid="stHeaderActionElements"]{ display:none !important; }
h1 > a, h2 > a, h3 > a, .stMarkdown a.anchor-link{ display:none !important; }
div[data-testid="InputInstructions"]{ display:none !important; }

/* Eliminación de márgenes fantasma entre iframe y contenedor */
div[data-testid="stCustomComponentV1"] {
  margin-bottom: 0px !important;
  padding-bottom: 0px !important;
}
div[data-testid="stCustomComponentV1"] iframe {
  margin-bottom: 0px !important;
  padding-bottom: 0px !important;
  display: block !important;
}

/* ---------- Cabecera fluida ---------- */
.st-key-cabecera{
  background:var(--negro);
  padding:clamp(0.55rem, 1vh, 0.8rem) clamp(1rem, 2vw, 1.8rem);
  margin-bottom:clamp(0.25rem, 0.6vh, 0.45rem);
  box-shadow:0 2px 10px rgba(0,0,0,0.06);
}
.rotulo{
  color:#8A8A8A; font-size:clamp(0.58rem, 0.65vw, 0.66rem); font-weight:600;
  letter-spacing:.16em; text-transform:uppercase; margin:0 0 .1rem;
}
.rotulo span{ color:var(--rojo); font-weight:700; }

/* Título */
.st-key-marca button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  padding:0 !important; justify-content:flex-start !important; margin-bottom:.35rem;
}
.st-key-marca button p{
  color:#fff !important; font-size:clamp(1.2rem, 1.45vw, 1.45rem) !important;
  font-weight:700 !important; letter-spacing:-.025em; margin:0 !important;
  text-align:left !important; border-bottom:2px solid transparent; transition:border-color .15s ease;
}
.st-key-marca button:hover p{ border-bottom-color:var(--rojo); }

/* Campo de búsqueda */
.st-key-cabecera div[data-testid="stTextInput"] div[data-baseweb="base-input"],
.st-key-cabecera div[data-testid="stTextInput"] input,
.st-key-cabecera div[data-testid="stTextInput"] input:focus,
.st-key-cabecera div[data-testid="stTextInput"] input:hover{
  background:transparent !important; border:none !important;
  box-shadow:none !important; outline:none !important;
}
.st-key-cabecera div[data-testid="stTextInput"] div[data-baseweb="input"]{
  background:#fff !important; border:1px solid #fff !important;
  border-radius:4px 0 0 4px !important; box-shadow:none !important;
}
.st-key-cabecera div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within{
  border-color:var(--rojo) !important; box-shadow:0 0 0 2px var(--rojo) !important;
}
div[data-testid="stTextInput"] input{
  padding:clamp(0.42rem, 0.8vh, 0.6rem) clamp(0.7rem, 1vw, 1rem) !important;
  font-size:clamp(0.88rem, 0.95vw, 0.98rem) !important;
  color:var(--texto) !important; font-family:'Libre Franklin',sans-serif !important;
}

/* Botones */
.st-key-buscar button{
  background:var(--rojo) !important; color:#fff !important; border:none !important;
  border-radius:0 4px 4px 0 !important; font-weight:700 !important;
  font-size:clamp(0.84rem, 0.9vw, 0.92rem) !important;
  padding:clamp(0.42rem, 0.8vh, 0.6rem) 1rem !important;
  min-height:clamp(36px, 3.8vh, 44px) !important; letter-spacing:.02em;
  transition:background .15s ease;
}
.st-key-buscar button:hover{ background:var(--rojo-oscuro) !important; }
.st-key-buscar button p{ color:#fff !important; font-weight:700 !important; }

.st-key-ajustes button{
  width:clamp(36px, 3.8vh, 44px) !important; height:clamp(36px, 3.8vh, 44px) !important;
  min-height:clamp(36px, 3.8vh, 44px) !important;
  border-radius:4px !important; padding:0 !important;
  background:#1A1A1A !important; border:1px solid #333 !important; color:#fff !important;
  display:flex !important; align-items:center !important; justify-content:center !important;
  transition:all .18s ease;
}
.st-key-ajustes button:hover{
  background:var(--rojo) !important; border-color:var(--rojo) !important; color:#fff !important;
}

/* Consulta activa */
.consulta-box{
  border-bottom:2px solid var(--negro); padding-bottom:.2rem;
  margin:0 0 clamp(0.25rem, 0.5vh, 0.4rem);
}
.consulta-texto{
  font-size:clamp(0.95rem, 1.05vw, 1.08rem); font-weight:700;
  letter-spacing:-.015em; color:var(--texto);
}
.seccion{
  font-size:.65rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:var(--suave); margin:1rem 0 .5rem;
}

/* Pregunta interactiva centrada (arriba de las tarjetas) */
.st-key-pregunta{
  background:#fff; border:1px solid var(--linea); border-top:3px solid var(--rojo);
  border-radius:4px; padding:clamp(0.45rem, 0.8vh, 0.65rem) clamp(0.8rem, 1.2vw, 1.2rem);
  margin:0.2rem 0 0.45rem !important; box-shadow:0 1px 4px rgba(0,0,0,0.03);
  text-align:center !important;
}
.pregunta-titulo{
  font-size:.62rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:var(--rojo); margin-bottom:.12rem; text-align:center !important;
}
.pregunta-texto{
  font-size:clamp(0.9rem, 0.98vw, 0.98rem); line-height:1.32; font-weight:600;
  color:var(--texto); margin-bottom:.42rem; text-align:center !important;
}
.st-key-pregunta div[data-testid="stHorizontalBlock"]{
  justify-content:center !important; align-items:center !important;
}
.st-key-pregunta .stButton button{
  background:#fff; border:1px solid var(--negro); font-weight:600; border-radius:4px;
  padding:.32rem .75rem; min-height:34px; font-size:.84rem; transition:all .15s ease;
  white-space:normal !important; height:auto !important;
}
.st-key-pregunta .stButton button:hover{
  background:var(--negro); color:#fff; border-color:var(--negro);
}

.nota{ font-size:.74rem; color:var(--suave); margin:.15rem 0; }
.separa{ height:1px; background:var(--linea); margin:clamp(0.25rem, 0.5vh, 0.4rem) 0; }

/* Botón de reinicio */
.st-key-reinicio,
.st-key-reinicio > div,
.st-key-reinicio [data-testid="stTooltipHoverTarget"],
.st-key-reinicio [data-testid="stElementToolbar"]{
  display:flex !important; justify-content:center !important; width:100% !important;
}
.st-key-reinicio button{
  width:clamp(40px, 4.4vh, 48px) !important; height:clamp(40px, 4.4vh, 48px) !important;
  min-height:clamp(40px, 4.4vh, 48px) !important;
  border-radius:50% !important; padding:0 !important;
  border:2px solid var(--negro) !important; background:#fff !important;
  display:flex !important; align-items:center !important; justify-content:center !important;
  transition:all .2s cubic-bezier(.2,.85,.3,1); box-shadow:0 2px 6px rgba(0,0,0,0.05);
}
.st-key-reinicio button p{
  font-size:clamp(1.25rem, 1.5vw, 1.5rem) !important; line-height:1 !important;
  margin:0 !important; color:var(--negro) !important;
}
.st-key-reinicio button:hover{
  background:var(--rojo) !important; border-color:var(--rojo) !important;
  transform:rotate(-90deg) scale(1.05);
}
.st-key-reinicio button:hover p{ color:#fff !important; }
.pie-nueva{
  text-align:center; font-size:.74rem; font-weight:600; color:var(--suave); margin:.2rem 0 0;
}

div[data-testid="stExpander"]{ border:none; background:transparent; margin-top:.1rem; }
div[data-testid="stExpander"] summary{ font-size:.8rem; color:var(--suave); padding:.1rem 0; }
</style>
"""


def aplica():
    st.markdown(CSS, unsafe_allow_html=True)


def menu(actual):
    """El menú de herramientas. Va dentro de la banda negra de cada página.

    `actual` es el id (ver `comun/registro.py`) de la herramienta que lo
    pinta: sale marcada en rojo y no es un enlace.
    """
    from comun.registro import PAGINAS

    try:
        caja = st.container(key="menu")
    except TypeError:
        caja = st.container()
    with caja:
        cols = st.columns(len(PAGINAS), gap="small")
        for col, h in zip(cols, PAGINAS):
            col.page_link(h["ruta"], label=h["titulo"], icon=h["icono"],
                          disabled=(h["id"] == actual))
