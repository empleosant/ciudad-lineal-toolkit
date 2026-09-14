"""
Generador de CV con IA en pocos pasos: la pantalla.

    1 · Datos        quién es (no se manda a la IA)
    2 · Experiencia  fichas: del codificador SISPE, a mano o estructuradas por la IA
    3 · Formación    títulos, idiomas, informática, otros
    4 · Documento    perfil redactado por la IA, vista previa y descarga en Word

La lógica está en `motor.py` (Python puro), las llamadas a la IA en
`modelo.py` y el currículo en curso en `estado.py`, que es por donde entran
las experiencias que manda el codificador.

Claves de sesión con prefijo `cv_`; las de widgets, `cv_w_`.
"""

import hashlib
import re

import streamlit as st

from comun import estilo, ia
from herramientas.cv import estado, modelo, motor, plantilla

estilo.aplica()
st.markdown("""
<style>
/* Aire propio del generador: contenido más estrecho que el codificador,
   porque son formularios y leen mejor sin estirarse; hueco entre bloques
   y margen inferior para que el último botón no quede pegado al borde. */
.block-container{ max-width:1040px; padding-bottom:3.5rem !important; }
.st-key-cv_paso{ margin:.9rem 0 .6rem; }
.seccion{ margin-top:1.4rem; }
.st-key-cabecera{ margin-bottom:.4rem; }
div[data-testid="stExpander"]{ margin-top:.5rem; }
.st-key-descargas{ margin-top:.6rem; }
</style>
""", unsafe_allow_html=True)
cv = estado.cv()

PASOS = ["1 · Datos", "2 · Experiencia", "3 · Formación", "4 · Documento"]
st.session_state.setdefault("cv_paso", PASOS[0])


def ir_a(paso):
    st.session_state["cv_paso"] = PASOS[paso]


def empezar_de_nuevo():
    estado.vacia()
    for k in [k for k in st.session_state if k.startswith("cv_w_")]:
        del st.session_state[k]
    st.session_state["cv_paso"] = PASOS[0]


def campo(etiqueta, clave, **k):
    """Un text_input ligado a una clave del currículo."""
    cv[clave] = st.text_input(etiqueta, value=cv[clave], key=f"cv_w_{clave}", **k)


def area(etiqueta, clave, **k):
    cv[clave] = st.text_area(etiqueta, value=cv[clave], key=f"cv_w_{clave}", **k)


# ---------------------------------------------------------------------------
# Cabecera y selector de paso
# ---------------------------------------------------------------------------

estilo.banda(
    "cv", "Generador de CV",
    "Datos, experiencia, formación y documento. La IA ordena, sugiere y redacta; tú revisas.",
)

if st.session_state.get("cv_paso") not in PASOS:
    st.session_state["cv_paso"] = PASOS[0]
paso = st.segmented_control(
    "Paso", PASOS, key="cv_paso", label_visibility="collapsed",
) or PASOS[0]
n_paso = PASOS.index(paso)


def navegacion():
    st.markdown('<div class="separa"></div>', unsafe_allow_html=True)
    izq, _, der = st.columns([2, 5, 2], gap="small")
    if n_paso > 0:
        izq.button("← Anterior", use_container_width=True, on_click=ir_a, args=(n_paso - 1,))
    if n_paso < len(PASOS) - 1:
        der.button("Siguiente →", type="primary", use_container_width=True,
                   on_click=ir_a, args=(n_paso + 1,))


# ---------------------------------------------------------------------------
# 1 · Datos
# ---------------------------------------------------------------------------

if n_paso == 0:
    st.markdown('<div class="seccion">Datos de contacto</div>', unsafe_allow_html=True)
    st.caption("Estos datos van solo al documento. Nunca se mandan a la IA.")
    campo("Nombre y apellidos", "nombre")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        campo("Teléfono", "telefono")
        campo("Localidad", "localidad", placeholder="Madrid (Ciudad Lineal)")
    with c2:
        campo("Correo electrónico", "email")
        campo("Permiso de conducir y vehículo", "permiso",
              placeholder="Carné B, vehículo propio", help="Opcional.")
    campo("Disponibilidad", "disponibilidad",
          placeholder="Inmediata, jornada completa o parcial, turnos…", help="Opcional.")
    navegacion()

