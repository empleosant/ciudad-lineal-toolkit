"""
Portada de la caja de herramientas.

Una tarjeta por herramienta, a partir de `comun/registro.py`, y el dibujo de
cómo se pasan datos entre sí. Aquí no hay lógica: solo presentación.

Las tarjetas van en filas de tres, una fila por `st.columns`: así en el móvil,
donde las columnas se apilan, salen en el orden del registro. Con una sola
fila de tres columnas y las tarjetas repartidas por turnos se apilaban por
columnas y el orden se descolocaba.

Cada tarjeta lleva un `page_link` que el CSS estira a toda la tarjeta: se
pulsa en cualquier sitio y se navega sin recargar la página, que es lo que
mantiene vivos el currículo en curso y lo demás que hay en la sesión. Un
enlace HTML normal recargaría la aplicación y lo perdería.
"""

import html

import streamlit as st

from comun import estilo, version
from comun.registro import HERRAMIENTAS

estilo.aplica()
st.markdown("""
<style>
[class*="st-key-tarjeta_"]{
  position:relative; background:#fff; border:1px solid var(--linea); border-radius:var(--radio);
  padding:.95rem 1rem .8rem; min-height:10.4rem; transition:border-color .15s ease, box-shadow .15s ease;
}
[class*="st-key-tarjeta_"]:hover{ border-color:var(--rojo); box-shadow:0 4px 16px rgba(209,18,46,.10); }
[class*="st-key-tarjeta_"] div[data-testid="stVerticalBlock"]{ gap:0; }
.tarjeta-ic{
  width:32px; height:32px; border-radius:7px; background:var(--gris); color:var(--texto);
  display:flex; align-items:center; justify-content:center; margin-bottom:.6rem;
}
.tarjeta-ic span[data-testid="stIconMaterial"], .tarjeta-ic .material-symbols-rounded{ font-size:20px; }
.tarjeta-t{ font-weight:700; font-size:1rem; letter-spacing:-.01em; margin:0 0 .25rem; }
.tarjeta-d{ font-size:.82rem; color:var(--suave); line-height:1.42; margin:0 0 .7rem; }
.tarjeta-pie{ margin:0; }
/* El enlace cubre la tarjeta entera; su texto se ve abajo a la derecha. Los
   envoltorios de Streamlit llevan position:relative y se lo quitamos, para
   que el enlace se mida contra la tarjeta y no contra su propia cajita. */
[class*="st-key-tarjeta_"] div[data-testid="stElementContainer"],
[class*="st-key-tarjeta_"] div[data-testid="stPageLink"]{ position:static !important; }
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"]{
  position:absolute; inset:0; display:flex; align-items:flex-end; justify-content:flex-end;
  padding:.8rem 1rem; background:transparent !important; text-decoration:none !important;
  border-radius:var(--radio);
}
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"] p{
  color:var(--rojo) !important; font-weight:700; font-size:.82rem; margin:0;
}
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"]:hover p{ text-decoration:underline; text-underline-offset:3px; }
.tarjeta-datos{
  border:1px dashed #C9CBD2; border-radius:var(--radio); min-height:10.4rem; padding:1rem;
  display:flex; align-items:center; justify-content:center; text-align:center;
  font-size:.8rem; color:var(--suave); line-height:1.5;
}
.tarjeta-datos b{ color:var(--texto); }

/* Cómo se pasan datos: una cadena de tres, y las dos que van por libre */
.flujo{ display:flex; align-items:stretch; background:#fff; border:1px solid var(--linea); border-radius:var(--radio); overflow:hidden; }
.flujo .nodo{ flex:1 1 0; padding:.8rem .95rem; min-width:0; }
.flujo .nodo b{ display:block; font-size:.9rem; margin-bottom:.15rem; }
.flujo .nodo span{ font-size:.78rem; color:var(--suave); line-height:1.4; }
.flujo .paso-datos{
  flex:0 0 auto; display:flex; flex-direction:column; justify-content:center; align-items:center;
  padding:.5rem .8rem; background:#FAFAFA; border-left:1px solid var(--linea); border-right:1px solid var(--linea);
  font-size:.72rem; color:var(--suave); text-align:center; line-height:1.3; max-width:9rem;
}
.flujo .paso-datos i{ color:var(--rojo); font-style:normal; font-weight:800; font-size:1rem; }
.flujo .nodo.aparte{ background:#FAFAFA; border-left:1px dashed #C9CBD2; }
@media (max-width:640px){
  .flujo{ flex-direction:column; }
  .flujo .paso-datos{ border:0; border-top:1px solid var(--linea); border-bottom:1px solid var(--linea); max-width:none; flex-direction:row; gap:.5rem; }
  .flujo .paso-datos i{ transform:rotate(90deg); }
  .flujo .nodo.aparte{ border-left:0; border-top:1px dashed #C9CBD2; }
}
</style>
""", unsafe_allow_html=True)

