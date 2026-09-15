"""
Generador de informes de orientación: la pantalla.

Las tres fases del protocolo de orientación individual, una por pestaña:

    1 · Preparación   el CV anonimizado -> la lectura en prosa + el PDF de dos páginas
    2 · La sesión     el guion de lo que hay que preguntar y dónde se vuelca después
    3 · Cierre        el correo a la persona, con los entregables que van adjuntos

La fase 2 no la escribe la IA a propósito: lo que se decide en la sala sustituye
a cualquier hipótesis de la fase 1.

El CV tiene que llegar ya anonimizado —en la Comunidad de Madrid solo puede
subirse a Teams—, pero llega como llega: lo que se cuele se avisa y se tacha
antes de salir hacia la IA.

Claves de sesión con prefijo `inf_`; las de widgets, `inf_w_`.
"""

import streamlit as st

from comun import estilo, ia
from herramientas.cv import estado as cv_estado
from herramientas.informes import modelo, motor

estilo.aplica()
st.markdown("""
<style>
.st-key-cabecera{ margin-bottom:.6rem; }
.aviso-clave{
  font-size:.78rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
  color:#B15A2B; margin:.1rem 0 -.2rem;
}
</style>
""", unsafe_allow_html=True)

estilo.banda(
    "informes", "Generador de informes de orientación",
    "Prepara la sesión leyendo el currículo, recoge lo que solo se ve en la sala "
    "y cierra con el correo a la persona.",
)

st.session_state.setdefault("inf_lectura", "")
st.session_state.setdefault("inf_ficha", None)
st.session_state.setdefault("inf_correo", "")
st.session_state.setdefault("inf_archivo", None)

fase1, fase2, fase3 = st.tabs(["1 · Preparación", "2 · La sesión", "3 · Cierre"])


def _cliente():
    """El cliente de IA, o None con el aviso ya puesto en pantalla."""
    cli = ia.cliente()
    if cli is None:
        st.error(f"No hay clave {ia.AJUSTES['clave']} en los Secrets: sin IA no puedo redactar.")
    return cli


