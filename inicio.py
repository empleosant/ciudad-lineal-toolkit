"""
Portada de la caja de herramientas.

Una columna por momento de la cita (inscribir, currículum, preparar,
orientar: `MOMENTOS` en `comun/registro.py`) y, dentro, una tarjeta por
herramienta. Arriba, el buscador del codificador, que es lo que más se usa:
se empieza a buscar sin abrir nada. Abajo, qué datos viajan de una
herramienta a otra. Aquí no hay lógica: solo presentación.

Una herramienta nueva sale sola en la columna de su momento, y un momento
nuevo abre columna. En el móvil las columnas se apilan en el orden de la cita.

Cada tarjeta lleva un `page_link` que el CSS estira a toda la tarjeta: se
pulsa en cualquier sitio y se navega sin recargar la página, que es lo que
mantiene vivos el currículo en curso y lo demás que hay en la sesión. Un
enlace HTML normal recargaría la aplicación y lo perdería.
"""

import html
import re

import streamlit as st

from comun import estilo, guia, mesa, version
from comun.registro import por_momento

estilo.aplica()
st.markdown("""
<style>
[class*="st-key-tarjeta_"]{
  position:relative; background:#fff; border:1px solid var(--linea); border-radius:var(--radio);
  padding:.75rem .85rem 2.3rem; min-height:8.4rem; transition:border-color .15s ease, box-shadow .15s ease;
}
/* Streamlit le resta 16px al markdown por el párrafo final que aquí no hay:
   la caja encogía y la etiqueta «Con IA» quedaba cortada por el borde. */
[class*="st-key-tarjeta_"] div[data-testid="stMarkdownContainer"]{ margin-bottom:0 !important; }
/* En el móvil las columnas se apilan con el hueco del ordenador, el doble
   que entre filas: se iguala. */
@media (max-width:640px){
  div[data-testid="stHorizontalBlock"]:has([class*="st-key-tarjeta_"]){ gap:1rem !important; }
}
[class*="st-key-tarjeta_"]:hover{ border-color:var(--rojo); box-shadow:0 4px 16px rgba(209,18,46,.10); }
[class*="st-key-tarjeta_"] div[data-testid="stVerticalBlock"]{ gap:0; }
.tarjeta-t{ font-weight:700; font-size:1rem; letter-spacing:-.01em; margin:0 0 .25rem; }
.tarjeta-d{ font-size:.82rem; color:var(--suave); line-height:1.42; margin:0 0 .7rem; }
/* La etiqueta va al pie, a la altura de «Abrir», tenga la tarjeta el texto que tenga */
.tarjeta-pie{ position:absolute; left:.85rem; right:2.4rem; bottom:.7rem; margin:0; z-index:1; pointer-events:none;
              display:flex; align-items:center; gap:.5rem; white-space:nowrap; overflow:hidden; }
.tarjeta-pie .chip{ margin:0; flex:0 0 auto; }
div[data-testid="stMarkdownContainer"]:has(.momento){ margin-bottom:0 !important; }
.tarjeta-pie small{ font-family:'JetBrains Mono',monospace; font-size:.66rem; color:var(--suave); }
/* El rótulo de cada momento: número en rojo y filete negro debajo */
.momento{ font-family:'JetBrains Mono',monospace; font-size:.68rem; font-weight:700; letter-spacing:.06em;
          text-transform:uppercase; color:var(--suave); padding-bottom:.35rem; border-bottom:2px solid var(--negro); }
.momento i{ font-style:normal; color:var(--rojo); margin-right:.35rem; }
div[data-testid="stColumn"]:has(.momento) > div[data-testid="stVerticalBlock"]{ gap:.5rem; }
/* El buscador de la portada */
.st-key-portada_buscador{ align-items:flex-end; }
.st-key-portada_buscador > div:first-child{ flex:1 1 auto !important; min-width:0; }
.st-key-portada_buscador > div:last-child{ flex:0 0 auto !important; width:auto !important; }
div[data-testid="stForm"]:has(.st-key-portada_buscador){ border:0 !important; padding:0 !important; }
/* Lo que viaja entre herramientas: una fila por paso de datos */
.viaja{ background:#fff; border:1px solid var(--linea); border-radius:var(--radio); }
.viaja div{ display:flex; gap:.6rem; align-items:baseline; padding:.42rem .75rem; border-top:1px solid var(--gris); font-size:.82rem; }
.viaja div:first-child{ border-top:0; }
.viaja b{ white-space:nowrap; } .viaja b i{ font-style:normal; color:var(--rojo); font-weight:800; }
.viaja span{ color:var(--suave); min-width:0; }
.pie-portada{ font-family:'JetBrains Mono',monospace; font-size:.66rem; color:var(--suave);
              display:flex; flex-wrap:wrap; gap:.2rem 1.1rem; margin-top:1rem; }
@media (max-width:640px){ .viaja div{ flex-direction:column; gap:0; } }
[class*="st-key-tarjeta_"] div[data-testid="stMarkdown"],
[class*="st-key-tarjeta_"] div[data-testid="stMarkdown"] > div,
[class*="st-key-tarjeta_"] div[data-testid="stMarkdownContainer"]{ position:static !important; }
/* El enlace cubre la tarjeta entera; su texto se ve abajo a la derecha. Los
   envoltorios de Streamlit llevan position:relative y se lo quitamos, para
   que el enlace se mida contra la tarjeta y no contra su propia cajita. */
[class*="st-key-tarjeta_"] div[data-testid="stElementContainer"],
[class*="st-key-tarjeta_"] div[data-testid="stPageLink"]{ position:static !important; }
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"]{
  position:absolute; inset:0; display:flex; align-items:flex-end; justify-content:flex-end;
  padding:.62rem .85rem; background:transparent !important; text-decoration:none !important;
  border-radius:var(--radio);
}
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"] p{
  color:var(--rojo) !important; font-weight:800; font-size:1rem; margin:0;
}
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"]:hover p{ text-decoration:underline; text-underline-offset:3px; }
</style>
""", unsafe_allow_html=True)

