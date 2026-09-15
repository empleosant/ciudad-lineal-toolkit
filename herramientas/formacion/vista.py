"""
Asesor de formación: la pantalla.

Dos entradas, una al lado de la otra: el catálogo de cursos (Excel o CSV,
arrastrado) y el perfil de la persona (un .md o .txt arrastrado, pegado a
mano, o tomado del generador de CV). La IA propone cursos del catálogo y
explica por qué. Solo puede elegir cursos que existen: devuelve números de
fila y la app muestra los datos reales del Excel.

El catálogo se descarga otra vez cada pocas semanas y NO viene igual: cambian
las cabeceras y a veces faltan columnas. Por eso aquí no se da por supuesta
ninguna columna (las etiquetas que no tienen dato no se pintan) y hay un
informe de qué ha entendido la aplicación de ESTE archivo.

Claves de sesión con prefijo `fmc_`; las de widgets, `fmc_w_`.
"""

import os

import streamlit as st

from comun import estilo, ia
from comun.texto import esc
from herramientas.cv import estado as cv_estado
from herramientas.formacion import modelo, motor

EJEMPLO_MD = open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos", "perfil_ejemplo.md"),
    encoding="utf-8",
).read()


def columnas_que_faltan(n):
    """«falta 1 columna» / «faltan 3 columnas». Se dice en dos sitios."""
    return f"falta {n} columna" if n == 1 else f"faltan {n} columnas"