# ---------------------------------------------------------------------------
# FASE 1 — Preparación
# ---------------------------------------------------------------------------
with fase1:
    estilo.pasos([
        ("El currículo", "Anonimizado, pegado o arrastrado",
         "hecho" if (st.session_state.get("inf_w_cv") or "").strip() else "activo"),
        ("La lectura", "Trayectoria, tensión central e hipótesis",
         "hecho" if st.session_state["inf_lectura"] else ""),
        ("El documento", "Dos páginas A4 para llevar impresas",
         "hecho" if st.session_state["inf_ficha"] else ""),
    ])

    st.markdown('<div class="seccion">El currículo, sin datos personales</div>',
                unsafe_allow_html=True)
    st.caption(
        "Sin nombre, sin teléfono, sin correo, sin dirección y sin DNI o NIE. Las "
        "fechas, las empresas, las localidades y las titulaciones se quedan: de ahí "
        "sale el diagnóstico."
    )

    izq, der = st.columns([1, 1], gap="medium")
    with izq:
        with estilo.caja("soltar_cv"):
            subido = st.file_uploader("Currículo en .md o .txt", type=["md", "txt"],
                                      key="inf_w_archivo")
    with der:
        n_cv = len(cv_estado.experiencias())
        if st.button(
            f"Traerlo del generador de CV ({n_cv} exp.)" if n_cv else
            "Traerlo del generador de CV",
            use_container_width=True, disabled=not n_cv,
            help="Usa la trayectoria que hay en el generador de CV, sin el nombre "
                 "ni el contacto.",
        ):
            st.session_state["inf_w_cv"] = motor.trayectoria_desde_cv(cv_estado.cv())
            st.rerun()

        with st.expander("Cómo sacarlo de Teams (protección de datos)"):
            st.markdown(
                "Por protección de datos, en la Comunidad de Madrid **el CV de la "
                "persona solo puede subirse a Teams**, que es la única herramienta "
                "autorizada. Se le pide allí un volcado **sin datos identificativos** "
                "en Markdown, se guarda como `.md` y se arrastra aquí. Texto de "
                "encargo para pegar en Teams:"
            )
            st.code(
                "A partir del CV adjunto, vuelca la trayectoria en Markdown para "
                "orientación laboral. NO incluyas nombre, apellidos, fecha de nacimiento, "
                "DNI, teléfono, correo ni dirección. SÍ conserva los años de cada empleo, "
                "el tipo de empresa, la localidad y el país, las titulaciones con su año y "
                "los carnés: de ahí sale el diagnóstico. Devuelve solo el Markdown.",
                language=None, wrap_lines=True,
            )

    if subido is not None:
        huella = f"{subido.name}:{subido.size}"
        if st.session_state.get("inf_archivo") != huella:
            st.session_state["inf_archivo"] = huella
            st.session_state["inf_w_cv"] = subido.getvalue().decode("utf-8", errors="replace")
            st.rerun()

    cv = st.text_area(
        "Currículo", key="inf_w_cv", height=220, label_visibility="collapsed",
        placeholder="## Experiencia\n2016 – 2019  Reponedor en supermercado. Madrid.\n…",
    )

    _, hallazgos = motor.limpia_datos_personales(cv)
    if hallazgos:
        st.markdown('<div class="aviso-clave">Datos personales en el texto</div>',
                    unsafe_allow_html=True)
        st.warning(
            "He visto " + ", ".join(hallazgos) + ". Se trabaja igualmente: los "
            "identificadores se tachan antes de salir hacia la IA y no aparecerán en "
            "ninguna salida. Aun así, quítalos del original, porque el nombre propio "
            "no hay forma de detectarlo."
        )

    if st.button("Leer el CV y preparar la sesión", type="primary",
                 use_container_width=True, disabled=not cv.strip()):
        cli = _cliente()
        if cli is not None:
            limpio, _ = motor.limpia_datos_personales(cv)
            with st.spinner("Leyendo la trayectoria…"):
                try:
                    st.session_state["inf_lectura"] = modelo.lee_cv(cli, limpio)
                    st.session_state["inf_ficha"] = None
                except Exception as e:  # noqa: BLE001
                    st.error(f"No he podido leer el CV. {type(e).__name__}: {e}")

    lectura = st.session_state["inf_lectura"]
    if lectura:
        st.markdown('<div class="seccion">La lectura</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(lectura)
        st.caption(
            "Todo esto es hipótesis hasta la entrevista. La motivación no se deduce "
            "del CV: es lo primero que hay que leer en la sala."
        )

        st.markdown('<div class="seccion">El documento de dos páginas</div>',
                    unsafe_allow_html=True)
        st.caption(
            "Para llevarlo impreso y escribir encima: la trayectoria con sus huecos, "
            "la tensión central, la hipótesis de partida, las direcciones posibles, "
            "lo que hay que preguntar y el riesgo a evitar. Sin firma, sin logotipo "
            "y sin el nombre de la persona."
        )
        if st.button("Preparar el documento", use_container_width=True):
            cli = _cliente()
            if cli is not None:
                limpio, _ = motor.limpia_datos_personales(cv)
                with st.spinner("Montando las dos páginas…"):
                    try:
                        ficha = modelo.prepara(cli, limpio, lectura)
                    except Exception as e:  # noqa: BLE001
                        ficha = {}
                        st.error(f"No he podido montar el documento. {type(e).__name__}: {e}")
                if ficha.get("entradilla"):
                    st.session_state["inf_ficha"] = ficha
                elif ficha or not st.session_state["inf_ficha"]:
                    st.warning(
                        "La IA no ha devuelto un documento completo. Vuelve a pulsar: "
                        "suele salir a la segunda."
                    )

    ficha = st.session_state["inf_ficha"]
    if ficha:
        nombre = motor.nombre_archivo(ficha.get("rasgo"))
        try:
            pdf = motor.documento_pdf(ficha)
        except Exception as e:  # noqa: BLE001
            pdf = None
            st.error(f"No he podido generar el PDF. {type(e).__name__}: {e}")
        if pdf:
            st.download_button(
                f"Descargar {nombre}.pdf", pdf, file_name=f"{nombre}.pdf",
                mime="application/pdf", use_container_width=True, type="primary",
            )
            st.caption(
                "El archivo se nombra por el rasgo del perfil, nunca por la persona, y "
                "no lleva sufijo de versión: se sustituye entero."
            )
        with st.expander("Ver el contenido antes de imprimir"):
            st.json(ficha, expanded=False)

# ---------------------------------------------------------------------------
# FASE 2 — Lo que solo se ve en la sala
# ---------------------------------------------------------------------------
with fase2:
    st.markdown('<div class="seccion">Lo que el CV no puede decir</div>',
                unsafe_allow_html=True)
    st.caption(
        "Esto no lo escribe la IA. Se rellena después de la entrevista, y lo que se "
        "decidió en la sala sustituye a cualquier hipótesis de la fase 1. Los cuatro "
        "primeros bloques condicionan todo lo demás."
    )

    for clave, rotulo, condiciona, ayuda in motor.BLOQUES_SESION:
        st.text_area(
            f"{rotulo}  ·  condiciona todo lo demás" if condiciona else rotulo,
            key=f"inf_w_{clave}", height=76, placeholder=ayuda,
        )

    st.markdown('<div class="seccion">Motivación observada</div>', unsafe_allow_html=True)
    st.radio(
        "Motivación observada", motor.MOTIVACIONES, key="inf_w_motivacion",
        horizontal=True, label_visibility="collapsed",
        help="No se deduce del CV. Es lo que se ve en la sala.",
    )

    st.markdown('<div class="seccion">Objetivo elegido</div>', unsafe_allow_html=True)
    uno, dos = st.columns(2, gap="medium")
    uno.text_input("Principal", key="inf_w_objetivo1",
                   placeholder="Camarera de piso en hotel")
    dos.text_input("Secundario", key="inf_w_objetivo2",
                   placeholder="Limpiadora en colectividades")

    st.markdown('<div class="seccion">Calibración de la matriz</div>', unsafe_allow_html=True)
    st.caption(
        "Qué casilla se acabó asignando y si el caso encajaba de verdad en esa "
        "tipología. Sin esto, la matriz no mejora."
    )
    casilla, encaje = st.columns([1, 2], gap="medium")
    casilla.text_input("Casilla asignada", key="inf_w_casilla", placeholder="A3")
    encaje.radio("¿Encajaba en la tipología?", motor.ENCAJES, key="inf_w_encaje",
                 horizontal=True)

    if (st.session_state.get("inf_w_casilla") or "").strip():
        st.download_button(
            "Descargar la fila de calibración",
            motor.fila_calibracion({
                "casilla": st.session_state.get("inf_w_casilla"),
                "motivacion": st.session_state.get("inf_w_motivacion"),
                "encaje": st.session_state.get("inf_w_encaje"),
                "objetivo1": st.session_state.get("inf_w_objetivo1"),
            }),
            file_name="calibracion_matriz.csv", mime="text/csv",
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# FASE 3 — El correo de cierre
# ---------------------------------------------------------------------------
with fase3:
    st.markdown('<div class="seccion">Qué va adjunto</div>', unsafe_allow_html=True)
    for clave, rotulo, ayuda in motor.ENTREGABLES:
        st.checkbox(rotulo, key=f"inf_w_ent_{clave}", help=ayuda)
    st.text_input("Otro entregable", key="inf_w_ent_otros",
                  placeholder="Guion para presentarse en las empresas del polígono.")
    st.caption(
        "Los entregables van sin firmar: sin encabezado, sin pie y sin mención de la "
        "oficina ni de la Comunidad de Madrid. Material de uso genérico."
    )
    if motor.en_horario_laboral():
        st.info(
            "Estás en horario de oficina. Nada se publica sin haberlo leído en la "
            "fuente, y esta herramienta no lee fuentes: el correo sale sin enlaces y "
            "con aviso de comprobar lo que se nombre."
        )

    st.markdown('<div class="seccion">Quién firma</div>', unsafe_allow_html=True)
    quien, donde = st.columns(2, gap="medium")
    quien.text_input("Firma", key="inf_w_firma", placeholder="Álvaro, orientador laboral")
    donde.text_input("Canal de contacto", key="inf_w_canal",
                     placeholder="Respondiendo a este correo")

    objetivo = (st.session_state.get("inf_w_objetivo1") or "").strip()
    if not objetivo:
        st.caption(
            "Escribe el objetivo principal en la pestaña de la sesión: el correo se "
            "ordena alrededor de él."
        )

    if st.button("Redactar el correo", type="primary", use_container_width=True,
                 disabled=not objetivo):
        cli = _cliente()
        if cli is not None:
            adjuntos = [
                f"{rotulo}. {ayuda}" for clave, rotulo, ayuda in motor.ENTREGABLES
                if st.session_state.get(f"inf_w_ent_{clave}")
            ]
            extra = (st.session_state.get("inf_w_ent_otros") or "").strip()
            if extra:
                adjuntos.append(extra)
            datos = motor.texto_de_la_sesion({
                clave: st.session_state.get(f"inf_w_{clave}")
                for clave in [b[0] for b in motor.BLOQUES_SESION]
                + ["motivacion", "objetivo1", "objetivo2"]
            })
            with st.spinner("Redactando el correo…"):
                try:
                    st.session_state["inf_correo"] = modelo.escribe_correo(
                        cli, datos, adjuntos,
                        (st.session_state.get("inf_w_firma") or "").strip()
                        or "tu orientador laboral",
                        (st.session_state.get("inf_w_canal") or "").strip(),
                    )
                except Exception as e:  # noqa: BLE001
                    st.error(f"No he podido redactar el correo. {type(e).__name__}: {e}")

    correo = st.session_state["inf_correo"]
    if correo:
        st.markdown('<div class="seccion">El correo</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(correo)
        st.caption(
            "Selecciónalo y cópialo: al pegarlo en Outlook conserva las negritas y las "
            "listas. Léelo antes de enviarlo, que lo firmas tú."
        )
        with st.expander("Verlo en texto plano"):
            st.code(correo, language=None, wrap_lines=True)
