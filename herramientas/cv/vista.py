"""
Generador de CV con IA en pocos pasos: la pantalla.

    1 · Datos        quién es (no se manda a la IA)
    2 · Experiencia  fichas: del codificador SISPE, contadas o grabadas, o a mano
    3 · Formación    títulos, idiomas, informática, otros
    4 · Documento    objetivo profesional redactado por la IA, vista previa y descarga

La lógica está en `motor.py` (Python puro), las llamadas a la IA en
`modelo.py`, el Word sobre el modelo de la oficina en `plantilla.py` y el
currículo en curso en `estado.py`, que es por donde entran las
experiencias que manda el codificador.

Claves de sesión con prefijo `cv_`; las de widgets, `cv_w_`.
"""

import hashlib
import html
import re

import streamlit as st

from comun import estilo, ia
from herramientas.cv import estado, modelo, motor, plantilla

estilo.aplica()
st.markdown("""
<style>
.st-key-cabecera{ margin-bottom:.6rem; }
.seccion{ margin-top:1.3rem; }

/* ---------- Indicador de pasos ---------- */
.st-key-pasos{ margin:.2rem 0 1rem; }
.st-key-pasos div[data-testid="stHorizontalBlock"]{ gap:.4rem !important; }
[class*="st-key-paso_"] button{
  width:100% !important; border-radius:6px !important; padding:.55rem .6rem !important;
  min-height:0 !important; height:auto !important; justify-content:flex-start !important;
  border:1px solid var(--linea) !important; background:#fff !important; box-shadow:none !important;
  transition:all .15s ease;
}
[class*="st-key-paso_"] button p{
  margin:0 !important; font-size:.84rem !important; font-weight:600 !important; color:var(--suave) !important;
  text-align:left !important; line-height:1.25 !important; white-space:normal !important;
}
[class*="st-key-paso_"] button:hover{ border-color:var(--negro) !important; }
[class*="st-key-paso_"] button:hover p{ color:var(--texto) !important; }
[class*="st-key-paso_"][class*="_hecho"] button{ border-color:#BFE3CB !important; background:#F1FAF3 !important; }
[class*="st-key-paso_"][class*="_hecho"] button p{ color:#1B6B3A !important; }
/* El paso activo manda sobre hecho, hover y foco (Streamlit pinta el foco en rojo) */
[class*="st-key-paso_"][class*="_activo"] button,
[class*="st-key-paso_"][class*="_activo"] button:hover,
[class*="st-key-paso_"][class*="_activo"] button:focus,
[class*="st-key-paso_"][class*="_activo"] button:focus:not(:active){
  background:var(--negro) !important; border-color:var(--negro) !important; box-shadow:none !important;
}
[class*="st-key-paso_"][class*="_activo"] button p,
[class*="st-key-paso_"][class*="_activo"] button:hover p,
[class*="st-key-paso_"][class*="_activo"] button:focus p{ color:#fff !important; }
[class*="st-key-paso_"] button:focus:not(:active){ box-shadow:none !important; }

/* ---------- Vista previa como hoja (paso 4) ---------- */
.hoja{
  background:#fff; border:1px solid #DDD; box-shadow:0 6px 24px rgba(0,0,0,.10);
  padding:5% 5.5%; font-family:'Trebuchet MS','Libre Franklin',system-ui,sans-serif; color:#000;
  line-height:1.15; aspect-ratio:210/297; overflow:hidden; position:relative;
}
.hoja .nombre{ font-weight:700; font-size:2.05em; line-height:1.1; margin:0; }
.hoja .contacto{ font-size:1.45em; margin:0 0 0 1.5em; line-height:1.18; }
.hoja .cab{ background:#3366FF; color:#fff; font-size:1.5em; padding:.06em .3em; margin:.55em 0 .2em; line-height:1.15; }
.hoja .cab.primera{ margin-top:.15em; }
.hoja .sector{ font-size:1.5em; text-decoration:underline; margin:.35em 0 .25em .1em; }
.hoja .exp{ font-size:1.35em; margin:.35em 0 0 1.6em; text-indent:-.75em; }
.hoja .exp b{ font-weight:700; } .hoja .exp i{ font-style:italic; }
.hoja .emp, .hoja .fun{ font-size:1.2em; margin:0 0 0 1.5em; text-align:justify; }
.hoja .form{ font-size:1.2em; margin:.3em 0 0 1.6em; text-indent:-.75em; }
.hoja .otro{ font-size:1.2em; margin:.3em 0 0 1.55em; text-indent:-.7em; text-align:justify; }
.hoja .omitida{ opacity:.35; }
.hoja::after{ content:""; position:absolute; left:0; right:0; bottom:0; height:12%;
              background:linear-gradient(transparent, #fff 85%); pointer-events:none; }
</style>
""", unsafe_allow_html=True)

