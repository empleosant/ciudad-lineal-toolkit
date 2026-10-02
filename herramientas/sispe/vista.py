"""
Codificador de ocupaciones SISPE: la pantalla.

Apoyo para localizar códigos oficiales antes de grabarlos en SilcoiWeb.
Aquí solo vive lo que dibuja: tarjetas, cabecera, pestañas y el hilo de una
consulta (`resuelve`). La lógica está repartida en:

    motor.py        búsqueda en el catálogo, sin Streamlit (lo prueban las baterías)
    modelo.py       prompts y llamadas a la IA
    aprendizaje.py  lo que se guarda en el Gist compartido
    comun/          cliente de IA, Gist y estilo, compartidos con otras herramientas

Conexión con otras herramientas: el botón «+ CV» bajo las tarjetas manda
la ocupación al generador de CV a través de `herramientas.cv.estado`, y
«Dónde enviar el CV», debajo, saca de la guía de empleo (`comun/guia.py`) las
empresas del sector de cada ocupación.

Claves de sesión: todas con prefijo `sispe_`. Las claves de los contenedores
(`buscador`, `titular`, `pregunta`, `oc_*`, `cesta`, `guia`) las usa el CSS de aquí
abajo por su nombre: no las cambies sin cambiarlo también.
"""

import csv
import io
import re
import time

import streamlit as st

from comun import estilo, gist, guia, ia, version
from comun.texto import normaliza
from herramientas.cv import estado as cv_estado
from herramientas.cv import motor as cv_motor
from herramientas.sispe import aprendizaje, modelo, motor

N_CANDIDATOS = 16
VENTAJA_CLARA = 3.0   # cuántas veces debe superar el 1º del buscador al 2º
                      # para que mande él en lugar del modelo (sube para que
                      # mande menos, baja para que mande más)

