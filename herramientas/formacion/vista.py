"""
Asesor de formación: la pantalla.

Dos entradas: el catálogo de cursos (Excel o CSV, arrastrado) y el perfil de
la persona (un .md o .txt arrastrado, pegado a mano, o tomado del generador
de CV). La IA propone cursos del catálogo y explica por qué. Solo puede
elegir cursos que existen: devuelve números de fila y la app muestra los
datos reales del Excel.

Claves de sesión con prefijo `fmc_`; las de widgets, `fmc_w_`.
"""

import streamlit as st

from comun import estilo, ia
from herramientas.cv import estado as cv_estado
from herramientas.formacion import modelo, motor

estilo.aplica()
st.markdown("""
<style>
.block-container{ max-width:1040px; padding-bottom:3.5rem !important; }
.seccion{ margin-top:1.4rem; }
.st-key-cabecera{ margin-bottom:.4rem; }
.prioridad{
  display:inline-block; font-size:.62rem; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; padding:.14rem .5rem; border-radius:3px; margin-left:.4rem;
  background:var(--gris); color:var(--suave); vertical-align:middle;
}
.prioridad.alta{ background:var(--rojo); color:#fff; }
.prioridad.media{ background:#FFF7ED; color:#C2410C; border:1px solid #FFEDD5; }
.curso-titulo{ font-size:1rem; font-weight:700; margin:0 0 .2rem; }
.curso-campos{ font-size:.8rem; color:var(--suave); line-height:1.45; margin:0 0 .45rem; }
.curso-porque{ font-size:.9rem; line-height:1.4; margin:0; }
.curso-aviso{ font-size:.82rem; color:#C2410C; margin:.35rem 0 0; }
</style>
""", unsafe_allow_html=True)

estilo.banda(
    "formacion", "Asesor de formación",
    "Sube el catálogo de cursos y el perfil de la persona; la IA propone los que más le convienen.",
)

st.session_state.setdefault("fmc_cursos", [])
st.session_state.setdefault("fmc_filas", 0)
st.session_state.setdefault("fmc_hojas", [])
st.session_state.setdefault("fmc_archivo", "")
st.session_state.setdefault("fmc_resultado", None)

# ---------------------------------------------------------------------------
# 1. Catálogo de cursos
# ---------------------------------------------------------------------------

st.markdown('<div class="seccion">1 · Catálogo de cursos</div>', unsafe_allow_html=True)
st.caption(
    "El Excel de cursos se descarga del portal de formación de la Comunidad de Madrid: "
    "[vialaboris.comunidad.madrid/Formacion](https://vialaboris.comunidad.madrid/Formacion/). "
    "Sube aquí ese archivo tal cual."
)
archivo = st.file_uploader(
    "Excel o CSV con los cursos", type=["xlsx", "xls", "csv"], key="fmc_w_excel",
    help="Vale cualquier hoja con una fila por curso. Se usan las columnas que tengan contenido.",
)
if archivo is not None:
    huella = f"{archivo.name}:{archivo.size}"
    hoja = st.session_state.get("fmc_w_hoja")
    if st.session_state["fmc_archivo"] != huella or st.session_state.get("fmc_hoja_leida") != hoja:
        try:
            filas, hojas = motor.lee_filas(archivo.getvalue(), archivo.name, hoja)
            st.session_state.update(fmc_cursos=motor.agrupa(filas), fmc_filas=len(filas),
                                    fmc_hojas=hojas, fmc_archivo=huella,
                                    fmc_hoja_leida=hoja, fmc_resultado=None)
        except Exception as e:  # noqa: BLE001
            st.error(f"No he podido leer el archivo: {type(e).__name__}: {e}")
            st.session_state.update(fmc_cursos=[], fmc_filas=0, fmc_hojas=[], fmc_archivo="")
    if len(st.session_state["fmc_hojas"]) > 1:
        st.selectbox("Hoja del Excel", st.session_state["fmc_hojas"], key="fmc_w_hoja")
        if st.session_state.get("fmc_hoja_leida") != st.session_state.get("fmc_w_hoja"):
            st.rerun()