cv = estado.cv()

PASOS = ["Datos", "Experiencia", "Formación", "Documento"]
st.session_state.setdefault("cv_paso", 0)
if isinstance(st.session_state["cv_paso"], str):   # versiones anteriores guardaban el texto
    st.session_state["cv_paso"] = 0


def ir_a(paso):
    st.session_state["cv_paso"] = max(0, min(len(PASOS) - 1, paso))


def empezar_de_nuevo():
    estado.vacia()
    for k in [k for k in st.session_state if k.startswith("cv_w_")]:
        del st.session_state[k]
    st.session_state["cv_paso"] = 0


def campo(etiqueta, clave, **k):
    cv[clave] = st.text_input(etiqueta, value=cv[clave], key=f"cv_w_{clave}", **k)


def area(etiqueta, clave, **k):
    cv[clave] = st.text_area(etiqueta, value=cv[clave], key=f"cv_w_{clave}", **k)


def esc(t):
    return html.escape(str(t or ""))


# ---------------------------------------------------------------------------
# Qué hay hecho, para el indicador de pasos
# ---------------------------------------------------------------------------

def resumen():
    n_exp = len(cv["experiencias"])
    n_form = len([f for f in cv["formacion"] if f.get("titulo")])
    extras = sum(1 for k in ("idiomas", "informatica", "permiso", "disponibilidad", "otros") if cv.get(k))
    return [
        (bool(cv["nombre"] and (cv["telefono"] or cv["email"])),
         cv["nombre"].split()[0] if cv["nombre"] else "Nombre y contacto"),
        (n_exp > 0, f"{n_exp} experiencia{'s' if n_exp != 1 else ''}" if n_exp else "Ninguna todavía"),
        (n_form > 0 or extras > 0,
         " · ".join(x for x in (f"{n_form} título{'s' if n_form != 1 else ''}" if n_form else "",
                                f"{extras} apartado{'s' if extras != 1 else ''}" if extras else "") if x) or "Títulos e idiomas"),
        (bool(cv.get("objetivo")), "Objetivo y descarga" if not cv.get("objetivo") else "Listo para descargar"),
    ]


# ---------------------------------------------------------------------------
# Cabecera e indicador de pasos
# ---------------------------------------------------------------------------

estilo.banda(
    "cv", "Generador de CV",
    "Cuatro pasos y sale en Word sobre el modelo de la oficina, siempre en una página.",
)

n_paso = st.session_state["cv_paso"]
hecho = resumen()
try:
    barra = st.container(key="pasos")
except TypeError:
    barra = st.container()
with barra:
    cols = st.columns(len(PASOS), gap="small")
    for i, (col, nombre) in enumerate(zip(cols, PASOS)):
        ok, detalle = hecho[i]
        clase = f"paso_{i}" + ("_activo" if i == n_paso else "") + ("_hecho" if ok else "")
        marca = "✓" if ok and i != n_paso else str(i + 1)
        with col:
            try:
                caja = st.container(key=clase)
            except TypeError:
                caja = st.container()
            with caja:
                st.button(f"{marca} · {nombre}\n\n{detalle}", key=f"cv_w_ir_{i}",
                          use_container_width=True, on_click=ir_a, args=(i,))


