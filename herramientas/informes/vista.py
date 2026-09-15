"""
Generador de informes de orientación: la pantalla.

El flujo de una orientación individual, en tres pestañas:

    1 · Preparación   el CV anonimizado -> la lectura en prosa + el PDF de dos páginas
    2 · La cita       lo que se habló, en prosa o dictado, y lo que se acordó
    3 · Cierre        el cuerpo del correo para la persona, listo para pegar en Outlook

Entre la preparación y la cita pasan días y Streamlit se olvida de todo al
cerrar la pestaña: por eso el expediente, que se descarga y se vuelve a subir.
Es lo que reproduce el hilo con el que se venía trabajando —una conversación
por persona, el contexto acumulándose—, y sin él el correo de cierre no sabría
de dónde viene.

El CV tiene que llegar ya anonimizado —en la Comunidad de Madrid solo puede
subirse a Teams—, pero llega como llega: lo que se cuele se avisa y se tacha
antes de salir hacia la IA. Lo mismo con las notas de la cita.

Claves de sesión con prefijo `inf_`; las de widgets, `inf_w_`.
"""

import hashlib

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
    "Prepara la cita leyendo el currículo, recoge lo que solo se ve en la sala "
    "y cierra con el correo a la persona.",
)

st.session_state.setdefault("inf_lectura", "")
st.session_state.setdefault("inf_ficha", None)
st.session_state.setdefault("inf_correo", "")
st.session_state.setdefault("inf_archivo", None)

# Lo que viene de un expediente subido se aplica AQUÍ, antes de que exista
# ningún widget: Streamlit no deja tocar la clave de un widget ya dibujado.
_pendiente = st.session_state.pop("inf_cargar", None)
if _pendiente:
    for _clave, _valor in _pendiente.items():
        st.session_state[_clave] = _valor

# El expediente: del archivo a la sesión y al revés.
DEL_ARCHIVO = {
    "cv": "inf_w_cv", "notas": "inf_w_notas", "objetivo1": "inf_w_objetivo1",
    "objetivo2": "inf_w_objetivo2", "zona": "inf_w_zona", "adjuntos": "inf_w_adjuntos",
    "firma": "inf_w_firma", "canal": "inf_w_canal", "casilla": "inf_w_casilla",
    "motivacion": "inf_w_motivacion", "encaje": "inf_w_encaje",
    "lectura": "inf_lectura", "ficha": "inf_ficha",
}


def _cliente():
    """El cliente de IA, o None con el aviso ya puesto en pantalla."""
    cli = ia.cliente()
    if cli is None:
        st.error(f"No hay clave {ia.AJUSTES['clave']} en los Secrets: sin IA no puedo redactar.")
    return cli


def _estado():
    """Lo que hay ahora mismo, con los nombres del expediente."""
    datos = {archivo: st.session_state.get(sesion)
             for archivo, sesion in DEL_ARCHIVO.items()}
    return {k: v for k, v in datos.items() if v}


# ---------------------------------------------------------------------------
# El expediente, encima de todo: vale para las tres fases
# ---------------------------------------------------------------------------
with st.expander("Expediente · guardar para otro día o recuperar lo guardado"):
    st.caption(
        "Entre preparar la cita y tenerla pasan días, y al cerrar la pestaña se "
        "pierde todo. Descarga el expediente al terminar la preparación y súbelo el "
        "día de la cita: vuelve el currículo, la lectura y lo que llevaras anotado. "
        "El archivo se queda en tu equipo; aquí no se guarda nada de nadie."
    )
    guarda, recupera = st.columns(2, gap="medium")
    with guarda:
        _actual = _estado()
        _rasgo = (st.session_state.get("inf_ficha") or {}).get("rasgo")
        _nombre = motor.nombre_expediente(_rasgo)
        st.download_button(
            f"Guardar {_nombre}.json", motor.expediente(_actual),
            file_name=f"{_nombre}.json", mime="application/json",
            use_container_width=True, disabled=not _actual,
            help="Se nombra por el rasgo del perfil, nunca por la persona.",
        )
    with recupera:
        _subido = st.file_uploader("Expediente .json", type=["json"],
                                   key="inf_w_expediente", label_visibility="collapsed")
        if _subido is not None:
            _huella = f"{_subido.name}:{_subido.size}"
            if st.session_state.get("inf_expediente") != _huella:
                st.session_state["inf_expediente"] = _huella
                _datos, _error = motor.lee_expediente(_subido.getvalue())
                if _error:
                    st.error(_error)
                else:
                    # lee_expediente ya ha descartado lo que no era de su tipo.
                    st.session_state["inf_cargar"] = {
                        DEL_ARCHIVO[c]: v for c, v in _datos.items() if c in DEL_ARCHIVO
                    }
                    st.session_state["inf_correo"] = ""
                    st.rerun()

