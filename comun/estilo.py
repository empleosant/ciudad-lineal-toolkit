"""
Estilo compartido de la caja de herramientas.

Colores, tipografía y la maquetación de la cabecera y de los bloques que se
repiten (rótulos de sección, notas, preguntas). Cada página llama a
`aplica()` al principio. Lo específico de una herramienta va en su vista.
"""

import html

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
.block-container{ padding:0 1rem 3.5rem !important; max-width:1100px; }
/* Sin cabecera de Streamlit ni barra lateral: el menú de herramientas va
   dentro de la banda negra de cada página y no depende de ningún control
   interno. Antes se intentó dejar la cabecera transparente y su barra de
   herramientas seguía capturando los clics de lo que quedaba debajo. */
#MainMenu, footer, header[data-testid="stHeader"]{ display:none !important; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"]{ display:none !important; }

/* ---------- Piezas comunes a todas las herramientas ---------- */
/* Tarjeta con filo rojo arriba: vías de entrada, herramientas de la portada, pasos */
.via{ background:#fff; border:1px solid var(--linea); border-top:3px solid var(--rojo);
      border-radius:6px; padding:.7rem .85rem .5rem; height:100%; }
.via .t{ font-weight:700; font-size:.92rem; margin:0 0 .15rem; }
.via .d{ font-size:.8rem; color:var(--suave); line-height:1.4; margin:0 0 .4rem; }
.via.grande{ padding:1rem 1.1rem .7rem; min-height:8.6rem; }
.via.grande .t{ font-size:1.05rem; letter-spacing:-.01em; }
.via.grande .d{ font-size:.86rem; }
/* Tarjeta de estado: una cifra grande con rótulo y nota */
.estado-doc{ background:#fff; border:1px solid var(--linea); border-radius:6px; padding:.75rem .9rem; }
.estado-doc .g{ font-size:1.6rem; font-weight:700; letter-spacing:-.02em; line-height:1; }
.estado-doc .l{ font-size:.72rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--suave); }
.estado-doc .n{ font-size:.82rem; color:var(--suave); margin-top:.35rem; line-height:1.4; }
.chip{ display:inline-block; font-size:.66rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
       padding:.1rem .45rem; border-radius:3px; background:var(--gris); color:var(--suave); margin-left:.4rem; }