def navegacion(siguiente="Siguiente →"):
    st.markdown('<div class="separa"></div>', unsafe_allow_html=True)
    izq, _, der = st.columns([2, 4, 2], gap="small")
    if n_paso > 0:
        izq.button("← Anterior", use_container_width=True, on_click=ir_a, args=(n_paso - 1,))
    if n_paso < len(PASOS) - 1:
        der.button(siguiente, type="primary", use_container_width=True, on_click=ir_a, args=(n_paso + 1,))


# ---------------------------------------------------------------------------
# 1 · Datos
# ---------------------------------------------------------------------------

if n_paso == 0:
    st.markdown('<div class="seccion">Datos de contacto</div>', unsafe_allow_html=True)
    st.caption("Van en la cabecera del currículo. Nunca se mandan a la IA.")
    campo("Nombre y apellidos", "nombre", placeholder="Tal como debe aparecer en el currículo")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        campo("Teléfono", "telefono", placeholder="612 345 678")
        campo("Código postal y localidad", "localidad", placeholder="28017 (Madrid)")
    with c2:
        campo("Correo electrónico", "email", placeholder="nombre@correo.es")
        campo("Permiso de conducir y vehículo", "permiso", placeholder="Carnet de conducir B.",
              help="Opcional. Sale en «Otros datos de interés».")
    campo("Disponibilidad", "disponibilidad",
          placeholder="Incorporación inmediata, con preferencia por la jornada de mañana.",
          help="Opcional. Sale en «Otros datos de interés».")
    navegacion("Siguiente: experiencia →")

# ---------------------------------------------------------------------------
# 2 · Experiencia
# ---------------------------------------------------------------------------

