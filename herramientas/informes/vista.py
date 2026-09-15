"""
Generador de informes de orientación: la pantalla.

El flujo de una orientación individual, en tres pestañas:

    1 · Preparación   el CV anonimizado -> el PDF de dos páginas + la lectura
    2 · La cita       lo que se habló, en prosa o dictado, y lo que se acordó
    3 · Cierre        el cuerpo del correo para la persona, listo para pegar en Outlook

REGLA DE LA PANTALLA: lo obligatorio, a la vista; lo opcional, plegado. Esto no
lo usa solo quien lo montó: la calibración de la matriz, la firma o el
expediente son cosas que no hacen falta para el trabajo de un día corriente, y
teniéndolas delante la herramienta parece mucho más difícil de lo que es. Quien
las necesita abre su desplegable.

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
import json
import re
import time

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

try:
    MANTENIMIENTO = st.query_params.get("mantenimiento") == "1"
except Exception:  # noqa: BLE001
    MANTENIMIENTO = False

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
    "referencia": "inf_w_referencia", "observaciones": "inf_w_observaciones",
    "lectura": "inf_lectura", "ficha": "inf_ficha",
}

CASILLAS = (motor.SIN_CASILLA,) + motor.CASILLAS_ROTULO


def _cliente():
    """El cliente de IA, o None con el aviso ya puesto en pantalla."""
    cli = ia.cliente()
    if cli is None:
        st.error(f"No hay clave {ia.AJUSTES['clave']} en los Secrets: sin IA no puedo redactar.")
    return cli


class _cronometra:
    """Apunta quién ha contestado y cuánto ha tardado, para el chip.

    Cada fase tiene su marca: las llamadas son de tamaños muy distintos y un
    único cronómetro no diría nada. El modelo se lee DESPUÉS de la llamada, que
    es cuando `ia` sabe cuál de la cadena de relevo acabó respondiendo.
    """

    def __init__(self, fase):
        self.clave = f"inf_uso_{fase}"

    def __enter__(self):
        st.session_state.pop(self.clave, None)
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, tipo, *_):
        if tipo is None:
            st.session_state[self.clave] = (ia.ultimo_uso()[1],
                                            time.perf_counter() - self.t0)
        return False


def _chip(fase):
    """El chip de una fase, si esa fase se ha llegado a ejecutar."""
    uso = st.session_state.get(f"inf_uso_{fase}")
    if uso:
        estilo.chip_ia(*uso)


def _estado():
    """Lo que hay ahora mismo, con los nombres del expediente."""
    datos = {archivo: st.session_state.get(sesion)
             for archivo, sesion in DEL_ARCHIVO.items()}
    return {k: v for k, v in datos.items() if v}


# ---------------------------------------------------------------------------
# Lo de arriba: cómo funciona y el expediente. Los dos, plegados.
# ---------------------------------------------------------------------------
with st.expander("Cómo funciona esto"):
    st.markdown(
        "**1 · Antes de la cita.** Pega el currículo de la persona, sin nombre ni "
        "teléfono, y pulsa el botón. Sale un PDF de dos páginas para imprimir y "
        "llevártelo a la entrevista: la trayectoria, la hipótesis de partida y la "
        "lista de lo que hay que preguntarle.\n\n"
        "**2 · Después de la cita.** En la segunda pestaña cuentas qué hablasteis, "
        "escribiendo o por el micrófono, y apuntas el objetivo que acordasteis y por "
        "dónde busca empleo.\n\n"
        "**3 · Para cerrar.** En la tercera sale el correo para la persona, con "
        "empresas a las que presentarse. Se copia y se pega en Outlook.\n\n"
        "Si la cita es otro día, **guarda el expediente** ahí abajo al terminar el "
        "paso 1 y súbelo cuando vuelvas: si no, hay que empezar de nuevo."
    )

with st.expander("Guardar para otro día, o recuperar lo guardado"):
    st.caption(
        "El archivo se queda en tu equipo. Aquí no se guarda nada de nadie."
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
                    for _fase in ("lectura", "ficha", "correo"):
                        st.session_state.pop(f"inf_uso_{_fase}", None)
                    st.rerun()

fase1, fase2, fase3 = st.tabs(["1 · Preparación", "2 · La cita", "3 · Cierre"])


# ---------------------------------------------------------------------------
# FASE 1 — Preparación
# ---------------------------------------------------------------------------
with fase1:
    estilo.pasos([
        ("El currículo", "Pégalo o arrástralo",
         "hecho" if (st.session_state.get("inf_w_cv") or "").strip() else "activo"),
        ("El documento", "Dos páginas para imprimir",
         "hecho" if st.session_state["inf_ficha"] else ""),
        ("La cita", "Se cuenta en la pestaña 2",
         "hecho" if (st.session_state.get("inf_w_notas") or "").strip() else ""),
    ])

    st.markdown('<div class="seccion">El currículo, sin datos personales</div>',
                unsafe_allow_html=True)
    st.caption("Sin nombre, teléfono, correo, dirección ni DNI. Las fechas, las "
               "empresas y las localidades sí: de ahí sale el diagnóstico.")

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

        with st.expander("Cómo sacarlo de Teams o de Copilot"):
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
            "He visto " + ", ".join(hallazgos) + ". Se tacha antes de salir hacia la "
            "IA, pero el nombre propio no hay forma de detectarlo: quítalo del original."
        )

    # Un solo botón para las dos llamadas. Eran dos —leer y luego montar— y el
    # paso intermedio no decidía nada: quien prepara una cita quiere el papel.
    if st.button("Preparar la cita", type="primary", use_container_width=True,
                 disabled=not cv.strip()):
        cli = _cliente()
        if cli is not None:
            limpio, _ = motor.limpia_datos_personales(cv)
            st.session_state["inf_ficha"] = None
            st.session_state.pop("inf_uso_ficha", None)
            try:
                with st.spinner("Leyendo la trayectoria…"):
                    with _cronometra("lectura"):
                        st.session_state["inf_lectura"] = modelo.lee_cv(cli, limpio)
                with st.spinner("Montando las dos páginas…"):
                    with _cronometra("ficha"):
                        ficha = modelo.prepara(cli, limpio,
                                               st.session_state["inf_lectura"])
                if ficha.get("entradilla"):
                    st.session_state["inf_ficha"] = ficha
                else:
                    st.warning("La IA no ha devuelto un documento completo. Vuelve a "
                               "pulsar: suele salir a la segunda.")
            except Exception as e:  # noqa: BLE001
                st.error(f"No he podido preparar la cita. {type(e).__name__}: {e}")

    ficha = st.session_state["inf_ficha"]
    if ficha:
        st.markdown('<div class="seccion">El documento de dos páginas</div>',
                    unsafe_allow_html=True)
        nombre = motor.nombre_archivo(ficha.get("rasgo"))
        try:
            pdf, medidas = motor.documento_pdf(ficha, con_detalle=True)
        except Exception as e:  # noqa: BLE001
            pdf, medidas = None, {}
            st.error(f"No he podido generar el PDF. {type(e).__name__}: {e}")
        if pdf:
            st.download_button(
                f"Descargar {nombre}.pdf", pdf, file_name=f"{nombre}.pdf",
                mime="application/pdf", use_container_width=True, type="primary",
            )
            _chip("ficha")
            st.caption("Imprímelo y llévatelo a la entrevista. La última sección va "
                       "en blanco para tomar notas durante la cita. Si la cita es "
                       "otro día, guarda también el expediente, ahí arriba.")
            # Recortar es el ultimo recurso del motor para no abrir una tercera
            # hoja, y pasa cuando la IA se pasa de largo. Conviene saberlo.
            if medidas.get("recortes"):
                st.warning(
                    f"La IA ha devuelto más de lo que cabe y he dejado fuera "
                    f"{medidas['recortes']} elemento"
                    f"{'s' if medidas['recortes'] > 1 else ''} del final. Si te "
                    f"importa lo que falta, vuelve a pulsar «Preparar la cita».")
        if MANTENIMIENTO:
            with st.expander("Ver lo que ha devuelto la IA"):
                st.json(ficha, expanded=False)

    lectura = st.session_state["inf_lectura"]
    if lectura:
        st.markdown('<div class="seccion">La lectura</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(lectura)
        _chip("lectura")
        st.caption("Todo esto es hipótesis hasta la entrevista.")

BOTON_COPIAR = """
<style>
  body{ margin:0; font-family:'Source Sans', system-ui, sans-serif; }
  button{
    width:100%; box-sizing:border-box; cursor:pointer;
    font-family:inherit; font-size:.92rem; font-weight:600;
    color:#2E5E4E; background:#fff; border:1px solid #2E5E4E;
    border-radius:.5rem; padding:.48rem 1rem; transition:all .15s ease;
  }
  button:hover{ background:#2E5E4E; color:#fff; }
  button.hecho{ background:#2E5E4E; color:#fff; }
  button.fallo{ color:#B15A2B; border-color:#B15A2B; background:#FBF2EC; }
  /* El correo tiene que estar en el documento para poder seleccionarlo, pero
     fuera de la vista. Con display:none no hay nada que seleccionar. */
  #oculto{ position:fixed; left:-9999px; top:0; width:600px; }
</style>
<button id="copiar">Copiar el correo</button>
<div id="oculto">__HTML__</div>
<script>
const TEXTO = __TEXTO__;
const RICO = __RICO__;
const boton = document.getElementById('copiar');

function avisa(texto, clase){
  boton.textContent = texto;
  boton.className = clase;
  setTimeout(() => { boton.textContent = 'Copiar el correo'; boton.className = ''; }, 2200);
}

function porSeleccion(){
  // Copiar una selección conserva el formato igual que la API moderna, y
  // funciona donde aquella no está permitida. Es la red de abajo.
  try{
    const caja = document.getElementById('oculto');
    const rango = document.createRange();
    rango.selectNodeContents(caja);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(rango);
    const ok = document.execCommand('copy');
    sel.removeAllRanges();
    return ok;
  } catch (e){ return false; }
}

function porLaRed(){
  const ok = porSeleccion();
  avisa(ok ? 'Copiado con su formato' : 'No he podido copiarlo: selecciónalo a mano',
        ok ? 'hecho' : 'fallo');
}

boton.addEventListener('click', () => {
  if (navigator.clipboard && window.ClipboardItem){
    navigator.clipboard.write([new ClipboardItem({
      'text/html': new Blob([RICO], {type: 'text/html'}),
      'text/plain': new Blob([TEXTO], {type: 'text/plain'}),
    })]).then(() => avisa('Copiado con su formato', 'hecho'), porLaRed);
  } else {
    porLaRed();
  }
});
</script>
"""


def _copiar(texto):
    """El botón que se lleva el correo al portapapeles con su formato.

    Va en un marco aparte porque necesita JavaScript, y el portapapeles lleva
    las dos versiones: Outlook coge el HTML y conserva negritas y listas, y un
    cuadro de texto pelado coge el texto. `json.dumps` escapa el contenido para
    meterlo en el guion; lo de `</` es para que un `</script>` en el correo no
    cierre el guion antes de tiempo.
    """
    def literal(x):
        return json.dumps(x, ensure_ascii=False).replace("</", "<\\/")

    rico = motor.correo_html(texto)
    piezas = {"__HTML__": rico, "__TEXTO__": literal(texto), "__RICO__": literal(rico)}
    estilo.marco(
        re.sub(r"__(?:HTML|TEXTO|RICO)__", lambda m: piezas[m.group(0)], BOTON_COPIAR),
        46,
    )


# ---------------------------------------------------------------------------
# FASE 2 — Lo que se habló en la cita
# ---------------------------------------------------------------------------
with fase2:
    st.markdown('<div class="seccion">Qué hablasteis</div>', unsafe_allow_html=True)
    st.caption("En bruto, como se lo contarías a un compañero. Puedes dictarlo.")

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
    st.caption("Lo que cuentes aquí manda sobre cualquier hipótesis de la preparación. "
               "Conviene que salgan la situación documental y económica, las cargas, la "
               "disponibilidad real y cómo ha buscado hasta ahora.")

    _, hallazgos_notas = motor.limpia_datos_personales(notas)
    if hallazgos_notas:
        st.markdown('<div class="aviso-clave">Datos personales en las notas</div>',
                    unsafe_allow_html=True)
        st.warning(
            "He visto " + ", ".join(hallazgos_notas) + ". Se tacha antes de salir hacia "
            "la IA, pero el nombre propio no hay forma de detectarlo: no lo escribas."
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

    # La calibración es investigación, no trabajo del día: va plegada. El
    # documento y el correo salen igual sin tocarla, porque la casilla la
    # propone la IA por dentro.
    with st.expander("Calibración de la matriz de tipologías · opcional"):
        st.caption(
            "Para la hoja de calibración. Clasificando treinta o cuarenta casos se ve "
            "qué casilla sobra y cuál hay que partir en dos. No hace falta para que "
            "salgan el documento ni el correo."
        )

        # La que propuso la IA viene precargada, para confirmarla o cambiarla. Es una
        # hipótesis salida de un papel: quien cierra la casilla es quien estuvo en la
        # sala. Solo se precarga si no hay ninguna elegida, y una sola vez por
        # propuesta: si se cambia a mano, el cambio manda y no se vuelve a pisar.
        _propuesta = (st.session_state.get("inf_ficha") or {}).get("casilla")
        _rotulo = next((r for r in motor.CASILLAS_ROTULO
                        if motor.codigo_de_casilla(r) == str(_propuesta or "").upper()), "")
        if _rotulo and st.session_state.get("inf_propuesta") != _rotulo:
            st.session_state["inf_propuesta"] = _rotulo
            if st.session_state.get("inf_w_casilla", motor.SIN_CASILLA) == motor.SIN_CASILLA:
                st.session_state["inf_w_casilla"] = _rotulo

        casilla, motivacion = st.columns([3, 4], gap="medium")
        casilla.selectbox(
            "Casilla asignada", CASILLAS, key="inf_w_casilla",
            help="La propone la IA al preparar la cita y la cierras tú aquí." if _rotulo
                 else "De la matriz de tipologías.",
        )
        motivacion.radio("Motivación observada", motor.MOTIVACIONES,
                         key="inf_w_motivacion", horizontal=True)
        encaja, referencia = st.columns([3, 4], gap="medium")
        encaja.radio("¿Encajaba en la tipología?", motor.ENCAJES, key="inf_w_encaje",
                     horizontal=True)
        referencia.text_input("Referencia del caso", key="inf_w_referencia",
                              placeholder="Cita 15/09 · perfil de logística",
                              help="Cómo reconoces tú el caso en tu hoja. Sin nombres.")
        st.text_input("Observaciones", key="inf_w_observaciones",
                      placeholder="Encaja en A2, pero el hueco de dos años pesa como si "
                                  "fuera B1.")

        _casilla = st.session_state.get("inf_w_casilla") or motor.SIN_CASILLA
        if motor.codigo_de_casilla(_casilla):
            st.download_button(
                "Descargar la fila de calibración",
                motor.fila_calibracion({
                    clave: st.session_state.get(f"inf_w_{clave}")
                    for clave in ("casilla", "motivacion", "encaje", "referencia",
                                  "observaciones")
                }),
                file_name="calibracion_matriz.csv", mime="text/csv",
                use_container_width=True,
                help="Una fila con las columnas de la hoja, para pegarla tal cual.",
            )

# ---------------------------------------------------------------------------
# FASE 3 — El correo de cierre
# ---------------------------------------------------------------------------
with fase3:
    with st.expander("Tu firma y lo que adjuntes · opcional"):
        quien, donde = st.columns(2, gap="medium")
        quien.text_input("Firma", key="inf_w_firma",
                         placeholder="Álvaro, orientador laboral")
        donde.text_input("Canal de contacto", key="inf_w_canal",
                         placeholder="Respondiendo a este correo")
        st.text_input(
            "Qué va adjunto, si va algo", key="inf_w_adjuntos",
            placeholder="El currículo reescrito para hostelería.",
            help="Lo que adjuntes a mano en Outlook. El correo lo mencionará; si lo "
                 "dejas vacío, no habla de adjuntos.",
        )
        st.caption("Lo que adjuntes va sin firmar y sin mención de la oficina.")

    objetivo = (st.session_state.get("inf_w_objetivo1") or "").strip()
    if not objetivo:
        st.info("Escribe el objetivo principal en la pestaña de la cita: el correo se "
                "ordena alrededor de él.")

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
                    with _cronometra("correo"):
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
        with st.container(border=True):
            st.markdown(correo)
        _chip("correo")
        _copiar(correo)
        st.warning(
            "**Repasa las empresas antes de enviar.** Las propone la IA y puede "
            "equivocarse de nombre o proponer alguna que ya no exista. Cada una lleva "
            "su tipo y su zona, así que lo que no cuadre se sustituye sin rehacer nada."
        )
        st.caption("Pégalo en Outlook con «Mantener formato de origen»: llegan las "
                   "negritas y las listas, y la letra la pone tu Outlook. Léelo antes "
                   "de enviarlo, que lo firmas tú.")
        with st.expander("Verlo en texto plano"):
            st.code(correo, language=None, wrap_lines=True)