estilo.aplica()
st.markdown("""
<style>
/* El buscador: campo con borde negro y botón rojo pegado, en una sola línea
   también en el móvil */
.st-key-buscador{ gap:0 !important; margin:.2rem 0 .4rem; box-shadow:0 8px 24px rgba(10,10,10,.08); border-radius:var(--radio); }
.st-key-buscador > div:first-child{ flex:1 1 auto !important; min-width:0; }
.st-key-buscador > div:last-child{ flex:0 0 auto !important; width:auto !important; }
.st-key-buscador div[data-testid="stTextInput"] div[data-testid="stTextInputRootElement"],
.st-key-buscador div[data-testid="stTextInput"]:not(:has(div[data-testid="stTextInputRootElement"])) div[data-baseweb="input"]{
  border:2px solid var(--negro) !important; border-right:0 !important;
  border-radius:var(--radio) 0 0 var(--radio) !important; background:#fff !important; box-shadow:none !important;
}
.st-key-buscador div[data-testid="stTextInput"] div[data-baseweb="base-input"],
.st-key-buscador div[data-testid="stTextInput"] input{ background:transparent !important; border:none !important; box-shadow:none !important; }
.st-key-buscador div[data-testid="stTextInput"] input{
  padding:.62rem .9rem !important; font-size:.98rem !important; color:var(--texto) !important;
  font-family:'Libre Franklin',sans-serif !important;
}
.st-key-buscador div[data-testid="stTextInput"]:focus-within div[data-testid="stTextInputRootElement"],
.st-key-buscador div[data-testid="stTextInput"]:not(:has(div[data-testid="stTextInputRootElement"])):focus-within div[data-baseweb="input"]{ border-color:var(--rojo) !important; }
.st-key-buscador button{
  background:var(--rojo) !important; color:#fff !important; border:2px solid var(--rojo) !important;
  border-radius:0 var(--radio) var(--radio) 0 !important; font-weight:700 !important;
  padding:0 1.3rem !important; min-height:40px !important; height:40px !important; letter-spacing:.02em;
}
.st-key-buscador button:hover{ background:var(--rojo-oscuro) !important; border-color:var(--rojo-oscuro) !important; }
.st-key-buscador button p{ color:#fff !important; font-weight:700 !important; }
.pie-buscador{ display:flex; justify-content:space-between; gap:.6rem; flex-wrap:wrap; font-size:.74rem; color:var(--tenue); margin:0 0 .4rem; }

/* La consulta como titular, con «Nueva búsqueda» al lado */
.st-key-titular{ border-bottom:2px solid var(--negro); padding-bottom:.25rem; margin:.6rem 0 .5rem; }
.st-key-titular div[data-testid="stColumn"]:last-child{ display:flex; justify-content:flex-end; }
@media (max-width:640px){ .st-key-titular div[data-testid="stColumn"]:last-child{ justify-content:flex-start; } }
.st-key-titular > div:first-child{ flex:1 1 auto !important; min-width:0; }
.st-key-titular > div:last-child:not(:first-child){ flex:0 0 auto !important; width:auto !important; }
.consulta-texto{ font-size:1.05rem; font-weight:700; letter-spacing:-.015em; color:var(--texto); line-height:1.25; }
.consulta-texto small{ font-weight:500; color:var(--suave); font-size:.9rem; }
.st-key-titular button{
  background:transparent !important; border:none !important; box-shadow:none !important; padding:0 !important;
  min-height:0 !important; height:auto !important;
}
.st-key-titular button p{ font-size:.8rem !important; font-weight:600 !important; color:var(--suave) !important; white-space:nowrap; }
.st-key-titular button:hover p{ color:var(--rojo) !important; }

/* La pregunta a la persona: texto a la izquierda, opciones a la derecha */
.st-key-pregunta{
  background:#fff; border:1px solid var(--linea); border-left:3px solid var(--rojo); border-radius:var(--radio);
  padding:.6rem .9rem; margin:0 0 .5rem;
}
.pregunta-titulo{ font-size:.62rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--rojo); margin-bottom:.1rem; }
.pregunta-texto{ font-size:.95rem; line-height:1.3; font-weight:600; color:var(--texto); }
.st-key-pregunta .stButton button{
  background:#fff; border:1.5px solid var(--negro); font-weight:600; border-radius:var(--radio);
  padding:.32rem .8rem; min-height:34px; font-size:.84rem; transition:all .15s ease;
  white-space:normal !important; height:auto !important;
}
.st-key-pregunta .stButton button p{ white-space:normal !important; }
.st-key-pregunta .stButton button:hover{ background:var(--negro); color:#fff; border-color:var(--negro); }
.st-key-pregunta .stButton button:hover p{ color:#fff; }

/* Las tarjetas de ocupación: contenedores de verdad, con sus dos botones */
[class*="st-key-oc_"]{
  background:#fff; border:1px solid var(--linea); border-radius:var(--radio); padding:.65rem .8rem .6rem .9rem;
  height:100%;
}
[class*="st-key-oc_"][class*="_top"]{ border-color:var(--rojo); box-shadow:inset 0 0 0 1px var(--rojo); }
[class*="st-key-oc_"][class*="_relleno"]{ background:#FAFAFA; }
[class*="st-key-oc_"] div[data-testid="stVerticalBlock"]{ gap:.3rem; }
.oc-cab{ display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }
.oc-cod{ font-family:'JetBrains Mono',monospace; font-weight:700; font-size:1.15rem; letter-spacing:.03em; color:var(--negro); }
.oc-rec{ font-size:.6rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; background:var(--rojo); color:#fff; padding:.14rem .45rem; border-radius:3px; white-space:nowrap; }
.oc-den{ font-weight:600; font-size:.9rem; line-height:1.25; color:var(--texto); margin-top:.1rem; }
.oc-mot{ font-size:.78rem; color:var(--suave); line-height:1.3; }
.oc-niv{ font-size:.62rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--tenue); margin-top:.15rem; }
.oc-niv.mando{ color:#C2410C; }
[class*="st-key-oc_"] .st-key-acciones_oc,
[class*="st-key-oc_"] div[data-testid="stHorizontalBlock"]{ flex-wrap:nowrap !important; gap:.4rem !important; }
[class*="st-key-oc_"] div[data-testid="stHorizontalBlock"] > div{ flex:1 1 0 !important; min-width:0 !important; width:auto !important; }
[class*="st-key-oc_"] .stButton button{
  width:100%; min-height:34px !important; height:34px !important; padding:0 .6rem !important;
  border-radius:var(--radio) !important; font-size:.8rem !important; font-weight:600 !important;
}
[class*="st-key-oc_"] iframe{ height:34px !important; }
[class*="st-key-oc_"] div[data-testid="stElementContainer"]:has(> iframe){ height:34px !important; flex:0 0 34px !important; }

/* Una línea para el currículo en curso */
.st-key-cesta{
  background:#fff; border:1px solid var(--linea); border-radius:var(--radio); padding:.45rem .9rem;
  margin-top:.6rem; align-items:center !important; flex-wrap:wrap !important; gap:.6rem !important;
}
.st-key-cesta > div:first-child{ flex:1 1 14rem !important; min-width:0; }
.st-key-cesta > div:last-child:not(:first-child){ flex:0 0 auto !important; width:auto !important; }
.cesta-texto{ font-size:.82rem; color:var(--suave); line-height:1.35; }
.cesta-texto b{ color:var(--texto); }
.st-key-cesta a[data-testid="stPageLink-NavLink"]{ font-weight:700; }
.st-key-cesta a[data-testid="stPageLink-NavLink"] p{ color:var(--rojo) !important; font-size:.84rem; }

/* Los ejemplos: chips */
.st-key-ejemplos div[data-testid="stButtonGroup"] button{ font-size:.84rem; font-weight:600; border-radius:999px; }

/* Dónde enviar el CV: el rótulo del desplegable (las fichas, en comun/estilo.py) */
.st-key-guia div[data-testid="stExpander"] summary p{ font-weight:700; font-size:.88rem; }
</style>
""", unsafe_allow_html=True)

if not motor.IDX["ok"]:
    st.error(f"Falta el archivo **{motor.CATALOGO}**.")
    st.stop()


def _busca(consulta, **k):
    """El buscador del motor más lo aprendido en el Gist compartido."""
    return motor.busca(
        consulta, lexico=aprendizaje.lexico(), refuerzos=aprendizaje.refuerzos(), **k
    )


# ---------------------------------------------------------------------------
# TARJETAS
# ---------------------------------------------------------------------------
# Cada tarjeta es un contenedor de Streamlit, con lo que dentro caben botones
# de verdad: el «+ CV» que manda la ocupación al generador va en la propia
# tarjeta, y no en una lista repetida debajo. Antes las tarjetas vivían todas
# en un marco aislado por el botón de copiar, y hacía falta calcular desde
# Python el alto del marco en tres anchos de pantalla. Ahora el marco es solo
# el botón de copiar, uno por tarjeta, de 34 px: lo único que de verdad
# necesita JavaScript.