elif n_paso == 1:
    exps = estado.experiencias()

    st.markdown('<div class="seccion">Añadir experiencias</div>', unsafe_allow_html=True)
    v1, v2, v3 = st.columns(3, gap="small")
    with v1:
        st.markdown('<div class="via"><div class="t">Desde el codificador SISPE</div>'
                    '<div class="d">Busca la ocupación y pulsa «+ CV»: llega aquí con el nombre '
                    'del puesto ya preparado.</div></div>', unsafe_allow_html=True)
        st.page_link("herramientas/sispe/vista.py", label="Ir al codificador", icon=":material/manage_search:")
    with v2:
        st.markdown('<div class="via"><div class="t">Contarla o grabarla</div>'
                    '<div class="d">La persona lo cuenta con sus palabras, por escrito o por el '
                    'micrófono, y la IA lo convierte en fichas.</div></div>', unsafe_allow_html=True)
        abrir_relato = st.toggle("Abrir el cuadro", key="cv_w_abrir_relato")
    with v3:
        st.markdown('<div class="via"><div class="t">A mano</div>'
                    '<div class="d">Una ficha vacía para rellenar campo a campo. Para lo que no '
                    'hace falta codificar.</div></div>', unsafe_allow_html=True)
        st.button("Añadir ficha vacía", key="cv_w_mano", use_container_width=True, on_click=estado.anade_a_mano)

    if abrir_relato:
        with st.container(border=True):
            st.caption(
                "Escribe lo que cuente la persona, tal cual: «Estuve seis años de camarera de piso "
                "en hoteles de Madrid, luego dos en un supermercado reponiendo…», o grábalo. "
                "Sin nombre, teléfono ni ningún dato identificativo: se manda a la IA."
            )
            grabacion = st.audio_input(
                "Grabar con el micrófono", key="cv_w_audio",
                help="Pulsa el micrófono, habla y vuelve a pulsar para parar. Se transcribe y se "
                     "añade al cuadro de texto.",
            )
            if grabacion is not None:
                huella = hashlib.md5(grabacion.getvalue()).hexdigest()
                if st.session_state.get("cv_audio_huella") != huella:
                    with st.spinner("Transcribiendo…"):
                        texto, error = modelo.transcribe(
                            ia.cliente(), grabacion.getvalue(), grabacion.type or "audio/wav",
                        )
                    st.session_state["cv_audio_huella"] = huella
                    if texto:
                        previo = (st.session_state.get("cv_w_relato") or "").rstrip()
                        st.session_state["cv_w_relato"] = f"{previo}\n{texto}".strip()
                        st.rerun()
                    st.warning(f"No he podido transcribir la grabación. {error}")
            relato = st.text_area("Trayectoria", key="cv_w_relato", height=130, label_visibility="collapsed",
                                  placeholder="Estuve seis años de camarera de piso en hoteles de Madrid…")
            if st.button("Estructurar con IA", type="primary", disabled=len((relato or "").strip()) < 10):
                with st.spinner("Leyendo la trayectoria…"):
                    nuevas, formacion = modelo.estructura(ia.cliente(), relato)
                if not nuevas and not formacion:
                    st.warning("No he sacado nada en claro. Prueba a contarlo con más detalle, "
                               "o añade las experiencias a mano.")
                else:
                    for f in nuevas:
                        estado.anade_a_mano(**f)
                    for f in formacion:
                        cv["formacion"].append(motor.formacion(**f))
                    st.session_state["cv_aviso"] = (
                        f"Añadidas {len(nuevas)} experiencias y {len(formacion)} títulos. "
                        "Revisa cada ficha: la IA solo ordena lo que le has contado."
                    )
                    st.rerun()

    st.markdown('<div class="seccion">Experiencia laboral</div>', unsafe_allow_html=True)
    aviso = st.session_state.pop("cv_aviso", "")
    if aviso:
        st.info(aviso)

    if not exps:
        st.info("Todavía no hay ninguna experiencia. Usa una de las tres vías de arriba.")
    else:
        a, b = st.columns([3, 2], gap="medium")
        a.caption(
            "El nombre del puesto que viene del catálogo está pasado a singular. Cámbialo si "
            "no encaja: manda lo que escribas aquí. En el documento van en bloques por sector."
        )
        st.session_state["cv_auto_orden"] = b.toggle(
            "Ordenar solas por fechas", value=st.session_state["cv_auto_orden"],
            help="La más reciente arriba. Apágalo para colocarlas con las flechas.",
        )

        def mueve(i, salto):
            j = i + salto
            if 0 <= j < len(exps):
                exps[i], exps[j] = exps[j], exps[i]

        def quita(i):
            exps.pop(i)

        def pon_funciones(codigo):
            for e in exps:
                if e["codigo"] == codigo:
                    escrito = (st.session_state.get(f"cv_w_pue_{codigo}") or e["puesto"] or "").strip()
                    oficio = e["denominacion"] or escrito
                    if len(oficio.strip()) < 3:
                        st.session_state["cv_aviso"] = "Escribe primero el puesto y vuelve a pulsar."
                        return
                    texto = modelo.sugiere_funciones(ia.cliente(), oficio, e.get("motivo", ""))
                    if texto:
                        e["funciones"] = texto
                        st.session_state[f"cv_w_fun_{codigo}"] = texto
                    else:
                        st.session_state["cv_aviso"] = (
                            "No he podido proponer funciones para ese puesto. Comprueba que el "
                            "nombre del oficio es claro, o escríbelas a mano."
                        )
                    return

        try:
            fichas = st.container(key="fichas")
        except TypeError:
            fichas = st.container()
        with fichas:
            for i, e in enumerate(exps):
                k = e["codigo"]
                titulo = motor.titulo_experiencia(e)
                fechas = motor.periodo(e)
                partes = [titulo]
                if fechas:
                    partes.append(fechas)
                if e.get("sector"):
                    partes.append(e["sector"].strip())
                completa = bool(e["puesto"] or e["denominacion"]) and bool(e["desde"] or e["hasta"])
                with st.expander(("✓  " if completa else "○  ") + "  ·  ".join(partes),
                                 expanded=not completa):
                    arriba, abajo, apunte, fuera = st.columns([0.7, 0.7, 6, 1.4], gap="small")
                    arriba.button("↑", key=f"cv_w_sube_{k}", disabled=(i == 0),
                                  use_container_width=True, on_click=mueve, args=(i, -1))
                    abajo.button("↓", key=f"cv_w_baja_{k}", disabled=(i == len(exps) - 1),
                                 use_container_width=True, on_click=mueve, args=(i, 1))
                    apunte.markdown(
                        '<div style="padding-top:.45rem;font-size:.8rem;color:var(--suave)">'
                        + (f"Del catálogo SISPE: {esc(e['denominacion'])} · {esc(k)}" if e["denominacion"]
                           else "Añadida a mano")
                        + "</div>", unsafe_allow_html=True,
                    )
                    fuera.button("Quitar", key=f"cv_w_quita_{k}", use_container_width=True,
                                 on_click=quita, args=(i,))

                    c1, c2 = st.columns([3, 2], gap="medium")
                    e["puesto"] = c1.text_input("Puesto, tal como debe salir", value=e["puesto"],
                                                key=f"cv_w_pue_{k}", placeholder="Camarera de piso")
                    e["sector"] = c2.text_input(
                        "Sector", value=e["sector"], key=f"cv_w_sec_{k}",
                        placeholder="Hostelería, Comercio, Construcción…",
                        help="Agrupa las experiencias del mismo ramo bajo un rótulo. Solo sale "
                             "si hay dos o más del mismo sector.",
                    )
                    c3, c4, c5 = st.columns([1, 1, 3], gap="medium")
                    e["desde"] = c3.text_input("Desde", value=e["desde"], key=f"cv_w_des_{k}", placeholder="2016")
                    e["hasta"] = c4.text_input("Hasta", value=e["hasta"], key=f"cv_w_has_{k}",
                                               placeholder="2022 o «actualmente»")
                    e["contexto"] = c5.text_input(
                        "Empresa o tipo de empresa", value=e["contexto"], key=f"cv_w_ctx_{k}",
                        placeholder="Hoteles de 3 y 4 estrellas en Madrid capital",
                        help="Nombra las empresas o describe el tipo, útil cuando han sido muchas.",
                    )
                    etiqueta, varita = st.columns([6, 2], gap="small")
                    etiqueta.markdown('<div style="font-size:.8rem;padding-top:.4rem">Funciones</div>',
                                      unsafe_allow_html=True)
                    varita.button(
                        "🪄 Sugerir funciones", key=f"cv_w_ia_{k}", use_container_width=True,
                        on_click=pon_funciones, args=(k,),
                        help="La IA propone las funciones HABITUALES de este oficio, no las de "
                             "esta persona. Quita lo que no hiciera antes de darlo por bueno.",
                    )
                    st.session_state.setdefault(f"cv_w_fun_{k}", e["funciones"])
                    e["funciones"] = st.text_area(
                        "Funciones", key=f"cv_w_fun_{k}", height=80, label_visibility="collapsed",
                        placeholder="Qué hacía en ese puesto, en dos o tres líneas.",
                    )

        if not st.session_state["cv_auto_orden"]:
            st.button("Ordenar por fechas ahora", on_click=motor.ordena_por_fechas, args=(exps,))
        else:
            antes = [x["codigo"] for x in exps]
            motor.ordena_por_fechas(exps)
            if [x["codigo"] for x in exps] != antes:
                st.rerun()

    navegacion("Siguiente: formación →")