# ---------------------------------------------------------------------------
# 2 · Experiencia
# ---------------------------------------------------------------------------

elif n_paso == 1:
    exps = estado.experiencias()

    with st.expander("Contar la trayectoria en texto libre y que la IA la ordene"):
        st.caption(
            "Escribe lo que cuente la persona, tal cual: «Estuve seis años de "
            "camarera de piso en hoteles de Madrid, luego dos en un supermercado "
            "reponiendo…», o grábalo con el micrófono. La IA lo convierte en "
            "fichas, que después revisas. Sin nombre, teléfono ni ningún dato "
            "identificativo."
        )
        grabacion = st.audio_input(
            "O cuéntalo por el micrófono", key="cv_w_audio",
            help="Pulsa el micrófono, habla y vuelve a pulsar para parar. Lo que se "
                 "diga se transcribe y se añade al cuadro de texto. La grabación "
                 "sale a la IA para transcribirla: no digáis nombre ni teléfono.",
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

        relato = st.text_area("Trayectoria", key="cv_w_relato", height=140,
                              label_visibility="collapsed")
        if st.button("Estructurar con IA", type="primary", disabled=len(relato.strip()) < 10):
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
                    f"Añadidas {len(nuevas)} experiencias y {len(formacion)} "
                    "títulos. Revisa cada ficha: la IA solo ordena lo que le has contado."
                )
                st.rerun()

    st.markdown('<div class="seccion">Experiencia laboral</div>', unsafe_allow_html=True)
    aviso = st.session_state.pop("cv_aviso", "")
    if aviso:
        st.info(aviso)

    if not exps:
        with st.container(border=True):
            st.markdown("**Todavía no hay ninguna experiencia**")
            st.caption(
                "Puedes traerlas del Codificador SISPE, buscando la ocupación y "
                "pulsando el botón rojo que sale bajo las tarjetas; contarlas en "
                "texto libre ahí arriba; o escribirlas aquí a mano."
            )
            st.button("Añadir una experiencia a mano", type="primary",
                      use_container_width=True, on_click=estado.anade_a_mano)
    else:
        st.caption(
            "El nombre del puesto que viene del catálogo está pasado a singular y "
            "minúscula. Cámbialo si no encaja: manda lo que escribas aquí."
        )
        st.session_state["cv_auto_orden"] = st.toggle(
            "Ordenar solo por fechas", value=st.session_state["cv_auto_orden"],
            help="En cuanto escribas los años, el más reciente sube al primer "
                 "puesto. Apágalo si quieres colocarlos tú con las flechas.",
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
                            "No he podido proponer funciones para ese puesto. Comprueba "
                            "que el nombre del oficio es claro, o escríbelas a mano."
                        )
                    return

        for i, e in enumerate(exps):
            k = e["codigo"]
            with st.container(border=True):
                arriba, abajo, titulo, fuera = st.columns([0.8, 0.8, 7, 1.2], gap="small")
                arriba.button("↑", key=f"cv_w_sube_{k}", disabled=(i == 0),
                              use_container_width=True, on_click=mueve, args=(i, -1))
                abajo.button("↓", key=f"cv_w_baja_{k}", disabled=(i == len(exps) - 1),
                             use_container_width=True, on_click=mueve, args=(i, 1))
                apunte = (f"{k} · {e['denominacion'][:40]}" if e["denominacion"]
                          else "Sin código SISPE")
                titulo.markdown(
                    f"**{motor.titulo_experiencia(e)}**"
                    f" &nbsp;&nbsp;<span style='color:#888;font-size:.8rem'>{apunte}</span>",
                    unsafe_allow_html=True,
                )
                fuera.button("Quitar", key=f"cv_w_quita_{k}", use_container_width=True,
                             on_click=quita, args=(i,))

                c1, c2 = st.columns(2, gap="medium")
                e["sector"] = c1.text_input(
                    "Sector", value=e["sector"], key=f"cv_w_sec_{k}",
                    placeholder="Construcción, Hostelería, Conducción profesional…",
                    help="Opcional. Solo aparece en el currículo si agrupa dos o "
                         "más experiencias del mismo ramo.",
                )
                e["puesto"] = c2.text_input(
                    "Puesto, tal como quieres que salga", value=e["puesto"], key=f"cv_w_pue_{k}",
                )
                c3, c4 = st.columns(2, gap="medium")
                e["desde"] = c3.text_input("Desde", value=e["desde"], key=f"cv_w_des_{k}",
                                           placeholder="2016")
                e["hasta"] = c4.text_input("Hasta", value=e["hasta"], key=f"cv_w_has_{k}",
                                           placeholder="2022, o «actualmente»")
                e["contexto"] = st.text_input(
                    "Dónde", value=e["contexto"], key=f"cv_w_ctx_{k}",
                    placeholder="Empresas de construcción y obras públicas en Madrid capital.",
                    help="Puedes nombrar las empresas o describir el tipo de empresa, "
                         "que es útil cuando han sido muchas o no se recuerdan los nombres.",
                )
                etiqueta, varita = st.columns([6, 2], gap="small")
                etiqueta.markdown('<div style="font-size:.8rem;padding-top:.4rem">Funciones</div>',
                                  unsafe_allow_html=True)
                varita.button(
                    "🪄 Sugerir funciones", key=f"cv_w_ia_{k}", use_container_width=True,
                    on_click=pon_funciones, args=(k,),
                    help="La IA propone las funciones HABITUALES de este oficio, no las "
                         "de esta persona. Quita lo que no hiciera antes de darlo por bueno.",
                )
                st.session_state.setdefault(f"cv_w_fun_{k}", e["funciones"])
                e["funciones"] = st.text_area(
                    "Funciones", key=f"cv_w_fun_{k}", height=90, label_visibility="collapsed",
                    placeholder="Qué hacía en ese puesto, en dos o tres líneas.",
                )

        izq, der = st.columns(2, gap="small")
        izq.button("Añadir otra experiencia a mano", use_container_width=True,
                   on_click=estado.anade_a_mano)
        if not st.session_state["cv_auto_orden"]:
            der.button("Ordenar por fechas", use_container_width=True,
                       on_click=motor.ordena_por_fechas, args=(exps,))
        else:
            der.caption("Se ordenan solas por fecha, de la más reciente a la más antigua.")

        # Se ordena DESPUÉS de leer los campos: así, en cuanto escribes un año,
        # la ficha sube o baja sola en el siguiente refresco.
        if st.session_state["cv_auto_orden"]:
            antes = [x["codigo"] for x in exps]
            motor.ordena_por_fechas(exps)
            if [x["codigo"] for x in exps] != antes:
                st.rerun()

    navegacion()