.chip.rojo{ background:var(--rojo); color:#fff; }
.chip.naranja{ background:#FFF7ED; color:#C2410C; border:1px solid #FFEDD5; }
.ok{ color:#1B6B3A; } .aviso{ color:#C2410C; }
/* Fichas plegables con filo rojo a la izquierda (experiencias, resultados) */
/* Ojo con los dos data-testid del contenedor con borde: hasta cierta versión
   era stVerticalBlockBorderWrapper y ahora el borde lo lleva el stVerticalBlock
   de dentro de un stLayoutWrapper. Se ponen los dos porque requirements.txt
   pide streamlit>=1.40 y Cloud instala la que le da la gana; con uno solo, el
   filo rojo de las tarjetas de resultado desaparecía sin que nadie lo notara. */
.st-key-fichas div[data-testid="stExpander"],
[class*="st-key-curso_"] div[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-curso_"] > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]{
  background:#fff; border:1px solid var(--linea) !important; border-left:4px solid var(--rojo) !important;
  border-radius:6px; margin:.35rem 0;
}
.st-key-fichas div[data-testid="stExpander"] summary{ padding:.5rem .8rem; font-size:.92rem; color:var(--texto); }
.st-key-fichas div[data-testid="stExpander"] summary p{ font-weight:600; }
/* Enlaces de página dentro de tarjetas: como un botón discreto */
.via-enlace a[data-testid="stPageLink-NavLink"]{ font-weight:600; }

/* ---------- Menú de herramientas, dentro de la banda negra ---------- */
.st-key-menu{ margin:0; }
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

/* Un bloque que solo lleva un <style> no pinta nada, pero sigue siendo un
   hijo de la columna flexible y se lleva su separacion: un hueco de 16 px
   por cada hoja de estilo que se inyecta. */
div[data-testid="stElementContainer"]:has(style:only-child){ display:none !important; }

/* Eliminación de márgenes fantasma entre iframe y contenedor.
   El data-testid cambió de nombre al actualizar Streamlit (stCustomComponentV1
   -> stIFrame) y la regla se había quedado sin efecto. Se dejan los dos. */
div[data-testid="stCustomComponentV1"],
div[data-testid="stElementContainer"]:has(> iframe) {
  margin-bottom: 0px !important;
  padding-bottom: 0px !important;
}
div[data-testid="stCustomComponentV1"] iframe,
iframe.stIFrame {
  margin-bottom: 0px !important;
  padding-bottom: 0px !important;
  display: block !important;
}

/* Botones "+ CV" bajo las tarjetas del codificador. A partir de 640 px
   Streamlit apila las columnas, y el botón quedaba ENCIMA de la ocupación a
   la que pertenece, pegado al nombre de la anterior. Invertida la fila, cada
   nombre va justo antes de su botón. */
@media (max-width:640px){
  .st-key-carrito div[data-testid="stHorizontalBlock"]{
    flex-direction: column-reverse;
    flex-wrap: nowrap;
  }
}

/* ---------- Banda de cabecera ---------- */
.st-key-cabecera{
  background:linear-gradient(135deg, #0A0A0A 0%, #1F1F22 100%);
  padding:clamp(0.7rem, 1.2vh, 1rem) clamp(1.1rem, 2vw, 1.9rem) clamp(0.9rem, 1.4vh, 1.2rem);
  margin-bottom:clamp(0.4rem, 0.8vh, 0.7rem);
  border-radius:0 0 12px 12px; border-bottom:3px solid var(--rojo);
  box-shadow:0 8px 22px rgba(0,0,0,0.14);
}
.st-key-cabecera div[data-testid="stHorizontalBlock"]{ align-items:center; }
.st-key-titulo{
  border-left:4px solid var(--rojo); padding-left:.85rem;
  margin:clamp(0.6rem, 1vh, 0.9rem) 0 clamp(0.3rem, 0.6vh, 0.5rem);
}
.st-key-titulo div[data-testid="stMarkdown"], .st-key-titulo div[data-testid="stElementContainer"]{ margin:0 !important; }
.titulo-banda{
  color:#fff; font-size:clamp(1.35rem, 1.7vw, 1.7rem); font-weight:700;
  letter-spacing:-.025em; line-height:1.15; margin:0;
}
.subtitulo-banda{
  color:#C4C4C4; font-size:clamp(0.82rem, 0.9vw, 0.92rem); margin:.2rem 0 0; line-height:1.35;
}

/* Título */
.st-key-marca button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  padding:0 !important; justify-content:flex-start !important; margin:0 !important;
  min-height:0 !important; height:auto !important;
}
.st-key-marca button p{
  color:#fff !important; font-size:clamp(1.35rem, 1.7vw, 1.7rem) !important;
  font-weight:700 !important; letter-spacing:-.025em; margin:0 !important; line-height:1.15 !important;
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
/* Streamlit pone el "nowrap" en el parrafo de dentro, no en el boton: sin
   esta linea el rotulo se corta con puntos suspensivos en pantallas
   estrechas aunque el boton sí sepa crecer. */
.st-key-pregunta .stButton button p,
.st-key-ejemplos .stButton button p{ white-space:normal !important; }
.st-key-ejemplos .stButton button{
  white-space:normal !important; height:auto !important; min-height:38px;
  line-height:1.25;
}
.st-key-pregunta .stButton button:hover{
  background:var(--negro); color:#fff; border-color:var(--negro);
}

.nota{ font-size:.74rem; color:var(--suave); margin:.15rem 0; }
.separa{ height:1px; background:var(--linea); margin:clamp(0.25rem, 0.5vh, 0.4rem) 0; }

/* Chip de proveedor: qué modelo ha contestado y cuánto ha tardado */
.chip-proveedor{
  display:inline-flex; align-items:center; gap:4px;
  font-size:.62rem; font-weight:600; color:var(--tenue);
  background:var(--gris); border:1px solid var(--linea);
  border-radius:12px; padding:.15rem .55rem; margin:.2rem auto;
  letter-spacing:.03em;
}
.chip-proveedor-punto{
  width:5px; height:5px; border-radius:50%; background:#16A34A;
  display:inline-block;
}

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

/* ---------- Indicador de pasos ---------- */
/* Mismo aspecto que la barra del generador de CV, pero aquí NO son botones:
   la página no está paginada, se recorre entera, así que esto informa de por
   dónde vas y no navega. Un botón que no lleva a ningún sitio miente. */
.pasos{ display:grid; grid-template-columns:repeat(3,1fr); gap:.4rem; margin:.2rem 0 .3rem; }
.pasos .paso{
  border:1px solid var(--linea); border-radius:6px; background:#fff;
  padding:.5rem .7rem; display:flex; flex-direction:column; gap:.1rem; min-width:0;
}
.pasos .paso .t{ font-size:.84rem; font-weight:600; color:var(--suave); }
.pasos .paso .d{ font-size:.76rem; color:var(--tenue); }
.pasos .paso.hecho{ border-color:#BFE3CB; background:#F1FAF3; }
.pasos .paso.hecho .t{ color:#1B6B3A; }
.pasos .paso.hecho .d{ color:#3F8459; }
.pasos .paso.activo{ background:var(--negro); border-color:var(--negro); }
.pasos .paso.activo .t{ color:#fff; }
.pasos .paso.activo .d{ color:#B9B9BE; }
@media (max-width:640px){ .pasos{ grid-template-columns:1fr; } }

/* ---------- Zonas de arrastre ---------- */
/* El cargador de Streamlit YA acepta arrastrar y soltar; lo que no hace es
   parecerlo, y además habla en inglés ("Upload", "200MB per file") dentro de
   una herramienta de una oficina pública española.
   Todo lo de aquí es ADITIVO a propósito. Si una versión nueva de Streamlit
   cambia su DOM, estos selectores dejan de casar y vuelve a salir el cargador
   de serie: feo, pero entero y funcionando. Nada de esto puede tumbar la
   página. Verificado contra Streamlit 1.63. */
[class*="st-key-soltar_"] div[data-testid="stFileUploader"] label{ display:none; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]{
  flex-direction:column; align-items:center; justify-content:center; gap:.3rem;
  min-height:8.2rem; padding:1.1rem .9rem;
  border:2px dashed #C7CFDA !important; border-radius:6px; background:#F8FAFC !important;
  transition:border-color .15s ease, background .15s ease;
}
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]:hover{
  border-color:var(--rojo) !important; background:#fff !important;
}
/* El rótulo grande, en ::before para no depender de ningún nodo de Streamlit */
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]::before{
  order:1; font-size:.92rem; font-weight:700; color:var(--texto); text-align:center; line-height:1.3;
}
.st-key-soltar_cursos section[data-testid="stFileUploaderDropzone"]::before{
  content:"Arrastra aquí el Excel del catálogo";
}
.st-key-soltar_perfil section[data-testid="stFileUploaderDropzone"]::before{
  content:"Arrastra aquí el perfil";
}
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] > span:has(button){ order:2; }
/* La línea de Streamlit ("200MB per file • XLSX, XLS, CSV") sobra entera:
   está en inglés y el tamaño lo lleva un <span> de dentro, así que pelearlo
   desde fuera no vale. Se quita y se pone la nuestra en ::after. */
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] >
  div[data-testid="stFileUploaderDropzoneInstructions"]{ display:none !important; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]::after{
  order:3; font-size:.74rem; color:var(--tenue); text-align:center;
}
.st-key-soltar_cursos section[data-testid="stFileUploaderDropzone"]::after{
  content:"Un Excel o un CSV, hasta 200 MB";
}
.st-key-soltar_perfil section[data-testid="stFileUploaderDropzone"]::after{
  content:"Un .md o un .txt, hasta 200 MB";
}
/* El "Drag and drop a file here" que Streamlit asoma en pantallas anchas
   sobra: ya lo dice el rótulo de arriba, y encima en español. */
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] >
  *:not(input):not([data-testid]):not(:has(button)){ display:none !important; }
/* "Upload" -> "Buscar en el equipo", sin tocar el icono, que es una ligadura */
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] button
  div[data-testid="stMarkdownContainer"] p{ font-size:0 !important; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] button
  div[data-testid="stMarkdownContainer"] p::after{
  content:"Buscar en el equipo"; font-size:.82rem; font-weight:600;
}
/* Ya hay archivo: la caja se encoge y se pone verde */
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChip"]){
  flex-direction:row; min-height:0; padding:.5rem .6rem;
  border:1px solid #BFE3CB !important; background:#F1FAF3 !important;
}
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChip"])::before,
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChip"])::after{
  display:none;
}

/* ---------- Etiquetas de una tarjeta de curso ---------- */
.etiquetas{ display:flex; flex-wrap:wrap; gap:.25rem; margin:.45rem 0 0; }
.et{ font-size:.73rem; border-radius:4px; padding:.12rem .45rem; background:var(--gris); color:var(--suave); }
.et.pronto{ background:#F1FAF3; color:#1B6B3A; }
.et.tarde{ background:#FFF7ED; color:#C2410C; }

/* El filo toma el color de la prioridad: se capta sin leer la etiqueta */
[class*="st-key-curso_"][class*="_media"] div[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-curso_"][class*="_media"] > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]{
  border-left-color:#C2410C !important;
}
[class*="st-key-curso_"][class*="_baja"] div[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-curso_"][class*="_baja"] > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]{
  border-left-color:#C7CFDA !important;
}

/* ---------- Franja de revisión de datos personales ---------- */
.revision{
  display:flex; gap:.5rem; align-items:flex-start; border-radius:6px;
  padding:.5rem .7rem; font-size:.8rem; line-height:1.45; margin:.4rem 0 0;
}
.revision.limpio{ background:#F1FAF3; color:#1B6B3A; border:1px solid #BFE3CB; }
.revision.alerta{ background:#FFF7ED; color:#C2410C; border:1px solid #FFEDD5; }
.revision b{ font-weight:700; }
.revision .flojo{ opacity:.85; font-weight:400; }

/* ---------- Tabla compacta (vista previa del catálogo, ediciones) ---------- */
.tablilla{ width:100%; border-collapse:collapse; font-size:.78rem; }
.tablilla th{
  text-align:left; font-size:.62rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
  color:var(--tenue); padding:0 .5rem .3rem 0; border-bottom:1px solid var(--linea); white-space:nowrap;
}
.tablilla td{ padding:.3rem .5rem .3rem 0; border-bottom:1px solid var(--gris); vertical-align:top; }
.envuelve-tabla{ overflow-x:auto; }

div[data-testid="stExpander"]{ border:none; background:transparent; margin-top:.1rem; }
div[data-testid="stExpander"] summary{ font-size:.8rem; color:var(--suave); padding:.1rem 0; }
</style>
"""


def aplica():
    st.markdown(CSS, unsafe_allow_html=True)


def caja(clave):
    """`st.container(key=...)`, o uno sin clave en versiones que no lo admiten.

    Sin la clave el contenedor sigue funcionando; lo que se pierde es el CSS
    que cuelga de `.st-key-<clave>`, así que la página se ve de serie pero no
    se rompe. Se repetía en todas las vistas y vive mejor aquí.
    """
    try:
        return st.container(key=clave)
    except TypeError:
        return st.container()


def pasos(items):
    """Indicador de pasos: por dónde va la cosa y qué falta.

    `items` es [(rótulo, detalle, estado)] con estado "hecho", "activo" o "".
    No son botones y no navegan: esta página se recorre entera de arriba abajo
    (la del generador de CV sí está paginada, y allí sí lo son).
    """
    trozos = []
    for i, (rotulo, detalle, estado) in enumerate(items, 1):
        marca = "✓" if estado == "hecho" else str(i)
        trozos.append(
            f'<div class="paso {estado}">'
            f'<span class="t">{marca} · {html.escape(str(rotulo))}</span>'
            f'<span class="d">{html.escape(str(detalle))}</span></div>'
        )
    st.markdown(f'<div class="pasos">{"".join(trozos)}</div>', unsafe_allow_html=True)


def banda(actual, titulo, subtitulo="", al_pulsar_titulo=None):
    """La banda negra de cabecera, igual en todas las páginas.

    Arriba, el menú de herramientas; debajo, el título y una frase de qué
    hace la herramienta. Se devuelve el contenedor para que cada página
    añada dentro lo suyo (el codificador, su buscador). `al_pulsar_titulo`,
    si se da, convierte el título en botón (el codificador lo usa para
    volver al principio).
    """
    try:
        caja = st.container(key="cabecera")
    except TypeError:
        caja = st.container()
    with caja:
        menu(actual)
        try:
            fila = st.container(key="titulo")
        except TypeError:
            fila = st.container()
        with fila:
            if al_pulsar_titulo:
                st.button(titulo, key="marca", on_click=al_pulsar_titulo)
            else:
                st.markdown(f'<div class="titulo-banda">{titulo}</div>', unsafe_allow_html=True)
            if subtitulo:
                st.markdown(f'<div class="subtitulo-banda">{subtitulo}</div>', unsafe_allow_html=True)
    return caja


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