# ---------------------------------------------------------------------------
# 3 · Formación
# ---------------------------------------------------------------------------

elif n_paso == 2:
    st.markdown('<div class="seccion">Formación académica y complementaria</div>', unsafe_allow_html=True)
    forma = cv["formacion"]

    def quita_formacion(i):
        forma.pop(i)

    def anade_formacion():
        forma.append(motor.formacion())

    st.caption("Títulos oficiales, certificados de profesionalidad, cursos. Lo más reciente arriba.")
    for i, f in enumerate(forma):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([5, 4, 1.4, 1.2], gap="small")
            f["titulo"] = c1.text_input("Título", value=f["titulo"], key=f"cv_w_ft_{i}",
                                        placeholder="Certificado de profesionalidad de…")
            f["centro"] = c2.text_input("Centro", value=f["centro"], key=f"cv_w_fc_{i}",
                                        placeholder="Centro (horas), opcional")
            f["anio"] = c3.text_input("Año", value=f["anio"], key=f"cv_w_fa_{i}", placeholder="2019")
            c4.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
            c4.button("Quitar", key=f"cv_w_fq_{i}", use_container_width=True,
                      on_click=quita_formacion, args=(i,))
    st.button("+ Añadir formación", on_click=anade_formacion, type="primary" if not forma else "secondary")

    st.markdown('<div class="seccion">Otros datos de interés</div>', unsafe_allow_html=True)
    st.caption("Cada apartado es un punto del documento. Los vacíos no salen.")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        area("Idiomas", "idiomas", height=70, placeholder="Español nativo. Inglés básico.")
        area("Otros datos", "otros", height=70,
             placeholder="Un dato por línea: certificado de manipulador de alimentos, carné de carretillero…")
    with c2:
        area("Informática", "informatica", height=70,
             placeholder="Manejo de correo electrónico, Word y aplicaciones del móvil.")
        st.caption("El permiso de conducir y la disponibilidad se ponen en el paso 1 y salen aquí. "
                   "El objetivo profesional, que cierra el apartado, se redacta en el paso 4.")
    navegacion("Siguiente: documento →")