BOTON_COPIAR = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@600&display=swap');
  html,body{ margin:0; padding:0; background:transparent; overflow:hidden; }
  button{
    width:100%; height:34px; box-sizing:border-box; cursor:pointer;
    font-family:'Libre Franklin',system-ui,sans-serif; font-size:.8rem; font-weight:600;
    color:#fff; background:#0A0A0A; border:1px solid #0A0A0A; border-radius:6px;
    transition:all .15s ease;
  }
  button:hover{ background:#333; }
  button.hecho{ background:#D1122E; border-color:#D1122E; }
</style>
<button id="c">Copiar __COD__</button>
<script>
const b = document.getElementById('c');
function hecho(){
  b.textContent = 'Copiado'; b.classList.add('hecho');
  setTimeout(() => { b.textContent = 'Copiar __COD__'; b.classList.remove('hecho'); }, 1400);
}
b.addEventListener('click', () => {
  navigator.clipboard.writeText('__COD__').then(hecho).catch(() => {
    const caja = document.createElement('textarea');
    caja.value = '__COD__'; document.body.appendChild(caja); caja.select();
    document.execCommand('copy'); document.body.removeChild(caja); hecho();
  });
});
</script>
"""


def boton_copiar(codigo):
    estilo.marco(BOTON_COPIAR.replace("__COD__", codigo), 34)


def pinta_tarjeta(i, o, interactivo):
    es_primera = (i == 1 and not o.get("provisional"))
    es_mando = o.get("nivel") in ("10", "20", "30")
    clave = f"oc_{i}" + ("_top" if es_primera else "") + ("_relleno" if o.get("relleno") else "")
    with estilo.caja(clave):
        st.markdown(
            '<div class="oc-cab">'
            f'<span class="oc-cod">{o["codigo"]}</span>'
            + ('<span class="oc-rec">★ Recomendada</span>' if es_primera else "")
            + '</div>'
            f'<div class="oc-den">{o["denominacion"]}</div>'
            + (f'<div class="oc-mot">{o["motivo"]}</div>' if o.get("motivo") else "")
            + f'<div class="oc-niv{" mando" if es_mando else ""}">Nivel {o["nivel"]} · {o["nivel_texto"]}</div>',
            unsafe_allow_html=True,
        )
        if interactivo:
            copiar, anadir = st.columns(2, gap="small")
            with copiar:
                boton_copiar(o["codigo"])
            ya = cv_estado.en_lista(o["codigo"])
            anadir.button(
                "Añadido al CV" if ya else "+ CV", key=f"addcv_{o['codigo']}",
                use_container_width=True, disabled=ya,
                help=f"Al currículo como «{cv_motor.a_oracion(o['denominacion'])}»",
                on_click=cv_estado.anade_experiencia,
                args=(o["codigo"], o["denominacion"], o.get("motivo", "")),
            )
        else:
            boton_copiar(o["codigo"])


def pinta_tarjetas(ocupaciones, interactivo=False):
    """Las tarjetas, de dos en dos. En el móvil las columnas se apilan y salen
    en orden porque cada fila es su propio `st.columns`."""
    if not ocupaciones:
        return
    for fila in range(0, len(ocupaciones), 2):
        cols = st.columns(2, gap="small")
        for j, col in enumerate(cols):
            i = fila + j
            if i < len(ocupaciones):
                with col:
                    pinta_tarjeta(i + 1, ocupaciones[i], interactivo)


def pinta_resultado(payload, estado=None, avance=0.06, interactivo=False, consulta=""):
    if estado:
        st.progress(min(avance, 0.95), text=estado)
        # Antes se volvia aqui, asi que durante la espera solo se veia la barra.
        # Pero el catalogo ya ha respondido en el primer milisegundo y esos
        # resultados estaban calculados y guardados sin llegar a mostrarse. Si
        # los hay, se pintan bajo la barra y se sustituyen cuando el modelo
        # termina: la espera es la misma, pero deja de ser una pantalla vacia.
        if not payload.get("ocupaciones"):
            return
    if payload.get("aviso"):
        st.info(payload["aviso"])
        return

    ocupaciones = payload.get("ocupaciones", [])
    if not ocupaciones:
        st.info("No encuentro coincidencias claras. Prueba con el nombre del puesto o función concreta.")
        return

    # 1. PREGUNTA ARRIBA (antes de las tarjetas): el texto a la izquierda y
    #    las opciones a su derecha; en el móvil, debajo.
    if payload.get("pregunta"):
        with estilo.caja("pregunta"):
            opciones = (motor.extraer_opciones(payload.get("pregunta", ""), payload.get("opciones"))
                        if interactivo else [])
            texto_col, opciones_col = st.columns([5, 5], gap="small") if opciones else (st.container(), None)
            texto_col.markdown(
                '<div class="pregunta-titulo">Pregunta para la persona</div>'
                f'<div class="pregunta-texto">{payload["pregunta"]}</div>',
                unsafe_allow_html=True,
            )
            if opciones:
                with opciones_col, estilo.fila("opciones_pregunta", wrap=True):
                    for idx, opc in enumerate(opciones):
                        if st.button(opc, key=f"resp_opt_{idx}"):
                            st.session_state["sispe_respuesta"] = (consulta, payload["pregunta"], opc)
                            st.rerun()

    # 2. TARJETAS DE OCUPACIONES
    pinta_tarjetas(ocupaciones, interactivo=interactivo)

    if estado:
        return

    if payload.get("interpretado") and MANTENIMIENTO:
        origen, destino = payload["interpretado"]
        st.markdown(
            f'<div class="nota">Interpretado <b>{origen}</b> como: {destino}</div>',
            unsafe_allow_html=True,
        )

    otras = payload.get("otras", [])
    if otras:
        with st.expander("Ver otras ocupaciones del catálogo"):
            arranque = len(payload.get("ocupaciones", [])) + 1
            for orden, (cod, den) in enumerate(otras, arranque):
                st.markdown(
                    f'<div style="padding:.15rem 0;border-bottom:1px solid var(--linea)">'
                    f'<span style="font-family:JetBrains Mono,monospace;font-weight:700;'
                    f'font-size:.82rem;letter-spacing:.04em">{cod}</span> &nbsp; '
                    f'<span style="font-size:.82rem">{den}</span></div>',
                    unsafe_allow_html=True,
                )

    if payload.get("fallo"):
        st.markdown('<div class="nota">Resultados del catálogo, sin afinar.</div>', unsafe_allow_html=True)
        if MANTENIMIENTO:
            with st.expander("Ver el motivo"):
                st.code(payload["fallo"], language=None, wrap_lines=True)

    if payload.get("descartadas"):
        st.markdown(
            f'<div class="nota">Se {"ha" if payload["descartadas"] == 1 else "han"} descartado '
            f'{payload["descartadas"]} '
            f'{"sugerencia que no figuraba" if payload["descartadas"] == 1 else "sugerencias que no figuraban"} '
            f'en el catálogo oficial.</div>',
            unsafe_allow_html=True,
        )

    pinta_chip(payload)


def pinta_donde_enviar(ocupaciones):
    """«Dónde enviar el CV», plegado bajo las tarjetas.

    Las empresas del sector de la ocupación, sacadas de la guía de empleo
    (`comun/guia.py`), con la lista para imprimir. Va cerrado porque quien
    codifica una inscripción no lo necesita; quien orienta, lo abre. Si hay
    varias tarjetas se elige la ocupación dentro; el rótulo es siempre el de
    la recomendada, para que el desplegable no se cierre al cambiarla.
    """
    ocupaciones = [o for o in ocupaciones if o.get("codigo")]
    if not ocupaciones:
        return
    primeras = guia.secciones([ocupaciones[0]["codigo"]])
    if not primeras:
        return
    rotulo = ("portales generalistas" if primeras[0]["general"]
              else ", ".join(s["corto"] for s in primeras[:3]) + ("…" if len(primeras) > 3 else ""))
    with st.container(key="guia"), st.expander(f"Dónde enviar el CV · {rotulo}", icon=":material/send:"):
        if len(ocupaciones) > 1:
            nombres = {o["codigo"]: o["denominacion"] for o in ocupaciones}
            codigo = st.selectbox(
                "Para la ocupación", list(nombres), key="sispe_guia_oc",
                format_func=lambda c: f"{c} · {cv_motor.a_oracion(nombres[c])}",
            )
        else:
            codigo = ocupaciones[0]["codigo"]
        denominacion = next(o["denominacion"] for o in ocupaciones if o["codigo"] == codigo)
        secs = guia.secciones([codigo])
        if secs[0]["general"]:
            st.caption("La guía no tiene un sector para esta ocupación: estos son los portales "
                       "generalistas y las grandes redes de trabajo temporal.")
        elegida = st.pills(
            "Sector", list(range(len(secs))), default=0, key=f"sispe_guia_sec_{codigo}",
            format_func=lambda i: f"{secs[i]['corto']} · {secs[i]['n']}", label_visibility="collapsed",
        )
        puesto = cv_motor.a_oracion(denominacion)
        st.download_button(
            "Lista para imprimir (PDF)", icon=":material/print:", on_click="ignore",
            data=lambda: guia.pdf(secs, "Dónde enviar tu currículum",
                                  f"{puesto} · " + ", ".join(s["corto"] for s in secs),
                                  puesto=puesto[:1].lower() + puesto[1:]),
            file_name=f"Donde_enviar_CV_{re.sub(r'[^0-9A-Za-z]+', '_', puesto).strip('_')}.pdf",
            mime="application/pdf", help="Todos los sectores de esta ocupación, a dos columnas y "
                                         "en blanco y negro, con el guion para llamar.",
        )
        st.caption(f"De la guía «{guia.EDICION['titulo_empresas']}» "
                   f"({guia.EDICION['edicion'].lower()}), comprobada en {guia.EDICION['verificado']}. "
                   "Que una empresa salga aquí no garantiza que tenga vacantes.")
        st.markdown(guia.apartados_html(secs[elegida or 0]["apartados"]), unsafe_allow_html=True)


def pinta_chip(payload):
    """El pie del resultado: quién ha contestado y cuánto se ha esperado.

    Sin esto no hay forma de saber, mirando la pantalla, si ha respondido el
    primero de la cadena o el de repuesto, ni si la espera ha sido de uno o de
    diez segundos. Con `fallo` no se pinta: ahí no ha contestado nadie y lo
    que se ve es el catálogo sin afinar.
    """
    nombre = payload.get("modelo", "")
    if nombre and not payload.get("fallo"):
        estilo.chip_ia(nombre, payload.get("espera", 0.0))
    elif any(o.get("motivo", "").startswith("Coincidencia directa")
             for o in payload.get("ocupaciones", [])):
        estilo.chip("Coincidencia directa", "#3B82F6")


# ---------------------------------------------------------------------------
# LOGICA DE CONSULTA
# ---------------------------------------------------------------------------

class cronometra:
    """Mide lo que tarda cada llamada al modelo y lo guarda para el panel.

    Solo observa: no cambia ni un resultado. Sirve para dejar de decidir a ojo
    dónde se va el tiempo. Se ve en el panel de ajustes con ?mantenimiento=1.
    """

    def __init__(self, etiqueta):
        self.etiqueta = etiqueta

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *_):
        segundos = time.perf_counter() - self.t0
        st.session_state.setdefault("sispe_tiempos", []).append((self.etiqueta, segundos))
        return False


def anota_relevo(linea):
    """Deja constancia de cada intento fallido de la cascada de proveedores.

    Sin esto el relevo es invisible: el primer proveedor puede llevar una
    semana caído y la herramienta parece ir igual de bien, solo que más lenta.
    Se ve en el panel de ajustes con ?mantenimiento=1.
    """
    st.session_state.setdefault("sispe_relevos", []).append(linea)


def _basica(encontrados, motivo=""):
    # "provisional" marca lo que sale del catalogo sin que el modelo lo haya
    # revisado: ni durante la espera, ni cuando el modelo falla. Esas tarjetas
    # no llevan la marca de recomendada, porque nadie las ha recomendado.
    return [{
        "codigo": c, "denominacion": d, "nivel": "00",
        "nivel_texto": motor.NIVELES["00"], "motivo": motivo,
        "provisional": True,
    } for _, c, d in encontrados[:5]]


def resuelve(texto, zona, usar_ia=True, contexto="", busqueda=None):
    codigo = texto.strip()
    if re.fullmatch(r"\d{8}", codigo):
        if codigo in motor.IDX["por_codigo"]:
            payload = {"ocupaciones": [{
                "codigo": codigo,
                "denominacion": motor.IDX["por_codigo"][codigo],
                "nivel": "00",
                "nivel_texto": motor.NIVELES["00"],
                "motivo": "Consulta directa por código.",
            }]}
        else:
            payload = {"aviso": f"El código {codigo} no figura en el catálogo oficial."}
        with zona.container():
            pinta_resultado(payload)
        return payload

    encontrados = _busca(busqueda or texto, tope=N_CANDIDATOS)
    # Lo que devuelve el buscador para lo que ESCRIBIO la persona, antes de que
    # la IA reinterprete y sustituya `encontrados`. La decision de quien manda
    # tiene que tomarse sobre esto, no sobre la busqueda reescrita por el
    # modelo: ahi las puntuaciones se aplanan y la ventaja real desaparece.
    literales = encontrados[:2]
    st.session_state["sispe_tiempos"] = []
    st.session_state["sispe_relevos"] = []
    cli = ia.cliente() if usar_ia else None

    if not encontrados and cli is None:
        payload = {"ocupaciones": []}
        with zona.container():
            pinta_resultado(payload)
        return payload

    memoria = st.session_state["sispe_cache"]
    clave = normaliza(texto + contexto)
    if clave in memoria:
        with zona.container():
            pinta_resultado(memoria[clave])
        return memoria[clave]

    provisional = {
        "ocupaciones": _basica(encontrados, "Resultado del catálogo, sin afinar todavía."),
        "otras": [(c, d) for _, c, d in encontrados[5:12]],
    }

    # ATAJO SIN IA.
    # Si el buscador saca al segundo mas de VENTAJA_CLARA veces, la persona ha
    # escrito practicamente el nombre de la ocupacion y no hay nada que
    # interpretar. Llamar al modelo ahi solo anade tres viajes a Google, entre
    # diez y treinta segundos de espera y consumo de cuota, para acabar en el
    # mismo sitio (o peor: para "montador de placa de pladur" proponia
    # escayolistas). Se contesta al instante con lo que dice el catalogo.
    # El resto de resultados sigue disponible en "Ver otras ocupaciones".
    if literales and not contexto:
        segundo_l = literales[1][0] if len(literales) > 1 else 0.0
        if segundo_l <= 0 or (literales[0][0] / segundo_l) > VENTAJA_CLARA:
            _, cod_a, den_a = literales[0]
            atajo = {
                "ocupaciones": [{
                    "codigo": cod_a,
                    "denominacion": den_a,
                    "nivel": "00",
                    "nivel_texto": motor.NIVELES["00"],
                    "motivo": "Coincidencia directa con lo que escribiste.",
                }],
                "otras": [(c, d) for _, c, d in encontrados[1:9]],
            }
            with zona.container():
                pinta_resultado(atajo)
            memoria[clave] = atajo
            return atajo

    if cli is None:
        with zona.container():
            pinta_resultado(provisional)
        return provisional

    with zona.container():
        pinta_resultado(provisional, estado="Afinando el resultado")

    interpretado, aviso = None, ""
    with zona.container():
        pinta_resultado({}, estado="Interpretando el oficio", avance=0.12)
    with cronometra("1. Interpretar el oficio"):
        lecturas = modelo.interpreta_consulta(
            cli, texto, st.session_state.setdefault("sispe_interpretaciones", {}),
            al_relevar=anota_relevo,
        )
    if lecturas:
        fundido, vistos = [], {}
        for orden, (terminos, grupos) in enumerate(lecturas):
            peso = (1.0, 0.88, 0.78)[min(orden, 2)]
            for puntos, c_cod, denom in _busca(terminos, tope=12, grupos=grupos):
                if puntos * peso > vistos.get(c_cod, 0):
                    vistos[c_cod] = puntos * peso
                    fundido.append((puntos * peso, c_cod, denom))

        mejores = sorted(
            {c: (p, c, d) for p, c, d in sorted(fundido)}.values(), reverse=True
        )[:N_CANDIDATOS + 4]

        if len(mejores) < 3:
            mejores = _busca(
                f"{busqueda or texto} {lecturas[0][0]}",
                tope=N_CANDIDATOS + 4, grupos=lecturas[0][1],
            )
        if mejores:
            encontrados = mejores
            interpretado = (
                "la consulta",
                " · ".join(t.split()[0] for t, _ in lecturas),
            )
            provisional = {
                "ocupaciones": _basica(encontrados, "Resultado del catálogo, sin afinar todavía."),
                "otras": [(c, d) for _, c, d in encontrados[5:12]],
            }

    if not encontrados:
        payload = {"ocupaciones": []}
        zona.empty()
        pinta_resultado(payload)
        return payload

    def consulta_al_modelo(candidatos, etiqueta):
        bruto, avance = "", 0.10
        arranque = time.perf_counter()
        for trozo in modelo.flujo_modelo(cli, texto + contexto, candidatos,
                                         al_relevar=anota_relevo):
            bruto += trozo
            transcurrido = time.perf_counter() - arranque
            if transcurrido > ia.ESPERA_MAXIMA:
                raise TimeoutError(
                    f"El modelo ha tardado más de {ia.ESPERA_MAXIMA} segundos."
                )
            nuevo = min(0.10 + transcurrido / (ia.ESPERA_MAXIMA * 1.4), 0.92)
            if nuevo - avance > 0.04:
                avance = nuevo
                with zona.container():
                    pinta_resultado({}, estado=etiqueta, avance=avance)
        return motor.interpreta(bruto)

    try:
        lista = "\n".join(f"{c}:{d}" for _, c, d in encontrados)
        with cronometra("2. Afinar el resultado"):
            payload = consulta_al_modelo(lista, "Afinando el resultado")

        if payload.get("mas_terminos"):
            with zona.container():
                pinta_resultado({}, estado="Ampliando la búsqueda", avance=0.45)
            ampliados = _busca(f"{busqueda or texto} {payload['mas_terminos']}",
                              tope=N_CANDIDATOS + 6)
            if ampliados:
                encontrados = ampliados
                interpretado = ("la descripción", payload["mas_terminos"])
                with cronometra("3. Ampliar la búsqueda"):
                    segunda = consulta_al_modelo(
                        "\n".join(f"{c}:{d}" for _, c, d in ampliados),
                        "Afinando el resultado",
                    )
                if segunda["ocupaciones"]:
                    payload = segunda
    except Exception as e:  # noqa: BLE001
        zona.empty()
        provisional["fallo"] = f"{type(e).__name__}: {e}"
        pinta_resultado(provisional)
        return provisional

    if payload["ocupaciones"] and encontrados:
        elegido = payload["ocupaciones"][0]["codigo"]
        if elegido != encontrados[0][1]:
            palabras = [
                motor.raiz(w) for w in re.findall(r"\w+", normaliza(texto))
                if len(w) > 3 and w not in motor.VACIAS
            ]
            st.session_state.setdefault("sispe_refuerzos_por_guardar", []).append(
                (elegido, palabras)
            )

    if interpretado:
        payload["interpretado"] = interpretado
    if aviso:
        payload["fallo"] = aviso
    if not payload["ocupaciones"]:
        payload["ocupaciones"] = provisional["ocupaciones"]

    # Se muestran las ocupaciones que el modelo considera pertinentes. Ya no se
    # completan seis tarjetas siempre: rellenar el hueco con lo siguiente del
    # catalogo, sin relacion con lo buscado, restaba confianza en las buenas.
    # Lo descartado sigue a un clic, en "Ver otras ocupaciones del catalogo".
    #
    # Pero el buscador no puede quedar mudo. El modelo reinterpreta la consulta
    # y a veces se aleja de lo que se escribio: para "montador de placa de
    # pladur" ha llegado a proponer escayolistas y albañiles, que no estan ni
    # entre los seis mejores del catalogo. Por eso:
    #
    #   1) el mejor resultado del buscador entra SIEMPRE como tarjeta,
    #   2) y si ademas arrasa (VENTAJA_CLARA veces mas puntos que el segundo),
    #      se pone el primero y es el que lleva la marca de recomendada.
    #
    # Una ventaja aplastante significa que la persona escribio casi el nombre
    # exacto de la ocupacion; ahi interpretar sobra. Cuando la ventaja es corta
    # hay ambiguedad real y manda el modelo, que para eso esta.
    ya = {o["codigo"] for o in payload["ocupaciones"]}
    if literales:
        puntos, codigo_c, denom = literales[0]
        segundo = literales[1][0] if len(literales) > 1 else 0.0
        arrasa = segundo <= 0 or (puntos / segundo) > VENTAJA_CLARA

        if codigo_c not in ya:
            tarjeta = {
                "codigo": codigo_c,
                "denominacion": denom,
                "nivel": "00",
                "nivel_texto": motor.NIVELES["00"],
                "motivo": "Mejor coincidencia del catálogo con lo que escribiste.",
            }
            if arrasa:
                payload["ocupaciones"].insert(0, tarjeta)
            else:
                payload["ocupaciones"].append(tarjeta)
        elif arrasa and payload["ocupaciones"][0]["codigo"] != codigo_c:
            i_mejor = next(
                i for i, o in enumerate(payload["ocupaciones"])
                if o["codigo"] == codigo_c
            )
            payload["ocupaciones"].insert(0, payload["ocupaciones"].pop(i_mejor))

    elegidos = {o["codigo"] for o in payload["ocupaciones"]}
    payload["otras"] = [(c, d) for _, c, d in encontrados if c not in elegidos][:8]

    # Quien ha contestado y cuanto se ha esperado viajan DENTRO del resultado,
    # no en la sesion: el resultado se guarda en cache y se vuelve a pintar en
    # reruns posteriores, y leyendo la sesion el chip acababa atribuyendo a la
    # IA respuestas que habia dado el catalogo en una consulta anterior.
    payload["modelo"] = ia.ultimo_uso()[1]
    payload["espera"] = sum(t for _, t in st.session_state["sispe_tiempos"])

    zona.empty()
    pinta_resultado(payload)
    memoria[clave] = payload
    return payload


# ---------------------------------------------------------------------------
# INTERFAZ
# ---------------------------------------------------------------------------

try:
    MANTENIMIENTO = st.query_params.get("mantenimiento") == "1"
except Exception:  # noqa: BLE001
    MANTENIMIENTO = False

st.session_state.setdefault("sispe_actual", None)
st.session_state.setdefault("sispe_registro", [])
st.session_state.setdefault("sispe_pendiente", None)
st.session_state.setdefault("sispe_usar_ia", True)
st.session_state.setdefault("sispe_cache", {})
st.session_state.setdefault("sispe_respuesta", None)
st.session_state.setdefault("sispe_por_guardar", [])
st.session_state.setdefault("sispe_refuerzos_por_guardar", [])
st.session_state.setdefault("sispe_ultima", "")
st.session_state.setdefault("consulta", "")

ARRANQUE = "Una persona que "
EJEMPLOS = [
    "Una persona que limpia habitaciones de hotel",
    "Una persona que conduce autobuses",
    "Una persona que monta placa de pladur",
    "Una persona que organiza eventos para empresas",
    "Una persona que reparte comida en moto",
    "Una persona que cuida a mayores en su casa",
    "Una persona que atiende la barra de un bar",
    "Una persona que lleva las facturas y las nóminas",
    "Una persona que maneja carretilla en un almacén",
    "Una persona que corta el pelo en una peluquería",
]


def panel_ajustes():
    with st.popover(":material/tune:", help="Ajustes"):
        st.session_state["sispe_usar_ia"] = st.toggle(
            "Afinar con IA", value=st.session_state["sispe_usar_ia"],
            help="Desactivado, muestra las coincidencias del catálogo al instante.",
        )
        if st.session_state["sispe_registro"]:
            buffer = io.StringIO()
            escritor = csv.writer(buffer, delimiter=";")
            escritor.writerow(["consulta", "codigos"])
            for fila in st.session_state["sispe_registro"]:
                escritor.writerow(fila)
            st.download_button(
                "Descargar sesión", buffer.getvalue().encode("utf-8-sig"),
                file_name="codificaciones.csv", mime="text/csv",
                use_container_width=True,
            )

        st.caption(f"Versión {version.commit()}")
        if not MANTENIMIENTO:
            return

        tiempos = st.session_state.get("sispe_tiempos", [])
        if tiempos:
            st.caption("Última consulta, segundo a segundo:")
            for etiqueta, seg in tiempos:
                st.caption(f"· {etiqueta}: **{seg:.1f} s**")
            st.caption(f"· Total esperando al modelo: **{sum(t for _, t in tiempos):.1f} s**")

        relevos = st.session_state.get("sispe_relevos", [])
        if relevos:
            st.caption("Relevos de la última consulta:")
            for linea in relevos:
                st.caption(f"· {linea}")

        inexistentes = ia.muertos()
        if inexistentes:
            # Es el aviso más importante de los tres: significa que la lista de
            # PROVEEDORES está desfasada y hay que corregirla a mano. Se
            # comprueba con `scripts/comprobar_ia.py` donde haya claves.
            st.warning("Modelos que ya no existen: "
                       + "; ".join(f"{p}: {', '.join(ms)}"
                                   for p, ms in inexistentes.items()))

        apartados = ia.quemados()
        bajados = ia.degradados()
        if apartados:
            st.caption("Apartados por cupo: **" + ", ".join(sorted(apartados)) + "**")
        if bajados:
            st.caption("Degradados: **"
                       + ", ".join(f"{p} → {m}" for p, m in bajados.items()) + "**")

        # Fijar un proveedor apaga la cascada, que es justo lo que hace falta
        # para poder comparar dos: con el relevo activo, la consulta de prueba
        # podría acabar respondida por otro y estaríamos midiendo otra cosa.
        elegibles = [ia.CASCADA] + [p for p in ia.ORDEN if ia.tiene_clave(p)]
        actual = st.session_state.get("ia_proveedor", ia.CASCADA)
        st.session_state["ia_proveedor"] = st.selectbox(
            "Proveedor", elegibles,
            index=elegibles.index(actual) if actual in elegibles else 0,
            help="«cascada» recorre el orden; fijar uno apaga el relevo.",
        )

        if st.button("Probar la conexión con la IA", use_container_width=True):
            with st.spinner("Llamando…"):
                correcto, detalle = ia.prueba()
            (st.success if correcto else st.error)(detalle)

        # La de verdad: recorre la lista entera de PROVEEDORES y dice qué
        # nombres ya no existen. Es lo que hay que pulsar después de tocar esa
        # lista, y lo único que puede comprobarlo cuando las claves solo están
        # en el despliegue. Gasta una decena de llamadas de 16 tokens.
        if st.button("Probar TODOS los modelos", use_container_width=True,
                     help="Una llamada mínima por modelo de la lista. Dice cuáles ya no existen."):
            with st.spinner("Probando la cadena entera…"):
                correcto, detalle = ia.prueba(todos=True)
            (st.success if correcto else st.error)(detalle)

        if gist.activo():
            st.markdown("**Diccionario compartido**")
            st.caption(f"{len(aprendizaje.lexico())} términos aprendidos.")
            if st.button("Comprobar que guarda", use_container_width=True):
                correcto, detalle = aprendizaje.prueba()
                (st.success if correcto else st.error)(detalle)


def usar_ejemplo():
    """Un chip de ejemplo lanza la consulta completa y se suelta él solo."""
    elegido = st.session_state.get("sispe_ejemplo")
    if not elegido:
        return
    st.session_state["sispe_ejemplo"] = None
    st.session_state["sispe_pendiente"] = ARRANQUE + elegido
    st.session_state["consulta"] = ""
    st.session_state["sispe_actual"] = None
    st.session_state["sispe_ultima"] = ""


def linea_curriculo():
    """Una línea con lo que lleva el currículo en curso y el enlace al generador.

    Los «+ CV» van en cada tarjeta; esto solo dice cuántas experiencias hay ya
    y abre el generador. Es la conexión entre las dos herramientas: pasa por
    `herramientas.cv.estado`.
    """
    exps = cv_estado.experiencias()
    if not exps:
        return
    n = len(exps)
    nombres = " · ".join(cv_motor.titulo_experiencia(e) for e in exps[-3:])
    if n > 3:
        nombres = f"… · {nombres}"
    with estilo.fila("cesta", wrap=True, vertical_alignment="top"):
        st.markdown(
            f'<div class="cesta-texto"><b>Currículo en curso:</b> {n} experiencia{"s" if n != 1 else ""}'
            f' · {nombres}</div>',
            unsafe_allow_html=True, **estilo._ancho("stretch"),
        )
        st.page_link(cv_estado.PAGINA, label="Abrir el generador de CV →")


def empezar_de_nuevo():
    st.session_state["sispe_actual"] = None
    st.session_state["consulta"] = ""
    st.session_state["sispe_ultima"] = ""


# ---------------------------------------------------------------------------
# Desambiguación interactiva con opciones adaptativas
# ---------------------------------------------------------------------------

entrada, contexto, busqueda, rotulo = None, "", None, None

respuesta = st.session_state.pop("sispe_respuesta", None)
if respuesta:
    original, pregunta, eleccion = respuesta
    entrada = original
    rotulo = f"{original}  ·  {eleccion}"
    contexto = (
        f"\n\nACLARACIÓN: a la pregunta «{pregunta}» la persona respondió "
        f"«{eleccion}». Ten en cuenta esta aclaración para priorizar la opción adecuada "
        f"y no vuelvas a plantear la misma duda."
    )
    busqueda = f"{original} {eleccion}"

if not entrada:
    entrada = st.session_state.pop("sispe_pendiente", None)

# ---------------------------------------------------------------------------
# Barra, título y buscador
# ---------------------------------------------------------------------------

with estilo.banda(
    "sispe", "Codificador SISPE",
    "Describe el puesto con las palabras de la persona y te propone el código oficial.",
    acciones=panel_ajustes,
):
    with estilo.fila("buscador", vertical_alignment="center"):
        texto = st.text_input(
            "Consulta", label_visibility="collapsed", key="consulta",
            placeholder="Describe el puesto o escribe un código de 8 cifras",
        )
        buscar = st.button("Buscar", key="buscar")
    st.markdown(
        f'<div class="pie-buscador"><span>{len(motor.IDX["registros"])} ocupaciones del catálogo '
        'oficial · describe solo el puesto, sin datos identificativos</span>'
        f'<span>Afinar con IA: {"activado" if st.session_state["sispe_usar_ia"] else "desactivado"}</span></div>',
        unsafe_allow_html=True,
    )

    escrito = (texto or "").strip()
    if escrito and not entrada:
        if buscar or escrito != st.session_state.get("sispe_ultima", ""):
            entrada = escrito
            contexto, busqueda, rotulo = "", None, None

if entrada:
    st.session_state["sispe_ultima"] = entrada


def titular(consulta, n=None):
    """La consulta como titular, con la cuenta de resultados y «Nueva búsqueda».

    Van en columnas y no en un contenedor horizontal: en el horizontal,
    Streamlit mide el texto como si fuera una sola línea y, cuando en el
    móvil se parte en dos, la segunda se sale por debajo del filo. En
    columnas, el botón pasa debajo del texto en el móvil y no se pierde nada.
    """
    with estilo.caja("titular"):
        texto_col, boton_col = st.columns([7, 3], gap="small", vertical_alignment="bottom")
        cuenta = (f"{n} ocupación para " if n == 1 else f"{n} ocupaciones para ") if n else ""
        texto_col.markdown(
            f'<div class="consulta-texto"><small>{cuenta}</small>«{consulta}»</div>',
            unsafe_allow_html=True,
        )
        boton_col.button("↺ Nueva búsqueda", key="reinicio", on_click=empezar_de_nuevo)


# ---------------------------------------------------------------------------
# Cuerpo
# ---------------------------------------------------------------------------

if entrada:
    titular(rotulo or entrada)
    zona = st.empty()
    payload = resuelve(
        entrada, zona,
        usar_ia=st.session_state["sispe_usar_ia"],
        contexto=contexto, busqueda=busqueda,
    )
    st.session_state["sispe_actual"] = (rotulo or entrada, payload)
    st.session_state["sispe_registro"].append((
        rotulo or entrada,
        " | ".join(o["codigo"] for o in payload.get("ocupaciones", [])),
    ))
    st.rerun()

elif st.session_state["sispe_actual"]:
    consulta, payload = st.session_state["sispe_actual"]
    titular(consulta, len(payload.get("ocupaciones", [])))
    pinta_resultado(payload, interactivo=True, consulta=consulta)
    if not payload.get("aviso"):
        pinta_donde_enviar(payload.get("ocupaciones", []))
    linea_curriculo()

else:
    st.markdown('<div class="seccion">Prueba con «una persona que…»</div>', unsafe_allow_html=True)
    with estilo.caja("ejemplos"):
        st.pills(
            "Ejemplos", [ej[len(ARRANQUE):] for ej in EJEMPLOS], key="sispe_ejemplo",
            label_visibility="collapsed", on_change=usar_ejemplo,
        )
    linea_curriculo()

# Estas dos escrituras van a la API de GitHub y ocurren AL TERMINAR la
# busqueda, cuando el usuario ya cree que ha acabado. No se veian en el panel
# porque solo se cronometraba a Gemini; aqui pueden irse varios segundos.

_pendientes = st.session_state.pop("sispe_por_guardar", [])
if _pendientes:
    with cronometra("4. Guardar términos aprendidos (GitHub)"):
        for clave, valor in _pendientes:
            aprendizaje.guarda_termino(clave, valor)

_refuerzos = st.session_state.pop("sispe_refuerzos_por_guardar", [])
if _refuerzos:
    with cronometra("5. Guardar correcciones de orden (GitHub)"):
        for codigo, palabras in _refuerzos:
            aprendizaje.guarda_refuerzo(codigo, palabras)