else:
    st.session_state.update(fmc_cursos=[], fmc_filas=0, fmc_hojas=[], fmc_archivo="", fmc_resultado=None)

cursos = st.session_state["fmc_cursos"]
if cursos:
    n_filas = st.session_state["fmc_filas"]
    st.caption(
        f"{n_filas} ediciones leídas, {len(cursos)} cursos distintos. "
        "Las ediciones del mismo curso (otro centro, otra fecha) se agrupan."
    )
    with st.expander("Ver los primeros cursos tal como se los paso a la IA"):
        st.code(motor.lista_para_ia(cursos[:6]), language=None)

# ---------------------------------------------------------------------------
# 2. Perfil de la persona
# ---------------------------------------------------------------------------

st.markdown('<div class="seccion">2 · Perfil de la persona</div>', unsafe_allow_html=True)
st.caption(
    "Experiencia, formación, intereses, limitaciones de horario o de nivel. "
    "Sin nombre, teléfono ni ningún dato identificativo: el perfil se manda a la IA."
)
with st.expander("Cómo obtener el perfil desde Teams (protección de datos)"):
    st.markdown(
        "Por protección de datos, en la Comunidad de Madrid **el CV de la persona solo "
        "puede subirse a Teams**, que es la única herramienta autorizada. El camino es: "
        "subir el CV al asistente de Teams, pedirle un perfil **sin datos identificativos** "
        "en Markdown, guardarlo como `.md` y arrastrarlo aquí. Texto de encargo para pegar en Teams:"
    )
    st.code(
        "A partir del CV adjunto, redacta un perfil profesional en Markdown para orientación "
        "laboral. NO incluyas nombre, apellidos, fecha de nacimiento, DNI, teléfono, correo, "
        "dirección ni nombres de empresas concretas: sustitúyelos por el tipo de empresa. "
        "Incluye: experiencia (puestos, años aproximados y funciones), formación, idiomas, "
        "informática, permisos de conducir y disponibilidad. Devuelve solo el Markdown.",
        language=None,
    )
    st.caption(
        "Antes de arrastrar el archivo, échale un vistazo: si se ha colado algún dato "
        "identificativo, bórralo. Aquí lo que llega al cuadro se puede editar."
    )
izq, der = st.columns([3, 2], gap="medium")
with izq:
    md = st.file_uploader("Archivo .md o .txt", type=["md", "txt"], key="fmc_w_md")
with der:
    n_cv = len(cv_estado.experiencias())
    if st.button(
        f"Tomar el perfil del generador de CV ({n_cv} exp.)" if n_cv else "Tomar el perfil del generador de CV",
        use_container_width=True, disabled=not n_cv,
        help="Usa lo que hay en el generador de CV, sin el nombre ni el contacto.",
    ):
        st.session_state["fmc_w_perfil"] = motor.perfil_desde_cv(cv_estado.cv())
        st.rerun()

if md is not None:
    huella_md = f"{md.name}:{md.size}"
    if st.session_state.get("fmc_md") != huella_md:
        st.session_state["fmc_md"] = huella_md
        st.session_state["fmc_w_perfil"] = md.getvalue().decode("utf-8", errors="replace")
        st.rerun()

perfil = st.text_area(
    "Perfil", key="fmc_w_perfil", height=180, label_visibility="collapsed",
    placeholder="Ejemplo: seis años como camarera de piso en hoteles, dos como reponedora. "
                "Graduado en ESO. Le interesa el sector sociosanitario. Solo puede por las mañanas.",
)

# ---------------------------------------------------------------------------
# 3. Sugerencias
# ---------------------------------------------------------------------------