estilo.banda(
    "inicio", "Herramientas de orientación",
    "Pequeñas utilidades para el día a día de la oficina, que se pasan datos entre sí.",
)


def tarjeta(h):
    with estilo.caja(f"tarjeta_{h['id']}"):
        icono = h["icono"].replace(":material/", "").rstrip(":")
        st.markdown(
            f'<div class="tarjeta-ic"><span class="material-symbols-rounded" '
            f'style="font-family:\'Material Symbols Rounded\'">{icono}</span></div>'
            f'<div class="tarjeta-t">{html.escape(h["titulo"])}</div>'
            f'<div class="tarjeta-d">{html.escape(h["descripcion"])}</div>'
            f'<div class="tarjeta-pie"><span class="chip {"negro" if h.get("ia") else ""}" '
            f'style="margin:0">{"Con IA" if h.get("ia") else "Sin IA"}</span></div>',
            unsafe_allow_html=True,
        )
        st.page_link(h["ruta"], label="Abrir →")


def datos():
    """La sexta celda: qué versión corre y de cuándo son los datos."""
    try:
        from herramientas.sispe import motor as sispe
        n_ocupaciones = f"{len(sispe.IDX['registros']):,}".replace(",", ".")
    except Exception:  # noqa: BLE001
        n_ocupaciones = "2.218"
    try:
        from herramientas.extranjeria import motor as extranjeria
        fecha_ext = extranjeria.NOTAS["titulo"].split("·")[-1].strip().lower()
    except Exception:  # noqa: BLE001
        fecha_ext = "septiembre de 2026"
    st.markdown(
        f'<div class="tarjeta-datos"><div>Versión <b>{version.commit()}</b><br>'
        f'Catálogo SISPE de <b>{n_ocupaciones}</b> ocupaciones<br>'
        f'Extranjería: datos de <b>{html.escape(fecha_ext)}</b></div></div>',
        unsafe_allow_html=True,
    )


st.markdown('<div class="seccion">Herramientas</div>', unsafe_allow_html=True)
celdas = [("tarjeta", h) for h in HERRAMIENTAS] + [("datos", None)]
for i in range(0, len(celdas), 3):
    cols = st.columns(3, gap="medium")
    for col, (tipo, h) in zip(cols, celdas[i:i + 3]):
        with col:
            # Sentencias, no una expresión: Streamlit pinta el valor de una
            # expresión suelta, y aquí saldría un «None» bajo cada tarjeta.
            if tipo == "tarjeta":
                tarjeta(h)
            else:
                datos()

st.markdown('<div class="seccion">Cómo se pasan datos</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="flujo">'
    '<div class="nodo"><b>Codificador SISPE</b><span>Busca la ocupación y pulsa «+ CV».</span></div>'
    '<div class="paso-datos"><i>→</i>la experiencia, con el nombre del puesto ya preparado</div>'
    '<div class="nodo"><b>Generador de CV</b><span>Ordena la trayectoria y saca el Word.</span></div>'
    '<div class="paso-datos"><i>→</i>el perfil, sin el nombre ni el contacto</div>'
    '<div class="nodo"><b>Asesor de formación</b><span>Propone cursos del catálogo y explica por qué.</span></div>'
    '<div class="nodo aparte"><b>Informes · Extranjería</b><span>Van por libre. Informes también puede '
    'tomar la trayectoria del generador de CV.</span></div>'
    '</div>',
    unsafe_allow_html=True,
)