estilo.aplica()
st.markdown("""
<style>
.st-key-cabecera{ margin-bottom:.6rem; }
.entrada-t{ font-size:.95rem; font-weight:700; margin:0 0 .15rem; }
.entrada-d{ font-size:.8rem; color:var(--suave); line-height:1.4; margin:0 0 .5rem; min-height:2.8rem; }
.recuento{ font-size:.82rem; color:#1B6B3A; font-weight:600; margin:.45rem 0 0; }
.curso-titulo{ font-size:1rem; font-weight:700; margin:0 0 .2rem; }
.curso-campos{ font-size:.8rem; color:var(--suave); line-height:1.45; margin:0 0 .45rem; }
.curso-porque{ font-size:.9rem; line-height:1.4; margin:0; }
.curso-aviso{ font-size:.82rem; color:#C2410C; margin:.45rem 0 0; }
.sin-dato{ font-size:.8rem; color:var(--tenue); }
/* Mandos de ordenar y descartar, a la derecha de cada propuesta.
   Sin esto, Streamlit los reparte por todo el alto de la tarjeta. */
[class*="st-key-mandos_"]{ gap:.25rem !important; }
[class*="st-key-mandos_"] div[data-testid="stVerticalBlock"]{ gap:.25rem !important; }
[class*="st-key-mandos_"] div[data-testid="stElementContainer"]{ margin-bottom:0 !important; }
[class*="st-key-mandos_"] button{
  min-height:0 !important; height:auto !important; padding:.2rem .4rem !important;
  border:1px solid var(--linea) !important; background:#fff !important; box-shadow:none !important;
}
[class*="st-key-mandos_"] button p{
  font-size:.78rem !important; font-weight:600 !important; margin:0 !important; color:var(--suave) !important;
}
[class*="st-key-mandos_"] button:hover:not(:disabled){ border-color:var(--negro) !important; }
[class*="st-key-mandos_"] button:hover:not(:disabled) p{ color:var(--texto) !important; }
.descartada{ font-size:.86rem; color:var(--suave); line-height:1.35; padding-top:.3rem; }
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
st.session_state.setdefault("fmc_informe", None)
st.session_state.setdefault("fmc_resultado", None)

# El indicador de pasos va arriba, pero no sabe qué contar hasta que se han
# pintado el cargador y el cuadro de texto. Se reserva el hueco y se rellena
# al final, que es la forma de Streamlit de poner algo antes de calcularlo.
hueco_pasos = st.empty()

# ---------------------------------------------------------------------------
# Las dos entradas
# ---------------------------------------------------------------------------

st.markdown('<div class="seccion">Las dos entradas</div>', unsafe_allow_html=True)
col_cat, col_per = st.columns(2, gap="medium")

# --- 1. Catálogo de cursos -------------------------------------------------
with col_cat:
    st.markdown(
        '<div class="entrada-t">1 · Catálogo de cursos</div>'
        '<div class="entrada-d">El Excel del buscador de acciones formativas de la Comunidad de '
        'Madrid, tal cual se descarga de <a href="https://vialaboris.comunidad.madrid/Formacion/" '
        'target="_blank">vialaboris.comunidad.madrid/Formacion</a>.</div>',
        unsafe_allow_html=True,
    )
    with estilo.caja("soltar_cursos"):
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
                                        fmc_informe=motor.informe_columnas(filas),
                                        fmc_hoja_leida=hoja, fmc_resultado=None)
            except Exception as e:  # noqa: BLE001
                st.error(f"No he podido leer el archivo: {type(e).__name__}: {e}")
                st.session_state.update(fmc_cursos=[], fmc_filas=0, fmc_hojas=[],
                                        fmc_archivo="", fmc_informe=None)
        if len(st.session_state["fmc_hojas"]) > 1:
            st.selectbox("Hoja del Excel", st.session_state["fmc_hojas"], key="fmc_w_hoja")
            if st.session_state.get("fmc_hoja_leida") != st.session_state.get("fmc_w_hoja"):
                st.rerun()
    else:
        st.session_state.update(fmc_cursos=[], fmc_filas=0, fmc_hojas=[], fmc_archivo="",
                                fmc_informe=None, fmc_resultado=None)

    cursos = st.session_state["fmc_cursos"]
    informe = st.session_state["fmc_informe"]

    if cursos:
        n_filas = st.session_state["fmc_filas"]
        st.markdown(
            f'<div class="recuento">{n_filas} ediciones · {len(cursos)} cursos distintos</div>'
            '<div class="nota">Las ediciones del mismo curso (otro centro, otra fecha) se agrupan.</div>',
            unsafe_allow_html=True,
        )

        # Cada descarga del catálogo trae las cabeceras a su manera. Esto no
        # arregla el archivo, lo enseña: si algo importante no se ha
        # reconocido, se ve aquí y no cuando falten las sugerencias.
        if informe and informe["deducidas"]:
            cuales = ", ".join(f"«{esc(c)}»" for _, c in informe["deducidas"])
            st.warning(
                f"No he encontrado una columna con el nombre del curso, así que he tirado de "
                f"{cuales}, que es la de texto más largo. Compruébalo abajo antes de seguir."
            )

        if informe:
            faltan = informe["ausentes"]
            with st.expander(
                "Qué ha entendido de este archivo"
                + (f" · {columnas_que_faltan(len(faltan))}" if faltan else " · todo reconocido")
            ):
                filas_html = "".join(
                    f'<tr><td><b>{esc(rotulo)}</b></td><td>{esc(columna)}</td></tr>'
                    for rotulo, columna in informe["reconocidas"]
                ) + "".join(
                    f'<tr><td><b>{esc(rotulo)}</b></td>'
                    f'<td class="sin-dato">deducida: {esc(columna)}</td></tr>'
                    for rotulo, columna in informe["deducidas"]
                ) + "".join(
                    f'<tr><td>{esc(rotulo)}</td><td class="sin-dato">no está en este archivo</td></tr>'
                    for rotulo in faltan
                )
                st.markdown(
                    '<div class="envuelve-tabla"><table class="tablilla">'
                    '<thead><tr><th>Dato</th><th>Columna del archivo</th></tr></thead>'
                    f"<tbody>{filas_html}</tbody></table></div>",
                    unsafe_allow_html=True,
                )
                if informe["sobrantes"]:
                    st.caption(
                        "Columnas que no se usan: "
                        + ", ".join(f"«{c}»" for c in informe["sobrantes"][:8])
                        + ("…" if len(informe["sobrantes"]) > 8 else "")
                    )
                st.caption(
                    "Sin la denominación no hay nada que hacer. Lo demás solo quita detalle: "
                    "las etiquetas de las propuestas que no tengan dato no se pintan."
                )

        with st.expander("Ver los primeros cursos"):
            cabezas = ["#", "Denominación"]
            claves = []
            for clave, rotulo in (("tipo", "Tipo"), ("municipio", "Municipio"), ("inicio", "Inicio")):
                # Solo se enseña la columna si este archivo la trae.
                if any((c.get(clave) if clave == "tipo" else
                        (c["ediciones"][0].get(clave) if c["ediciones"] else "")) for c in cursos[:40]):
                    cabezas.append(rotulo)
                    claves.append(clave)
            cuerpo = []
            for c in cursos[:8]:
                e = c["ediciones"][0] if c["ediciones"] else {}
                celdas = [f'<td class="sin-dato">{c["n"]}</td>', f"<td>{esc(c['denominacion'])}</td>"]
                for clave in claves:
                    celdas.append(f"<td>{esc(c.get(clave) if clave == 'tipo' else e.get(clave, ''))}</td>")
                cuerpo.append(f"<tr>{''.join(celdas)}</tr>")
            st.markdown(
                '<div class="envuelve-tabla"><table class="tablilla"><thead><tr>'
                + "".join(f"<th>{esc(h)}</th>" for h in cabezas)
                + f"</tr></thead><tbody>{''.join(cuerpo)}</tbody></table></div>",
                unsafe_allow_html=True,
            )

# --- 2. Perfil de la persona ----------------------------------------------
with col_per:
    st.markdown(
        '<div class="entrada-t">2 · Perfil de la persona</div>'
        '<div class="entrada-d">Experiencia, formación, intereses y limitaciones. Sin nombre, '
        'teléfono ni ningún dato identificativo: el perfil se manda a la IA.</div>',
        unsafe_allow_html=True,
    )
    with estilo.caja("soltar_perfil"):
        md = st.file_uploader("Archivo .md o .txt", type=["md", "txt"], key="fmc_w_md")

    n_cv = len(cv_estado.experiencias())
    if st.button(
        f"Traerlo del generador de CV ({n_cv} exp.)" if n_cv else "Traerlo del generador de CV",
        use_container_width=True, disabled=not n_cv,
        help="Usa lo que hay en el generador de CV, sin el nombre ni el contacto.",
    ):
        st.session_state["fmc_w_perfil"] = motor.perfil_desde_cv(cv_estado.cv())
        st.rerun()

    with st.expander("Cómo sacarlo de Teams (protección de datos)"):
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
            language=None, wrap_lines=True,
        )
        st.download_button(
            "Descargar un perfil de ejemplo (.md)", EJEMPLO_MD, file_name="perfil_ejemplo.md",
            mime="text/markdown", help="Para ver el nivel de detalle que funciona bien.",
        )

if md is not None:
    huella_md = f"{md.name}:{md.size}"
    if st.session_state.get("fmc_md") != huella_md:
        st.session_state["fmc_md"] = huella_md
        st.session_state["fmc_w_perfil"] = md.getvalue().decode("utf-8", errors="replace")
        st.rerun()

# ---------------------------------------------------------------------------
# El perfil, tal como se va a mandar
# ---------------------------------------------------------------------------

st.markdown('<div class="seccion">El perfil, tal como se va a mandar</div>', unsafe_allow_html=True)
perfil = st.text_area(
    "Perfil", key="fmc_w_perfil", height=180, label_visibility="collapsed",
    placeholder="Ejemplo: seis años como camarera de piso en hoteles, dos como reponedora. "
                "Graduado en ESO. Le interesa el sector sociosanitario. Solo puede por las mañanas.",
)

# La pantalla llevaba tiempo diciendo «échale un vistazo antes de mandarlo» y
# ahí se quedaba. Esto lo comprueba. Lo que NO cubre se dice en voz alta: los
# nombres propios no se detectan, y callarlo daría una seguridad que no hay.
hallazgos = motor.revisa_perfil(perfil)
if (perfil or "").strip():
    if hallazgos:
        lista = ", ".join(f"<b>{esc(trozo)}</b> ({esc(que)})" for que, trozo in hallazgos[:6])
        st.markdown(
            f'<div class="revision alerta">⚠<div>Parece que queda algún dato identificativo: '
            f'{lista}. Bórralo del cuadro antes de pedir las sugerencias.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="revision limpio">✓<div>No encuentro teléfonos, correos, DNI ni direcciones. '
            '<span class="flojo">Los nombres propios no los detecta: esos míralos tú.</span></div></div>',
            unsafe_allow_html=True,
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

# El orientador se queda con lo que le sirve y en su orden. Se toca
# directamente la lista guardada en sesión: esa lista ES el orden, y de ahí
# sale luego el texto para el correo. Lo que se quita no se pierde, se aparta
# a "fuera", porque recuperar una propuesta no debería costar otra llamada a
# la IA. Van como on_click para que el cambio ocurra antes del repintado.

def mueve(i, d):
    r = st.session_state.get("fmc_resultado")
    if not r:
        return
    recs = r["recs"]
    j = i + d
    if 0 <= j < len(recs):
        recs[i], recs[j] = recs[j], recs[i]


def quita(i):
    r = st.session_state.get("fmc_resultado")
    if r and 0 <= i < len(r["recs"]):
        r.setdefault("fuera", []).append(r["recs"].pop(i))


def recupera(j):
    r = st.session_state.get("fmc_resultado")
    fuera = (r or {}).get("fuera") or []
    if 0 <= j < len(fuera):
        r["recs"].append(fuera.pop(j))


res = st.session_state.get("fmc_resultado")
if res:
    res.setdefault("fuera", [])
    if res["preseleccion"] < res["total"]:
        st.caption(
            f"De {res['total']} cursos, la IA ha valorado los {res['preseleccion']} que más "
            "palabras comparten con el perfil."
        )
    if not res["recs"]:
        if res["fuera"]:
            st.info("Has quitado todas las propuestas. Puedes recuperarlas ahí abajo.")
        else:
            st.info("La IA no ha encontrado cursos que encajen. Prueba con un perfil más detallado.")

    resultados = estilo.caja("resultados")
    for i, r in enumerate(res["recs"]):
        c = r["curso"]
        prioridad = r["prioridad"] if r["prioridad"] in ("alta", "media", "baja") else "media"
        cabecera = " · ".join(esc(x) for x in (c.get("tipo"), c.get("codigo_esp")) if x)

        # Las etiquetas salen de la edición real del archivo, no de lo que
        # conteste la IA, y la que no tenga dato sencillamente no se pinta:
        # este Excel puede no traer municipio, ni modalidad, ni fechas.
        e = motor.mejor_edicion(c) or {}
        etiqueta_fecha, clase_fecha = motor.cuando(e.get("inicio", ""))
        etiquetas = [(esc(x), "") for x in (e.get("municipio"), e.get("modalidad")) if x]
        if etiqueta_fecha:
            etiquetas.append((esc(etiqueta_fecha), clase_fecha))
        n_ed = len(c["ediciones"])
        if n_ed > 1:
            etiquetas.append((f"{n_ed} ediciones", ""))

        with resultados, estilo.caja(f"curso_{i}_{prioridad}"), st.container(border=True):
            clase_chip = {"alta": "rojo", "media": "naranja"}.get(prioridad, "")
            cuerpo, mandos = st.columns([9, 1.6], gap="small")
            cuerpo.markdown(
                f'<div class="curso-titulo">{esc(c["denominacion"])}'
                f'<span class="chip {clase_chip}">{esc(prioridad)}</span></div>'
                + (f'<div class="curso-campos">{cabecera}</div>' if cabecera else "")
                + f'<div class="curso-porque">{esc(r["por_que"])}</div>'
                + (f'<div class="etiquetas">'
                   + "".join(f'<span class="et {cl}">{tx}</span>' for tx, cl in etiquetas)
                   + "</div>" if etiquetas else "")
                + (f'<div class="curso-aviso">⚠ {esc(r["aviso"])}</div>' if r["aviso"] else "")
                + (f'<div class="curso-campos" style="margin:.45rem 0 0">'
                   f'<b>Edición que señala la IA:</b> {esc(r["edicion"])}</div>' if r["edicion"] else ""),
                unsafe_allow_html=True,
            )
            # La clave va por el número de curso, no por la posición: al
            # reordenar, la posición cambia y Streamlit se lía con los botones.
            k = c["n"]
            with mandos, estilo.caja(f"mandos_{k}"):
                st.button("↑", key=f"fmc_w_sube_{k}", disabled=(i == 0), use_container_width=True,
                          help="Subir", on_click=mueve, args=(i, -1))
                st.button("↓", key=f"fmc_w_baja_{k}", disabled=(i == len(res["recs"]) - 1),
                          use_container_width=True, help="Bajar", on_click=mueve, args=(i, 1))
                st.button("Quitar", key=f"fmc_w_fuera_{k}", use_container_width=True,
                          help="Apartarla del correo. Se puede recuperar.", on_click=quita, args=(i,))
            with st.expander(f"Ediciones ({n_ed})"):
                columnas_ed = [(cl, ro) for cl, ro in
                               (("inicio", "Inicio"), ("municipio", "Municipio"),
                                ("modalidad", "Modalidad"), ("centro", "Centro"), ("codigo", "Código"))
                               if any(ed.get(cl) for ed in c["ediciones"])]
                cuerpo = "".join(
                    "<tr>" + "".join(f"<td>{esc(ed.get(cl, ''))}</td>" for cl, _ in columnas_ed) + "</tr>"
                    for ed in c["ediciones"][:12]
                )
                st.markdown(
                    '<div class="envuelve-tabla"><table class="tablilla"><thead><tr>'
                    + "".join(f"<th>{esc(ro)}</th>" for _, ro in columnas_ed)
                    + f"</tr></thead><tbody>{cuerpo}</tbody></table></div>",
                    unsafe_allow_html=True,
                )
                if n_ed > 12:
                    st.caption(f"y {n_ed - 12} ediciones más")

    if res["fuera"]:
        with st.expander(f"Descartadas ({len(res['fuera'])})"):
            for j, r in enumerate(res["fuera"]):
                izq, der = st.columns([8, 2], gap="small")
                prio = r["prioridad"] if r["prioridad"] in ("alta", "media", "baja") else "media"
                izq.markdown(
                    f'<div class="descartada">{esc(r["curso"]["denominacion"])}'
                    f'<span class="chip">{esc(prio)}</span></div>',
                    unsafe_allow_html=True,
                )
                der.button("Recuperar", key=f"fmc_w_vuelve_{r['curso']['n']}",
                           use_container_width=True, on_click=recupera, args=(j,))

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
        st.caption("Sale con las propuestas que has dejado y en el orden que les has dado.")
        # wrap_lines: en el movil el cuadro no cabe a lo ancho y sin esto hay
        # que arrastrarlo de lado para leer cada linea.
        st.code("\n".join(lineas), language=None, wrap_lines=True)

# ---------------------------------------------------------------------------
# El indicador de pasos, ya con todo contado
# ---------------------------------------------------------------------------

n_perfil = len((perfil or "").strip())
if not cursos:
    paso_cat = ("Catálogo", "Arrastra el Excel", "activo")
else:
    faltan = len(informe["ausentes"]) if informe else 0
    paso_cat = ("Catálogo",
                f"{len(cursos)} cursos" + (f" · {columnas_que_faltan(faltan)}" if faltan else ""),
                "hecho")

if n_perfil < 20:
    paso_per = ("Perfil", "Arrástralo o pégalo" if not cursos else "Falta el perfil",
                "activo" if cursos else "")
elif hallazgos:
    paso_per = ("Perfil", "Revisa los datos personales", "activo")
else:
    paso_per = ("Perfil", f"{n_perfil} caracteres · revisado", "hecho")

if res and res["recs"]:
    paso_sug = ("Sugerencias", f"{len(res['recs'])} propuestas", "hecho")
elif listo and hallazgos:
    # No se bloquea el botón: puede ser una falsa alarma y quien decide es
    # el orientador. Pero el indicador no va a decir «listo» mientras el
    # perfil tenga pinta de llevar un teléfono dentro.
    paso_sug = ("Sugerencias", "Revisa el perfil antes", "")
elif listo:
    paso_sug = ("Sugerencias", "Listo para pedirlas", "activo")
else:
    paso_sug = ("Sugerencias", "Faltan las dos entradas", "")

with hueco_pasos.container():
    estilo.pasos([paso_cat, paso_per, paso_sug])