st.markdown('<div class="seccion">3 · Sugerencias</div>', unsafe_allow_html=True)
c1, c2 = st.columns([1, 2], gap="medium")
cuantos = c1.slider("Cuántos cursos proponer", 3, 8, 5, key="fmc_w_cuantos")
listo = bool(cursos) and len((perfil or "").strip()) >= 20
if not listo:
    c2.caption("Hace falta el catálogo de cursos y un perfil de al menos unas líneas.")
if c2.button("Pedir sugerencias", type="primary", use_container_width=True, disabled=not listo):
    candidatos = motor.preselecciona(cursos, perfil)
    with st.spinner(f"Comparando el perfil con {len(candidatos)} cursos…"):
        try:
            recs, obs, desc = modelo.sugiere(ia.cliente(), perfil, candidatos, cuantos)
            st.session_state["fmc_resultado"] = {
                "recs": recs, "obs": obs, "desc": desc, "preseleccion": len(candidatos),
                "total": len(cursos),
            }
        except Exception as e:  # noqa: BLE001
            st.session_state["fmc_resultado"] = None
            st.error(f"No he podido pedir las sugerencias. {type(e).__name__}: {e}")

res = st.session_state.get("fmc_resultado")
if res:
    if res["preseleccion"] < res["total"]:
        st.caption(
            f"De {res['total']} cursos, la IA ha valorado los {res['preseleccion']} que más "
            "palabras comparten con el perfil."
        )
    if not res["recs"]:
        st.info("La IA no ha encontrado cursos que encajen. Prueba con un perfil más detallado.")
    for r in res["recs"]:
        c = r["curso"]
        cabecera = " · ".join(x for x in (c.get("tipo"), c.get("codigo_esp")) if x)
        ediciones = "<br>".join(
            f"<b>{e['inicio'] or 'sin fecha'}</b> · {e['municipio'] or '?'} · {e['modalidad'].lower()}"
            f" · {e['centro']}" + (f" · código {e['codigo']}" if e["codigo"] else "")
            for e in c["ediciones"][:6]
        )
        if len(c["ediciones"]) > 6:
            ediciones += f"<br>y {len(c['ediciones']) - 6} ediciones más"
        with st.container(border=True):
            st.markdown(
                f'<div class="curso-titulo">{c["denominacion"]}'
                f'<span class="prioridad {r["prioridad"]}">{r["prioridad"]}</span></div>'
                f'<div class="curso-campos">{cabecera}</div>'
                f'<div class="curso-porque">{r["por_que"]}</div>'
                + (f'<div class="curso-aviso">⚠ {r["aviso"]}</div>' if r["aviso"] else "")
                + (f'<div class="curso-campos" style="margin-top:.4rem"><b>Edición que encaja:</b> {r["edicion"]}</div>' if r["edicion"] else ""),
                unsafe_allow_html=True,
            )
            with st.expander(f"Ediciones ({len(c['ediciones'])})"):
                st.markdown(f'<div class="curso-campos">{ediciones}</div>', unsafe_allow_html=True)
    if res["obs"]:
        st.markdown('<div class="seccion">Para el orientador</div>', unsafe_allow_html=True)
        st.markdown(res["obs"])
    if res["desc"]:
        st.caption(f"Se han descartado {res['desc']} propuestas que no correspondían a ningún curso del catálogo.")

    lineas = ["Cursos sugeridos", ""]
    for i, r in enumerate(res["recs"], 1):
        c = r["curso"]
        tipo = f" · {c['tipo']}" if c.get("tipo") else ""
        lineas.append(f"{i}. {c['denominacion']}{tipo} (prioridad {r['prioridad']})")
        lineas.append(f"   {r['por_que']}")
        if r["edicion"]:
            lineas.append(f"   Edición: {r['edicion']}")
        if r["aviso"]:
            lineas.append(f"   Aviso: {r['aviso']}")
    if res["obs"]:
        lineas += ["", res["obs"]]
    with st.expander("Texto para copiar en un correo o en la ficha"):
        st.code("\n".join(lineas), language=None)