# ---------------------------------------------------------------------------
# 3 · Formación
# ---------------------------------------------------------------------------

elif n_paso == 2:
    st.markdown('<div class="seccion">Formación</div>', unsafe_allow_html=True)
    forma = cv["formacion"]

    def quita_formacion(i):
        forma.pop(i)

    def anade_formacion():
        forma.append(motor.formacion())

    if not forma:
        st.caption("Títulos oficiales, certificados de profesionalidad, cursos. Lo más reciente arriba.")
    for i, f in enumerate(forma):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([5, 4, 1.5, 1.2], gap="small")
            f["titulo"] = c1.text_input("Título", value=f["titulo"], key=f"cv_w_ft_{i}",
                                        placeholder="Certificado de profesionalidad de…")
            f["centro"] = c2.text_input("Centro", value=f["centro"], key=f"cv_w_fc_{i}",
                                        placeholder="Opcional")
            f["anio"] = c3.text_input("Año", value=f["anio"], key=f"cv_w_fa_{i}", placeholder="2019")
            c4.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
            c4.button("Quitar", key=f"cv_w_fq_{i}", use_container_width=True,
                      on_click=quita_formacion, args=(i,))
    st.button("Añadir formación", use_container_width=True, on_click=anade_formacion,
              type="primary" if not forma else "secondary")

    st.markdown('<div class="seccion">Otros apartados</div>', unsafe_allow_html=True)
    st.caption("Los que queden vacíos no salen en el documento.")
    area("Idiomas", "idiomas", height=70, placeholder="Español nativo. Inglés básico.")
    area("Informática", "informatica", height=70,
         placeholder="Manejo de correo electrónico, Word y aplicaciones del móvil.")
    area("Otros datos", "otros", height=70,
         placeholder="Certificado de manipulador de alimentos. Carné de carretillero.")
    navegacion()