# ---------------------------------------------------------------------------
# 4 · Documento
# ---------------------------------------------------------------------------

else:
    izq, der = st.columns([3, 2], gap="large")

    with der:
        st.markdown('<div class="seccion" style="margin-top:.4rem">Objetivo profesional</div>',
                    unsafe_allow_html=True)
        st.caption("Cierra «Otros datos de interés»: hacia dónde se dirige la persona, en primera "
                   "persona y en tres líneas como máximo. Revísalo.")

        def redacta():
            texto = modelo.redacta_objetivo(ia.cliente(), cv)
            if texto:
                cv["objetivo"] = texto
                st.session_state["cv_w_objetivo"] = texto
            else:
                st.session_state["cv_aviso"] = (
                    "No he podido redactar el objetivo. Hace falta al menos una experiencia o un "
                    "título en los pasos anteriores, y conexión con la IA."
                )

        aviso = st.session_state.pop("cv_aviso", "")
        if aviso:
            st.warning(aviso)
        st.button("🪄 Redactar el objetivo con IA", on_click=redacta, use_container_width=True,
                  disabled=not (cv["experiencias"] or cv["formacion"]))
        area("Objetivo", "objetivo", height=110, label_visibility="collapsed",
             placeholder="Mi objetivo profesional está enfocado hacia trabajos en las áreas de…")

        st.markdown('<div class="seccion">Ajuste a una página</div>', unsafe_allow_html=True)
        decision = plantilla.decide(cv)
        factor = decision["factor"]
        hay_sectores = any((e.get("sector") or "").strip() for e in cv["experiencias"])
        n_exp = len(cv["experiencias"])
        n_dentro = n_exp - len(decision["omitidas"])
        notas = []
        if hay_sectores:
            notas.append("con bloques por sector" if decision["con_sectores"] else "sin rótulos de sector")
        if n_exp:
            notas.append(f"{n_dentro} de {n_exp} experiencias" if decision["omitidas"] else f"las {n_exp} experiencias")
        st.markdown(
            '<div class="estado-doc">'
            f'<div class="l">Tamaño de letra</div><div class="g">{round(factor * 100)} %</div>'
            f'<div class="n">{"Cabe con la letra del modelo." if factor >= 1 else "Reducida para que quepa en una página."}'
            + (f" {' · '.join(notas).capitalize()}." if notas else "") + "</div></div>",
            unsafe_allow_html=True,
        )
        if decision["omitidas"]:
            st.warning("Quedan fuera las más antiguas: " + "; ".join(f"**{t}**" for t in decision["omitidas"]) + ".")
        if n_exp > plantilla.MIN_EXPERIENCIAS:
            cv["todas_experiencias"] = st.checkbox(
                "Incluir todas aunque haya que reducir más la letra",
                value=cv.get("todas_experiencias", False), key="cv_w_todas",
            )

        st.markdown('<div class="seccion">Descargar</div>', unsafe_allow_html=True)
        vista = motor.texto_plano(cv)
        nombre_archivo = re.sub(r"[^\w]+", "_", cv["nombre"].strip(), flags=re.UNICODE).strip("_") or "curriculo"
        st.download_button(
            "Descargar en Word", motor.documento_docx(cv), file_name=f"CV_{nombre_archivo}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary", use_container_width=True, disabled=not vista,
            help="El documento definitivo, con la fuente exacta del modelo. Para retocarlo.",
        )
        st.download_button(
            "Descargar en PDF", motor.documento_pdf(cv), file_name=f"CV_{nombre_archivo}.pdf",
            mime="application/pdf", use_container_width=True, disabled=not vista,
            help="Para enviar o imprimir tal cual.",
        )
        st.button("Empezar un CV nuevo", use_container_width=True, on_click=empezar_de_nuevo,
                  help="Borra todos los datos de este currículo.")

    with izq:
        st.markdown('<div class="seccion" style="margin-top:.4rem">Vista previa</div>', unsafe_allow_html=True)
        if not vista:
            st.info("Aún no hay nada que mostrar. Rellena los pasos anteriores.")
        else:
            trozos, primera = [], True
            for tipo, datos in decision["bloques"]:
                if tipo == "nombre":
                    trozos.append(f'<div class="nombre">{esc(datos)}</div>')
                elif tipo == "contacto":
                    trozos.append(f'<div class="contacto">{esc(datos)}</div>')
                elif tipo == "cabecera":
                    trozos.append(f'<div class="cab{" primera" if primera else ""}">{esc(datos)}</div>')
                    primera = False
                elif tipo == "sector":
                    trozos.append(f'<div class="sector">{esc(datos)}</div>')
                elif tipo == "experiencia":
                    titulo, (a, fechas, c) = datos
                    cola = f" {esc(a)}<i>{esc(fechas)}</i>{esc(c)}" if fechas else ""
                    trozos.append(f'<div class="exp">•&nbsp; <b>{esc(titulo)}</b>{cola}</div>')
                elif tipo == "empresa":
                    trozos.append(f'<div class="emp">{esc(datos)}</div>')
                elif tipo == "funciones":
                    trozos.append(f'<div class="fun">{esc(datos)}</div>')
                elif tipo == "formacion":
                    titulo, centro, anio = datos
                    t = f"<b>{esc(titulo)}</b>" + (" –" if (centro or anio) else "")
                    if centro:
                        t += f" <i>{esc(centro)}{',' if anio else ''}</i>"
                    if anio:
                        t += f" {esc(anio)}."
                    trozos.append(f'<div class="form">•&nbsp; {t}</div>')
                elif tipo == "otros":
                    trozos.append(f'<div class="otro">·&nbsp; {esc(datos)}</div>')
            st.markdown(
                f'<div class="hoja" style="font-size:{round(0.62 * factor, 3)}rem">{"".join(trozos)}</div>',
                unsafe_allow_html=True,
            )
            st.caption("Aproximación en pantalla. El reparto exacto de líneas lo decide Word con Trebuchet MS.")

    navegacion()
