"""
Estilo compartido de la caja de herramientas.

Colores, tipografía y las piezas que se repiten: la barra negra con el menú,
el título de cada página, los rótulos de sección, los pasos, las notas y los
chips. Cada página llama a `aplica()` al principio y a `banda()` para la
cabecera. Lo específico de una herramienta va en su vista.

Lo que puede hacer el tema de Streamlit (`.streamlit/config.toml`) no se
hace aquí: el color primario, el borde y el fondo de los campos y el radio
de las esquinas salen de allí, y así no dependen de los selectores internos
de Streamlit, que cambian de versión.
"""

import html

import streamlit as st

ROJO = "#D1122E"
ROJO_OSCURO = "#A50E24"
NEGRO = "#0A0A0A"

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700;800&family=JetBrains+Mono:wght@600;700&display=swap');

:root{
  --negro:#0A0A0A;
  --rojo:#D1122E;
  --rojo-oscuro:#A50E24;
  --texto:#1A1A1A;
  --suave:#555555;
  --tenue:#8E8E93;
  --linea:#E2E5EA;
  --gris:#F1F2F4;
  --radio:6px;
}

.stApp{ background:#FAFAFA; }
/* Con el modo de dibujo por defecto, Chromium descoloca letras de la fuente
   de Streamlit a tamaños pequeños: «Co dificado r SISPE», «CAT EGORÍA». */
html, body, .stApp{ text-rendering:geometricPrecision; }
html,body,[class*="css"],.stMarkdown{
  font-family:'Libre Franklin',system-ui,sans-serif; color:var(--texto);
}
.block-container{ padding:0 1rem 3.5rem !important; max-width:1100px; }
/* Sin cabecera de Streamlit ni barra lateral: el menú de herramientas va
   en la barra negra de cada página y no depende de ningún control interno. */
#MainMenu, footer, header[data-testid="stHeader"]{ display:none !important; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"]{ display:none !important; }
[data-testid="stHeaderActionElements"]{ display:none !important; }
h1 > a, h2 > a, h3 > a, .stMarkdown a.anchor-link{ display:none !important; }
div[data-testid="InputInstructions"]{ display:none !important; }

/* Un bloque que solo lleva un <style> no pinta nada, pero sigue siendo un
   hijo de la columna flexible y se lleva su separacion: un hueco de 16 px
   por cada hoja de estilo que se inyecta. */
div[data-testid="stElementContainer"]:has(style:only-child){ display:none !important; }

/* Eliminación de márgenes fantasma entre iframe y contenedor. El data-testid
   cambió de nombre al actualizar Streamlit (stCustomComponentV1 -> stIFrame)
   y la regla se había quedado sin efecto. Se dejan los dos. */
div[data-testid="stCustomComponentV1"],
div[data-testid="stElementContainer"]:has(> iframe){
  margin-bottom:0 !important; padding-bottom:0 !important;
}
div[data-testid="stCustomComponentV1"] iframe, iframe.stIFrame{
  margin-bottom:0 !important; padding-bottom:0 !important; display:block !important;
}

/* ---------- La barra negra ---------- */
/* Va de lado a lado de la ventana aunque el contenido tenga un ancho máximo:
   el margen negativo la saca del contenedor centrado y el relleno devuelve el
   contenido a su sitio. El desbordamiento horizontal que eso puede dejar (el
   ancho de la barra de desplazamiento) se corta en la sección principal. */
section.stMain{ overflow-x:hidden; }
/* El ancho va fijado a la ventana: Streamlit le da al contenedor el ancho de
   la columna, y con solo los márgenes negativos la barra se corría a la
   izquierda sin crecer (no llegaba al borde derecho y cortaba «Informes»). */
.st-key-cabecera{
  background:var(--negro); border-bottom:3px solid var(--rojo);
  width:100vw !important; max-width:100vw !important;
  margin:0 0 1rem calc(50% - 50vw) !important; padding:.45rem calc(50vw - 50%) .5rem;
}
.st-key-cabecera div[data-testid="stVerticalBlock"]{ gap:.35rem; }
.st-key-menu{
  flex-wrap:nowrap !important; overflow-x:auto; gap:.3rem !important;
  scrollbar-width:none; -ms-overflow-style:none; align-items:center;
}
.st-key-menu::-webkit-scrollbar{ display:none; }
.st-key-menu > div{ flex:0 0 auto !important; min-width:0 !important; width:auto !important; }
/* La marca no se va con el desplazamiento: se queda pegada a la izquierda */
.st-key-menu > div:first-child{ position:sticky; left:0; z-index:1; background:var(--negro); padding-right:.6rem; }
.marca{ color:#fff; font-weight:800; font-size:.95rem; letter-spacing:-.01em; white-space:nowrap;
        display:inline-flex; align-items:center; gap:.45rem; line-height:1; }
.marca i{ width:14px; height:14px; border-radius:50%; background:var(--rojo); display:inline-block;
          box-shadow:inset 0 0 0 4px var(--rojo), inset 0 0 0 7px #fff; }
.marca small{ color:#9A9A9F; font-weight:500; font-size:.72rem; margin-left:.2rem; }
.st-key-menu a[data-testid="stPageLink-NavLink"]{
  color:#C9C9C9 !important; font-size:.78rem; font-weight:600; letter-spacing:.01em;
  padding:0 .75rem !important; border-radius:999px; border:1px solid #3A3A3E;
  background:transparent !important; text-decoration:none !important; white-space:nowrap;
  min-height:0 !important; height:30px; display:inline-flex; align-items:center; gap:0;
}
.st-key-menu a[data-testid="stPageLink-NavLink"] p{ font-size:.78rem !important; line-height:1 !important; }
.st-key-menu a[data-testid="stPageLink-NavLink"] *{ color:inherit !important; }
.st-key-menu a[data-testid="stPageLink-NavLink"]:hover{ color:#fff !important; border-color:#8E8E93; }
.st-key-menu a[data-testid="stPageLink-NavLink"][disabled]{
  color:#fff !important; background:var(--rojo) !important; border-color:var(--rojo); opacity:1 !important;
}
/* Los iconos del menú sobran en la barra: el nombre basta y ocupa menos */
.st-key-menu a[data-testid="stPageLink-NavLink"] > span:has(> span[data-testid="stIconMaterial"]){ display:none; }
@media (max-width:640px){
  .marca small{ display:none; }
  /* En el móvil la herramienta activa va la primera de la tira, para que se
     vea sin deslizar; la marca sigue delante de todo. */
  .st-key-menu > div:first-child{ order:-2; }
  .st-key-menu > div:has(a[data-testid="stPageLink-NavLink"][disabled]){ order:-1; }
}

/* ---------- El título de la página ---------- */
.st-key-titulo{ flex-wrap:nowrap !important; align-items:flex-start !important; margin-bottom:.6rem; overflow:visible !important; }
.st-key-titulo > div{ height:auto !important; }
.st-key-titulo > div:first-child{ flex:1 1 auto !important; min-width:0; }
.st-key-titulo .stMarkdown, .st-key-titulo div[data-testid="stElementContainer"]{ height:auto !important; }
.st-key-titulo > div:last-child:not(:first-child){ flex:0 0 auto !important; width:auto !important; }
.titulo-pagina{
  font-size:clamp(1.45rem, 2.2vw, 1.85rem); font-weight:800; letter-spacing:-.025em;
  line-height:1.12; margin:.2rem 0 0; color:var(--texto);
}
.subtitulo-pagina{ color:var(--suave); font-size:.92rem; margin:.3rem 0 0; line-height:1.4; max-width:70ch; }
/* Los botones de la fila del título (ajustes, ayuda, expediente): cuadrados y discretos */
.st-key-titulo button{
  width:36px !important; height:36px !important; min-height:36px !important;
  padding:0 !important; border-radius:var(--radio) !important;
  background:#fff !important; border:1px solid var(--linea) !important; color:var(--suave) !important;
  display:flex !important; align-items:center !important; justify-content:center !important;
}
.st-key-titulo button:hover{ border-color:var(--negro) !important; color:var(--texto) !important; }
.st-key-titulo button svg, .st-key-titulo button span[data-testid="stIconMaterial"]{ font-size:1.2rem; }
.st-key-titulo button [data-testid="stIconMaterial"] + *{ display:none; }

/* ---------- Piezas comunes a todas las herramientas ---------- */
.seccion{
  font-size:.66rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:var(--tenue); margin:1.1rem 0 .5rem;
}
.nota{ font-size:.76rem; color:var(--suave); margin:.15rem 0; }
/* Fichas de la guía de empleo (comun/guia.py: ficha_html y apartado_html) */
.gu-apartado{ font-size:.66rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--suave); margin:.7rem 0 .25rem; }
.gu-rejilla{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:6px; }
@media (max-width:760px){ .gu-rejilla{ grid-template-columns:1fr; } }
/* Cada ficha, tarjeta como las del codificador: filo gris a la izquierda */
.gu-ficha{
  background:#fff; border:1px solid var(--linea); border-left:4px solid #CBD5E1; border-radius:4px;
  padding:.45rem .75rem .5rem; box-shadow:0 1px 3px rgba(0,0,0,.03); min-width:0;
}
.gu-nom{ font-weight:700; font-size:.88rem; color:var(--texto); line-height:1.25; }
.gu-que{ font-size:.78rem; color:var(--suave); line-height:1.3; }
.gu-como{ font-size:.78rem; color:var(--texto); line-height:1.3; margin-top:.1rem; }
.gu-datos{ font-size:.78rem; line-height:1.35; margin-top:.1rem; overflow-wrap:anywhere; }
.gu-datos a{ color:var(--rojo); font-weight:600; text-decoration:none; }
.gu-datos a:hover{ text-decoration:underline; }
.separa{ height:1px; background:var(--linea); margin:.5rem 0; }
.ok{ color:#1B6B3A; } .aviso{ color:#C2410C; }
/* Tarjeta plana: vías de entrada, pasos, explicaciones */
.via{ background:#fff; border:1px solid var(--linea); border-radius:var(--radio); padding:.75rem .9rem .55rem; height:100%; }
.via .t{ font-weight:700; font-size:.92rem; margin:0 0 .15rem; }
.via .d{ font-size:.8rem; color:var(--suave); line-height:1.4; margin:0 0 .4rem; }
/* Tarjeta de estado: una cifra grande con rótulo y nota */
.estado-doc{ background:#fff; border:1px solid var(--linea); border-radius:var(--radio); padding:.75rem .9rem; }
.estado-doc .g{ font-size:1.6rem; font-weight:700; letter-spacing:-.02em; line-height:1; }
.estado-doc .l{ font-size:.68rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--tenue); }
.estado-doc .n{ font-size:.82rem; color:var(--suave); margin-top:.35rem; line-height:1.4; }
.chip{ display:inline-block; font-size:.64rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
       padding:.12rem .45rem; border-radius:3px; background:var(--gris); color:var(--suave); margin-left:.4rem; }
.chip.rojo{ background:var(--rojo); color:#fff; }
.chip.negro{ background:var(--negro); color:#fff; }
.chip.naranja{ background:#FFF7ED; color:#C2410C; border:1px solid #FFEDD5; }
/* Fichas plegables (experiencias del CV) y tarjetas de curso: filo gris, sin colores */
.st-key-fichas div[data-testid="stExpander"]{
  background:#fff; border:1px solid var(--linea) !important; border-radius:var(--radio); margin:.35rem 0;
}
.st-key-fichas div[data-testid="stExpander"] summary{ padding:.5rem .8rem; font-size:.92rem; color:var(--texto); }
.st-key-fichas div[data-testid="stExpander"] summary p{ font-weight:600; }
/* El filo de las tarjetas de curso toma el color de la prioridad: se capta
   sin leer la etiqueta. Ojo con los dos data-testid del contenedor con
   borde: hasta cierta versión era stVerticalBlockBorderWrapper y ahora el
   borde lo lleva el stVerticalBlock de dentro de un stLayoutWrapper. */
[class*="st-key-curso_"] div[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-curso_"] > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]{
  border-left:4px solid var(--rojo) !important; border-radius:var(--radio);
}
[class*="st-key-curso_"][class*="_media"] div[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-curso_"][class*="_media"] > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]{
  border-left-color:#C2410C !important;
}
[class*="st-key-curso_"][class*="_baja"] div[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-curso_"][class*="_baja"] > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]{
  border-left-color:#C7CFDA !important;
}
/* Enlaces de página dentro de tarjetas: como un botón discreto */
.via-enlace a[data-testid="stPageLink-NavLink"]{ font-weight:600; }

/* ---------- Pestañas como control segmentado ---------- */
/* Caben enteras en el móvil y se ven como lo que son: tres partes de la
   misma pantalla. Las de Streamlit iban subrayadas y se cortaban. */
/* Streamlit 1.64 pinta las pestañas con role="tablist" y stTab; las
   versiones anteriores, con data-baseweb. Se cubren las dos. */
div[data-testid="stTabs"] div[role="tablist"],
div[data-testid="stTabs"] div[data-baseweb="tab-list"]{
  display:flex; background:var(--gris); border-radius:8px; padding:3px; gap:2px; overflow:visible;
  border-bottom:0 !important;
}
div[data-testid="stTabs"] div[role="tablist"]::after{ display:none; }
div[data-testid="stTabs"] [data-testid="stTab"],
div[data-testid="stTabs"] button[data-baseweb="tab"]{
  flex:1 1 0; display:flex; justify-content:center; align-items:center; text-align:center;
  border-radius:var(--radio); padding:.42rem .5rem; min-width:0; margin:0;
  background:transparent; border-bottom:0 !important; transition:background .15s ease; cursor:pointer;
}
div[data-testid="stTabs"] [data-testid="stTab"] p,
div[data-testid="stTabs"] button[data-baseweb="tab"] p{
  font-size:.84rem; font-weight:600; color:var(--suave) !important; white-space:normal; line-height:1.2;
}
div[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"],
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{
  background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.08);
}
div[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] p,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] p{ color:var(--texto) !important; }
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
div[data-testid="stTabs"] div[data-baseweb="tab-border"],
div[data-testid="stTabs"] div[role="tablist"] > div:not([role="tab"]),
div[data-testid="stTabs"] [data-testid="stTab"] .react-aria-SelectionIndicator{ display:none; }

/* ---------- Indicador de pasos ---------- */
/* Un recuadro por paso, como antes del rediseño: negro el paso en curso,
   verde lo hecho, blanco lo que falta. Se ve de un vistazo y desde lejos; la
   línea con circulitos que lo sustituyó se perdía. Aquí NO son botones:
   informa de por dónde vas y no navega (los del generador de CV sí lo son, y
   se pintan igual desde su vista). */
.pasos{ display:grid; grid-template-columns:repeat(auto-fit, minmax(0, 1fr)); grid-auto-flow:column;
        gap:.4rem; margin:.2rem 0 .6rem; }
.pasos .paso{
  border:1px solid var(--linea); border-radius:6px; background:#fff;
  padding:.5rem .7rem; display:flex; flex-direction:column; gap:.1rem; min-width:0;
}
.pasos .paso .t{ font-size:.84rem; font-weight:600; color:var(--suave); line-height:1.2; }
.pasos .paso .d{ font-size:.76rem; color:var(--tenue); line-height:1.25; }
.pasos .paso.hecho{ border-color:#BFE3CB; background:#F1FAF3; }
.pasos .paso.hecho .t{ color:#1B6B3A; } .pasos .paso.hecho .d{ color:#3F8459; }
.pasos .paso.activo{ background:var(--negro); border-color:var(--negro); }
.pasos .paso.activo .t{ color:#fff; } .pasos .paso.activo .d{ color:#B9B9BE; }
@media (max-width:640px){ .pasos{ grid-auto-flow:row; grid-template-columns:1fr; } }

/* ---------- Chip de proveedor: qué modelo ha contestado y cuánto ha tardado ---------- */
.chip-proveedor{
  display:inline-flex; align-items:center; gap:5px;
  font-size:.66rem; font-weight:600; color:var(--tenue);
  background:#fff; border:1px solid var(--linea);
  border-radius:12px; padding:.15rem .6rem; margin:.2rem auto; letter-spacing:.02em;
}
.chip-proveedor-punto{ width:6px; height:6px; border-radius:50%; background:#16A34A; display:inline-block; }

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
  border:1.5px dashed #C7CFDA !important; border-radius:var(--radio); background:#FBFBFC !important;
  transition:border-color .15s ease, background .15s ease;
}
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]:hover{
  border-color:var(--rojo) !important; background:#fff !important;
}
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]::before{
  order:1; font-size:.92rem; font-weight:700; color:var(--texto); text-align:center; line-height:1.3;
}
.st-key-soltar_cursos section[data-testid="stFileUploaderDropzone"]::before{ content:"Arrastra aquí el Excel del catálogo"; }
.st-key-soltar_perfil section[data-testid="stFileUploaderDropzone"]::before{ content:"Arrastra aquí el perfil"; }
.st-key-soltar_cv section[data-testid="stFileUploaderDropzone"]::before{ content:"Arrastra aquí el currículo"; }
.st-key-soltar_expediente section[data-testid="stFileUploaderDropzone"]::before{ content:"Arrastra aquí el expediente"; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] > span:has(button){ order:2; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] >
  div[data-testid="stFileUploaderDropzoneInstructions"]{ display:none !important; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"]::after{
  order:3; font-size:.74rem; color:var(--tenue); text-align:center;
}
.st-key-soltar_cursos section[data-testid="stFileUploaderDropzone"]::after{ content:"Un Excel o un CSV, hasta 200 MB"; }
.st-key-soltar_perfil section[data-testid="stFileUploaderDropzone"]::after{ content:"Un .md o un .txt, hasta 200 MB"; }
.st-key-soltar_cv section[data-testid="stFileUploaderDropzone"]::after{ content:"Un .md o un .txt, sin datos personales"; }
.st-key-soltar_expediente section[data-testid="stFileUploaderDropzone"]::after{ content:"El .json que guardaste otro día"; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] >
  *:not(input):not([data-testid]):not(:has(button)){ display:none !important; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] button
  div[data-testid="stMarkdownContainer"] p{ font-size:0 !important; }
[class*="st-key-soltar_"] section[data-testid="stFileUploaderDropzone"] button
  div[data-testid="stMarkdownContainer"] p::after{
  content:"Buscar en el equipo"; font-size:.82rem; font-weight:600;
}
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

/* ---------- Franja de revisión de datos personales ---------- */
.revision{
  display:flex; gap:.5rem; align-items:flex-start; border-radius:var(--radio);
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

/* Los desplegables de la fila del título (ayuda, expediente) necesitan sitio */
div[data-testid="stPopoverBody"]{ min-width:min(440px, 92vw); }

/* Desplegables: sin caja alrededor, solo el rótulo */
div[data-testid="stExpander"]{ margin-top:.1rem; }
div[data-testid="stExpander"] summary{ font-size:.84rem; color:var(--suave); }
</style>
"""


def aplica():
    st.markdown(CSS, unsafe_allow_html=True)


def caja(clave, **k):
    """`st.container(key=...)`, o uno sin clave en versiones que no lo admiten.

    Sin la clave el contenedor sigue funcionando; lo que se pierde es el CSS
    que cuelga de `.st-key-<clave>`, así que la página se ve de serie pero no
    se rompe. Los argumentos extra (`horizontal`, `border`…) se pasan tal
    cual; si la versión instalada no los conoce, se prueba solo con la clave y
    luego sin nada.
    """
    for kw in (dict(k, key=clave), {"key": clave}, {}):
        try:
            return st.container(**kw)
        except TypeError:
            continue
    return st.container()


def fila(clave, **k):
    """Un contenedor en horizontal que no se apila en el móvil.

    Las columnas de Streamlit se ponen una debajo de otra por debajo de 640
    px; esto no. Sirve para el menú, la fila del título y la del buscador.
    En versiones sin `horizontal` cae en un contenedor normal (en vertical).
    """
    k.setdefault("horizontal", True)
    k.setdefault("wrap", False)
    return caja(clave, **k)


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


def banda(actual, titulo, subtitulo="", acciones=None):
    """La barra negra con el menú y, debajo, el título de la página.

    `actual` es el id de la herramienta (ver `comun/registro.py`), que sale
    marcada en rojo en el menú. `acciones`, si se da, es una función que pinta
    los botones de la fila del título (ajustes, ayuda…), a la derecha.

    Se devuelve un contenedor colocado justo debajo del título, para que cada
    página añada ahí lo suyo (el codificador, su buscador).
    """
    with caja("cabecera"):
        menu(actual)
    with fila("titulo", vertical_alignment="top"):
        st.markdown(
            f'<div class="titulo-pagina">{titulo}</div>'
            + (f'<div class="subtitulo-pagina">{subtitulo}</div>' if subtitulo else ""),
            unsafe_allow_html=True, **_ancho("stretch"),
        )
        if acciones:
            with fila("acciones_titulo"):
                acciones()
    return caja("bajo_titulo")


def pildoras(*args, **kwargs):
    """`st.pills` que pasa a otra línea cuando no cabe.

    Desde que Streamlit decide solo, las píldoras puestas directamente en una
    columna se quedan en una fila que se desliza de lado, y en el móvil se
    cortaban (los carnés del CV). En versiones sin `wrap`, `st.pills` tal cual.
    """
    import inspect
    try:
        if "wrap" in inspect.signature(st.pills).parameters:
            kwargs.setdefault("wrap", True)
    except (TypeError, ValueError):
        pass
    return st.pills(*args, **kwargs)


def _ancho(valor):
    """`width=` solo en las versiones que lo admiten."""
    import inspect
    try:
        return {"width": valor} if "width" in inspect.signature(st.markdown).parameters else {}
    except (TypeError, ValueError):
        return {}


def nombre_modelo(nombre):
    """«gemini-3.5-flash-lite» -> «Gemini 3.5 Flash Lite»."""
    partes = (nombre or "").replace("-preview", "").replace("-latest", "").split("-")
    rotulo = " ".join(p.capitalize() for p in partes if not p.isdigit() and len(p) > 1)
    return rotulo or (nombre or "").split("-")[0].capitalize()


def chip_ia(modelo, segundos=0.0):
    """Quién ha contestado y cuánto se ha esperado, centrado bajo el resultado.

    Sin esto no hay forma de saber, mirando la pantalla, si ha respondido el
    primero de la cadena de relevo o el de repuesto, ni si la espera ha sido de
    uno o de diez segundos.
    """
    if not modelo:
        return
    reloj = f" · {segundos:.1f}s" if segundos and segundos > 0 else ""
    chip(f"{nombre_modelo(modelo)}{reloj}")


def chip(texto, color="#16A34A"):
    """Un chip centrado: punto de color y etiqueta."""
    st.markdown(
        f'<div style="text-align:center"><span class="chip-proveedor">'
        f'<span class="chip-proveedor-punto" style="background:{color}"></span>'
        f"{html.escape(str(texto))}</span></div>",
        unsafe_allow_html=True,
    )


def marco(cuerpo, alto, ancho=None):
    """Un marco aislado con HTML y JavaScript propios.

    Lo necesitan los botones de copiar (los códigos del buscador, el correo de
    cierre): son lo único de la aplicación que no se puede hacer con
    componentes de Streamlit. `st.components.v1.html` quedó obsoleto en junio
    de 2026 y avisa por consola de que va a desaparecer; `st.iframe` es su
    relevo, pero llegó después de la versión mínima que pide
    `requirements.txt`, así que si no está se usa el de siempre.
    """
    if hasattr(st, "iframe"):
        return st.iframe(cuerpo, height=alto, **({"width": ancho} if ancho else {}))
    import streamlit.components.v1 as componentes
    return componentes.html(cuerpo, height=alto, **({"width": ancho} if ancho else {}))


def menu(actual):
    """El menú de herramientas: la marca y un chip por página, en una línea.

    En el móvil la línea se desliza con el dedo en vez de romperse; la marca
    se queda fija a la izquierda. `actual` es el id (ver `comun/registro.py`)
    de la herramienta que lo pinta: sale marcada en rojo y no es un enlace.
    """
    from comun.registro import PAGINAS

    with fila("menu", vertical_alignment="center"):
        st.markdown(
            '<div class="marca"><i></i>Herramientas<small>Oficina de Empleo · Ciudad Lineal</small></div>',
            unsafe_allow_html=True,
        )
        for h in PAGINAS:
            st.page_link(h["ruta"], label=h.get("corto") or h["titulo"], icon=h["icono"],
                         disabled=(h["id"] == actual))