with estilo.banda(
    "inicio", "Herramientas de orientación",
    "Lo que se hace con una persona en la mesa, en el orden en que se hace. "
    "Lo que averiguas en una herramienta ya está puesto en la siguiente.",
):
    # Un formulario para que Intro busque, como en el codificador.
    with st.form("portada_buscar", border=False):
        with estilo.fila("portada_buscador", vertical_alignment="bottom"):
            descrito = st.text_input(
                "Empieza por el código de ocupación", key="portada_consulta",
                placeholder="Describe el puesto: «limpiaba habitaciones en un hotel»",
            )
            buscar = st.form_submit_button("Buscar", type="primary")
    if buscar and (descrito or "").strip():
        # El codificador recoge `sispe_pendiente` al abrirse y busca.
        st.session_state["sispe_pendiente"] = descrito.strip()
        st.switch_page("herramientas/sispe/vista.py")


def _cifra(n):
    return f"{n:,}".replace(",", ".")


def dato(h):
    """La cifra del pie de la tarjeta: de qué tamaño es lo que hay detrás, o
    cómo va lo que hay en la mesa. '' si la herramienta no tiene nada que decir."""
    try:
        if h["id"] == "sispe":
            from herramientas.sispe import motor as sispe
            return f"{_cifra(len(sispe.IDX['registros']))} ocupaciones"
        if h["id"] == "extranjeria":
            from herramientas.extranjeria import motor as extranjeria
            fecha = extranjeria.NOTAS["titulo"].split("·")[-1].strip().lower()
            # «Actualizado septiembre 2026» -> «septiembre de 2026»
            fecha = re.sub(r"^actualizad[oa]\s+", "", fecha)
            return re.sub(r"^([a-zé]+) (\d{4})$", r"\1 de \2", fecha)
        if h["id"] == "cv":
            n = mesa.cesta()
            return f"{n} puesto{'s' if n != 1 else ''} en curso" if n else ""
        if h["id"] == "guia":
            n = len(mesa.empresas())
            return (f"{n} marcada{'s' if n != 1 else ''}" if n
                    else f"{_cifra(int(guia.EDICION['fichas']))} fichas")
    except Exception:  # noqa: BLE001
        pass
    return ""


def tarjeta(h):
    with estilo.caja(f"tarjeta_{h['id']}"):
        cifra = dato(h)
        st.markdown(
            f'<div class="tarjeta-t">{html.escape(h["titulo"])}</div>'
            f'<div class="tarjeta-d">{html.escape(h["descripcion"])}</div>'
            f'<div class="tarjeta-pie"><span class="chip {"negro" if h.get("ia") else ""}">'
            f'{"Con IA" if h.get("ia") else "Sin IA"}</span>'
            + (f"<small>{html.escape(cifra)}</small>" if cifra else "") + "</div>",
            unsafe_allow_html=True,
        )
        st.page_link(h["ruta"], label="→", help=f"Abrir {h['titulo']}")


grupos = por_momento()
cols = st.columns(len(grupos), gap="medium")
for n, (col, (_, rotulo, herramientas)) in enumerate(zip(cols, grupos), 1):
    with col:
        st.markdown(f'<div class="momento"><i>{n:02d}</i>{html.escape(rotulo)}</div>',
                    unsafe_allow_html=True)
        for h in herramientas:
            tarjeta(h)

st.markdown('<div class="seccion">Lo que viaja entre herramientas</div>', unsafe_allow_html=True)
VIAJA = [
    ("Codificador", "Generador de CV", "la experiencia, con el nombre del puesto ya preparado"),
    ("Codificador", "Dónde enviar", "el sector de la ocupación, y las empresas que se marquen"),
    ("Generador de CV", "Formación", "el perfil, sin el nombre ni el contacto"),
    ("Generador de CV", "Informes", "la trayectoria"),
    ("Dónde enviar", "Generador de CV", "las empresas marcadas, en la hoja aparte del paso 4"),
    ("Guía de empleo", "Informes", "las empresas comprobadas del sector, para el correo de cierre"),
]
st.markdown(
    '<div class="viaja">' + "".join(
        f"<div><b>{html.escape(de)} <i>→</i> {html.escape(a)}</b><span>{html.escape(que)}</span></div>"
        for de, a, que in VIAJA
    ) + "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="pie-portada"><span>Versión {html.escape(version.commit())}</span>'
    f'<span>Guía de empleo: {html.escape(guia.EDICION["edicion"].lower())}</span></div>',
    unsafe_allow_html=True,
)