fase1, fase2, fase3 = st.tabs(["1 · Preparación", "2 · La cita", "3 · Cierre"])


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

        with st.expander("Cómo sacarlo de Teams o de Copilot (protección de datos)"):
            st.markdown(
                "Por protección de datos, en la Comunidad de Madrid **el CV de la "
                "persona solo puede subirse a Teams**, que es la única herramienta "
                "autorizada. Se le pide allí un volcado **sin datos identificativos** "
                "en Markdown, se guarda como `.md` y se arrastra aquí. Texto de "
                "encargo para pegar:"
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

    if st.button("Leer el CV y preparar la cita", type="primary",
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
                "no lleva sufijo de versión: se sustituye entero. **Guarda también el "
                "expediente, ahí arriba**, para no perder esto hasta el día de la cita."
            )
        with st.expander("Ver el contenido antes de imprimir"):
            st.json(ficha, expanded=False)

# ---------------------------------------------------------------------------
# FASE 2 — Lo que se habló en la cita
# ---------------------------------------------------------------------------
with fase2:
    st.markdown('<div class="seccion">Qué hablasteis</div>', unsafe_allow_html=True)
    st.caption(
        "En bruto, como se lo contarías a un compañero: no hace falta ordenarlo. "
        "Lo que se decidió aquí manda sobre cualquier hipótesis de la preparación. "
        "Conviene que salga la situación documental y económica, los condicionantes "
        "duros, la disponibilidad real, las herramientas que maneja y cómo ha "
        "buscado hasta ahora — que es el guion de la §4 del documento impreso."
    )

    grabacion = st.audio_input(
        "Grabar con el micrófono", key="inf_w_audio",
        help="Pulsa el micrófono, habla y vuelve a pulsar para parar. Se transcribe y "
             "se añade al cuadro de texto.",
    )
    if grabacion is not None:
        huella_audio = hashlib.md5(grabacion.getvalue()).hexdigest()
        if st.session_state.get("inf_audio") != huella_audio:
            st.session_state["inf_audio"] = huella_audio
            cli = ia.cliente()
            if cli is None:
                st.error(f"No hay clave {ia.AJUSTES['clave']} en los Secrets: "
                         "no puedo transcribir.")
            else:
                with st.spinner("Transcribiendo…"):
                    try:
                        dicho = ia.transcribe(cli, grabacion.getvalue(),
                                              grabacion.type or "audio/wav")
                    except Exception as e:  # noqa: BLE001
                        dicho = ""
                        st.error(f"No he podido transcribir. {type(e).__name__}: {e}")
                if dicho:
                    previo = (st.session_state.get("inf_w_notas") or "").rstrip()
                    st.session_state["inf_w_notas"] = f"{previo}\n{dicho}".strip()
                    st.rerun()

    notas = st.text_area(
        "Notas de la cita", key="inf_w_notas", height=220, label_visibility="collapsed",
        placeholder="Tiene permiso de trabajo y la nacionalidad en trámite. El subsidio "
                    "se le acaba en marzo. Cuida de su madre por las mañanas, así que "
                    "solo puede tardes. Dice que de comercio ya se olvida…",
    )

    _, hallazgos_notas = motor.limpia_datos_personales(notas)
    if hallazgos_notas:
        st.markdown('<div class="aviso-clave">Datos personales en las notas</div>',
                    unsafe_allow_html=True)
        st.warning(
            "He visto " + ", ".join(hallazgos_notas) + " en lo que has escrito. Se "
            "tacha antes de salir hacia la IA, pero el nombre propio no hay forma de "
            "detectarlo: no lo escribas."
        )

    st.markdown('<div class="seccion">Lo que se acordó</div>', unsafe_allow_html=True)
    uno, dos = st.columns(2, gap="medium")
    uno.text_input("Objetivo principal", key="inf_w_objetivo1",
                   placeholder="Camarera de piso en hotel")
    dos.text_input("Objetivo secundario", key="inf_w_objetivo2",
                   placeholder="Limpiadora en colectividades")
    st.text_input(
        "Dónde busca empleo y hasta dónde se mueve", key="inf_w_zona",
        placeholder="Vive en Ciudad Lineal. Se mueve por toda Madrid capital en metro; "
                    "no quiere pasar de 45 minutos.",
        help="Decide qué empresas tienen sentido proponerle. Cuanto más concreto, mejor.",
    )

    st.markdown('<div class="seccion">Calibración de la matriz</div>', unsafe_allow_html=True)
    st.caption(
        "Qué casilla se acabó asignando y si el caso encajaba de verdad en esa "
        "tipología. Sin esto, la matriz no mejora."
    )
    casilla, motivacion = st.columns([1, 2], gap="medium")
    casilla.text_input("Casilla asignada", key="inf_w_casilla", placeholder="A3")
    motivacion.radio("Motivación observada", motor.MOTIVACIONES, key="inf_w_motivacion",
                     horizontal=True)
    st.radio("¿Encajaba en la tipología?", motor.ENCAJES, key="inf_w_encaje",
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
    st.markdown('<div class="seccion">Quién firma</div>', unsafe_allow_html=True)
    quien, donde = st.columns(2, gap="medium")
    quien.text_input("Firma", key="inf_w_firma", placeholder="Álvaro, orientador laboral")
    donde.text_input("Canal de contacto", key="inf_w_canal",
                     placeholder="Respondiendo a este correo")
    st.text_input(
        "Qué va adjunto, si va algo", key="inf_w_adjuntos",
        placeholder="El currículo reescrito para hostelería.",
        help="Lo que adjuntes a mano en Outlook. El correo lo mencionará; si lo dejas "
             "vacío, no habla de adjuntos.",
    )
    st.caption(
        "Lo que adjuntes va sin firmar: sin encabezado, sin pie y sin mención de la "
        "oficina ni de la Comunidad de Madrid. Material de uso genérico."
    )

    objetivo = (st.session_state.get("inf_w_objetivo1") or "").strip()
    if not objetivo:
        st.caption(
            "Escribe el objetivo principal en la pestaña de la cita: el correo se "
            "ordena alrededor de él."
        )

    if st.button("Redactar el correo", type="primary", use_container_width=True,
                 disabled=not objetivo):
        cli = _cliente()
        if cli is not None:
            cv_limpio, _ = motor.limpia_datos_personales(
                st.session_state.get("inf_w_cv") or "")
            notas_limpias, _ = motor.limpia_datos_personales(
                st.session_state.get("inf_w_notas") or "")
            acordado = motor.lo_acordado({
                clave: st.session_state.get(f"inf_w_{clave}")
                for clave in ("objetivo1", "objetivo2", "zona", "adjuntos", "motivacion")
            })
            with st.spinner("Buscando empresas y redactando…"):
                try:
                    st.session_state["inf_correo"] = modelo.escribe_correo(
                        cli, cv_limpio, st.session_state.get("inf_lectura") or "",
                        notas_limpias, acordado,
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
        st.warning(
            "**Las empresas las propone la IA de memoria, y puede equivocarse de nombre "
            "o proponer alguna que ya no exista.** Repásalas antes de enviar: cada una "
            "lleva su tipo y su zona, así que lo que no cuadre se sustituye sin "
            "rehacer el correo."
        )
        st.caption(
            "Selecciónalo y cópialo: al pegarlo en Outlook conserva las negritas y las "
            "listas. Léelo antes de enviarlo, que lo firmas tú."
        )
        with st.expander("Verlo en texto plano"):
            st.code(correo, language=None, wrap_lines=True)