# ---------------------------------------------------------------------------
# 4 · Documento
# ---------------------------------------------------------------------------

else:
    st.markdown('<div class="seccion">Perfil profesional</div>', unsafe_allow_html=True)
    st.caption(
        "Tres o cuatro líneas que abren el currículo. La IA lo redacta con lo que "
        "hay en los pasos anteriores, sin el nombre ni el contacto. Revísalo. "
        "El modelo de la oficina no lleva perfil: si lo dejas vacío, no sale."
    )

    def redacta():
        texto = modelo.redacta_perfil(ia.cliente(), cv)
        if texto:
            cv["perfil"] = texto
            st.session_state["cv_w_perfil"] = texto
        else:
            st.session_state["cv_aviso"] = (
                "No he podido redactar el perfil. Hace falta al menos una experiencia "
                "o un título en los pasos anteriores, y conexión con la IA."
            )

    aviso = st.session_state.pop("cv_aviso", "")
    if aviso:
        st.warning(aviso)
    st.button("🪄 Redactar el perfil con IA", on_click=redacta,
              disabled=not (cv["experiencias"] or cv["formacion"]))
    area("Perfil", "perfil", height=110, label_visibility="collapsed")

    st.markdown('<div class="seccion">Cómo queda</div>', unsafe_allow_html=True)
    vista = motor.texto_plano(cv)
    if vista:
        st.code(vista, language=None)
        _, factor, con_sectores = plantilla.decide(cv)
        hay_sectores = any((e.get("sector") or "").strip() for e in cv["experiencias"])
        if factor >= 1.0:
            ajuste = "Cabe en una página con el tamaño de letra del modelo."
        else:
            ajuste = f"Para que quepa en una página, la letra va al {round(factor * 100)} % del modelo."
        if hay_sectores and not con_sectores:
            ajuste += " Se han quitado los rótulos de sector para ganar espacio."
        st.caption(
            "El documento sigue el modelo de CV de la oficina: misma estructura, fuentes y "
            f"colores, siempre en una página. {ajuste}"
        )
    else:
        st.info("Aún no hay nada que mostrar. Rellena los pasos anteriores.")

    nombre_archivo = re.sub(r"[^\w]+", "_", cv["nombre"].strip(), flags=re.UNICODE).strip("_") or "curriculo"
    try:
        descargas = st.container(key="descargas")
    except TypeError:
        descargas = st.container()
    with descargas:
        word, pdf, nuevo = st.columns([1.2, 1.2, 1], gap="small")
        word.download_button(
            "Descargar en Word", motor.documento_docx(cv),
            file_name=f"CV_{nombre_archivo}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary", use_container_width=True, disabled=not vista,
            help="Para retocarlo después.",
        )
        pdf.download_button(
            "Descargar en PDF", motor.documento_pdf(cv),
            file_name=f"CV_{nombre_archivo}.pdf", mime="application/pdf",
            type="primary", use_container_width=True, disabled=not vista,
            help="Para enviarlo o imprimirlo tal cual.",
        )
        nuevo.button("Empezar un CV nuevo", use_container_width=True, on_click=empezar_de_nuevo,
                     help="Borra todos los datos de este currículo.")
    navegacion()
