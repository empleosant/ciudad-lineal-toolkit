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
la ocupación al generador de CV a través de `herramientas.cv.estado`.

Claves de sesión: todas con prefijo `sispe_`. Las claves de widgets (`consulta`, `buscar`, `marca`,
`cabecera`, `pregunta`, `reinicio`, `ajustes`) las usa el CSS de
`comun/estilo.py` por su nombre: no las cambies sin cambiarlo allí.
"""

import csv
import io
import math
import re
import time

import streamlit as st
import streamlit.components.v1 as components

from comun import estilo, gist, ia, version
from comun.texto import normaliza
from herramientas.cv import estado as cv_estado
from herramientas.cv import motor as cv_motor
from herramientas.sispe import aprendizaje, modelo, motor

N_CANDIDATOS = 16
VENTAJA_CLARA = 3.0   # cuántas veces debe superar el 1º del buscador al 2º
                      # para que mande él en lugar del modelo (sube para que
                      # mande menos, baja para que mande más)

estilo.aplica()

if not motor.IDX["ok"]:
    st.error(f"Falta el archivo **{motor.CATALOGO}**.")
    st.stop()


def _busca(consulta, **k):
    """El buscador del motor más lo aprendido en el Gist compartido."""
    return motor.busca(
        consulta, lexico=aprendizaje.lexico(), refuerzos=aprendizaje.refuerzos(), **k
    )


# ---------------------------------------------------------------------------
# TARJETAS FLUIDAS
# ---------------------------------------------------------------------------

ESTILO_TARJETAS = """
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700&family=JetBrains+Mono:wght@600;700&display=swap');
*{ box-sizing:border-box; }
body{
  margin:0; padding:0; background:transparent; font-family:'Libre Franklin',system-ui,sans-serif;
  --negro:#0A0A0A; --rojo:#D1122E; --texto:#1A1A1A; --suave:#555555;
  --linea:#E2E8F0; --gris:#F1F5F9;
  color:var(--texto); overflow:hidden;
}
.rejilla{
  display:grid; grid-template-columns:repeat(2,1fr);
  gap:6px; align-items:stretch;
}
@media (max-width:760px){ .rejilla{ grid-template-columns:1fr; } }

.tarjeta{
  background:#fff; border:1px solid var(--linea); border-left:4px solid #CBD5E1;
  border-radius:4px; padding:6px 12px; display:flex; flex-direction:column;
  justify-content:space-between; transition:transform .12s ease, box-shadow .12s ease;
  box-shadow:0 1px 3px rgba(0,0,0,0.03); cursor:pointer;
}
.tarjeta:hover{
  transform:translateY(-1px); box-shadow:0 3px 8px rgba(0,0,0,0.07); border-color:#CBD5E1;
}
.tarjeta.top{
  border-left-color:var(--rojo); background:#FFFFFF;
  box-shadow:0 2px 6px rgba(209,18,46,0.06);
}
.tarjeta.relleno{
  background:#FAFAFA; border-left-color:#E2E8F0; opacity:.92;
}

.fila{
  display:flex; align-items:center; justify-content:space-between;
  gap:8px; margin-bottom:2px;
}
.identificador{ display:flex; align-items:center; gap:8px; }
.orden{
  font-size:clamp(0.66rem, 0.72vw, 0.72rem); font-weight:700; color:var(--suave);
  font-family:'JetBrains Mono',monospace;
}
.codigo{
  font-size:clamp(1.05rem, 1.18vw, 1.2rem); font-weight:700;
  letter-spacing:.03em; color:var(--negro); font-family:'JetBrains Mono',monospace;
}

.copiar{
  font-family:'Libre Franklin',sans-serif; font-size:clamp(0.68rem, 0.74vw, 0.74rem);
  font-weight:600; color:var(--texto); background:#fff; border:1px solid #C4C4C4;
  border-radius:3px; padding:.2rem .6rem; cursor:pointer;
  transition:all .15s ease; white-space:nowrap;
}
.copiar:hover{ background:var(--negro); color:#fff; border-color:var(--negro); }
.copiar.hecho{ background:var(--rojo); border-color:var(--rojo); color:#fff; }

.denominacion{
  font-size:clamp(0.85rem, 0.94vw, 0.92rem); font-weight:600;
  line-height:1.25; color:var(--texto); margin:0 0 2px;
}
.motivo{
  font-size:clamp(0.74rem, 0.82vw, 0.8rem); color:var(--suave);
  line-height:1.24; margin-bottom:3px;
}

.etiquetas-fila{
  display:flex; align-items:center; gap:5px; flex-wrap:wrap; margin-top:auto; padding-top:2px;
}
.etiqueta{
  display:inline-flex; align-items:center; font-size:clamp(0.58rem, 0.65vw, 0.64rem);
  font-weight:700; letter-spacing:.06em; text-transform:uppercase;
  padding:.12rem .4rem; border-radius:3px; background:var(--gris); color:var(--suave);
}
.etiqueta.recomendada{ background:var(--rojo); color:#fff; }
.etiqueta.mando{ background:#FFF7ED; color:#C2410C; border:1px solid #FFEDD5; }
"""

GUION_INTERACTIVO = """
function copiarTexto(texto, boton){
  navigator.clipboard.writeText(texto).then(() => {
    boton.textContent = 'Copiado';
    boton.classList.add('hecho');
    setTimeout(() => { boton.textContent = 'Copiar'; boton.classList.remove('hecho'); }, 1400);
  }).catch(() => {
    const caja = document.createElement('textarea');
    caja.value = texto;
    document.body.appendChild(caja);
    caja.select();
    document.execCommand('copy');
    document.body.removeChild(caja);
    boton.textContent = 'Copiado';
    boton.classList.add('hecho');
    setTimeout(() => { boton.textContent = 'Copiar'; boton.classList.remove('hecho'); }, 1400);
  });
}

function alto(){
  // El alto del marco lo fija Python, que no sabe el ancho de la pantalla:
  // calcula el caso peor (una columna) y aqui se ajusta al real. Se mide la
  // rejilla y no el documento, porque scrollHeight nunca baja del alto del
  // propio marco y asi no se podria encoger.
  const rejilla = document.querySelector('.rejilla');
  if (!rejilla) return;
  const h = Math.ceil(rejilla.getBoundingClientRect().height) + 2;

  // srcdoc: el marco es del mismo origen que la pagina, asi que se puede
  // tocar. El postMessage de abajo solo lo escuchan los componentes
  // declarados con declare_component, no components.html.
  try {
    const marco = window.frameElement;
    if (marco && Math.abs(marco.getBoundingClientRect().height - h) > 1) {
      // Con prioridad: el alto de arranque entra por media query, que si no
      // le ganaria a un estilo en linea normal y el ajuste no serviria.
      marco.style.setProperty('height', h + 'px', 'important');
      // Streamlit le pasa el alto al contenedor, y no como 'height' sino
      // como flex-basis: el contenedor es un hijo flexible en columna, asi
      // que manda la base y no la altura. Tocando solo 'height' el marco
      // encogia pero el hueco se quedaba.
      const caja = marco.parentElement;
      if (caja) {
        caja.style.setProperty('height', h + 'px', 'important');
        caja.style.setProperty('flex', '0 0 ' + h + 'px', 'important');
      }
    }
  } catch (e) {
    // Si algun dia deja de ser del mismo origen queda el alto de Python:
    // sobrara espacio debajo, pero no se cortara ninguna tarjeta.
  }
  parent.postMessage({type:'streamlit:setFrameHeight', height: h}, '*');
}

document.querySelectorAll('.copiar').forEach(b => {
  b.addEventListener('click', (e) => {
    e.stopPropagation();
    copiarTexto(b.dataset.cod, b);
  });
});

document.querySelectorAll('.tarjeta').forEach(t => {
  t.addEventListener('click', () => {
    const btn = t.querySelector('.copiar');
    if (btn) btn.click();
  });
});

window.addEventListener('keydown', (e) => {
  if (['1','2','3','4','5','6'].includes(e.key) && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) {
    const idx = parseInt(e.key) - 1;
    const btns = document.querySelectorAll('.copiar');
    if (btns[idx]) btns[idx].click();
  }
});

// Se vigila la rejilla, no el body: el body no encoge por debajo del alto
// del marco y el observador nunca se enteraria de que sobra sitio.
const observador = new ResizeObserver(() => alto());
const rejilla = document.querySelector('.rejilla');
if (rejilla) observador.observe(rejilla);
window.addEventListener('load', alto);
window.addEventListener('resize', alto);
alto();
"""


def pinta_tarjetas(ocupaciones):
    if not ocupaciones:
        return

    trozos = []
    for i, o in enumerate(ocupaciones, 1):
        es_primera = (i == 1 and not o.get("provisional"))
        es_mando = o.get("nivel") in ("10", "20", "30")

        clases = ["tarjeta"]
        if es_primera:
            clases.append("top")
        if o.get("relleno"):
            clases.append("relleno")
        clase = " ".join(clases)

        etiquetas_html = []
        if es_primera:
            etiquetas_html.append('<span class="etiqueta recomendada">★ Recomendada</span>')

        etiqueta_clase = "etiqueta mando" if es_mando else "etiqueta"
        etiquetas_html.append(
            f'<span class="{etiqueta_clase}">Nivel {o["nivel"]} &middot; {o["nivel_texto"]}</span>'
        )

        motivo_html = f'<div class="motivo">{o["motivo"]}</div>' if o.get("motivo") else ""

        trozos.append(
            f'<div class="{clase}">'
            f'  <div>'
            f'    <div class="fila">'
            f'      <div class="identificador">'
            f'        <span class="orden">{i:02d}</span>'
            f'        <span class="codigo">{o["codigo"]}</span>'
            f'      </div>'
            f'      <button class="copiar" data-cod="{o["codigo"]}">Copiar</button>'
            f'    </div>'
            f'    <div class="denominacion">{o["denominacion"]}</div>'
            f'    {motivo_html}'
            f'  </div>'
            f'  <div class="etiquetas-fila">{"".join(etiquetas_html)}</div>'
            f'</div>'
        )

    # El alto del marco se fija desde Python, y aqui no se sabe el ancho de la
    # pantalla. Se calculan tres, uno por tramo, y los elige el CSS de abajo:
    # el de escritorio va en el propio componente y los otros dos entran por
    # media query. El guion de dentro ajusta luego al alto exacto, pero si
    # aqui se manda un solo numero el otro lado da un salto de medio metro de
    # pantalla mientras carga. Antes se calculaba siempre a dos columnas y en
    # el movil, donde las tarjetas se apilan, el marco se quedaba a la mitad:
    # la segunda tarjeta no se veia y la primera salia cortada.
    #
    # Los caracteres por linea estan medidos sobre el catalogo entero: son el
    # mayor valor con el que la cuenta nunca se queda corta de lineas.
    ALTO_FIJO = 58                 # codigo, boton, etiquetas y margenes
    ALTO_LINEA_DENOMINACION = 17
    ALTO_LINEA_MOTIVO = 15
    SEPARACION = 6                 # el gap de la rejilla

    def estima(caracteres_denom, caracteres_motivo, columnas):
        def mide(o):
            lineas_denom = max(1, math.ceil(len(o["denominacion"]) / caracteres_denom))
            lineas_motivo = (math.ceil(len(o["motivo"]) / caracteres_motivo)
                             if o.get("motivo") else 0)
            return (ALTO_FIJO
                    + lineas_denom * ALTO_LINEA_DENOMINACION
                    + lineas_motivo * ALTO_LINEA_MOTIVO)

        alturas = [mide(o) for o in ocupaciones]
        filas = [alturas[i:i + columnas] for i in range(0, len(alturas), columnas)]
        return sum(max(f) for f in filas) + SEPARACION * max(0, len(filas) - 1) + 4

    escritorio = estima(48, 52, 2)       # dos columnas de unos 530 px
    columna_ancha = estima(50, 100, 1)   # tableta o ventana estrecha
    movil = estima(20, 38, 1)            # una columna y el texto ocupando más

    components.html(
        f"<style>{ESTILO_TARJETAS}</style>"
        f"<div class=\"rejilla\">{''.join(trozos)}</div>"
        f"<script>{GUION_INTERACTIVO}</script>",
        height=escritorio,
    )
    # El marco de las tarjetas es el unico de la pagina, asi que no hace falta
    # marcarlo: 792 px de ventana son 760 de marco, que es donde la rejilla de
    # dentro pasa a una columna. Se toca tambien flex-basis porque Streamlit le
    # pasa el alto al contenedor por ahi y no por 'height'.
    st.markdown(
        "<style>"
        + "".join(
            f"@media (max-width:{ventana}px){{"
            f"iframe.stIFrame,"
            f"div[data-testid=\"stElementContainer\"]:has(> iframe.stIFrame)"
            f"{{height:{px}px !important;flex-basis:{px}px !important;}}}}"
            for ventana, px in ((792, columna_ancha), (552, movil))
        )
        + "</style>",
        unsafe_allow_html=True,
    )


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

    # 1. PREGUNTA ARRIBA (antes de las tarjetas)
    if payload.get("pregunta"):
        try:
            caja = st.container(key="pregunta")
        except TypeError:
            caja = st.container()
        with caja:
            st.markdown(
                '<div class="pregunta-titulo">Pregunta para la persona</div>'
                f'<div class="pregunta-texto">{payload["pregunta"]}</div>',
                unsafe_allow_html=True,
            )
            if interactivo:
                opciones = motor.extraer_opciones(payload.get("pregunta", ""), payload.get("opciones"))
                # El ancho se reparte segun lo que ocupa cada texto. Con el
                # limite en 44 caracteres hace falta algo mas de holgura que
                # antes, o el boton vuelve a cortar la frase por su cuenta.
                pesos = [max(1.2, len(opc) * 0.105) for opc in opciones]
                spacer = max(0.2, (9.0 - sum(pesos)) / 2.0)
                col_weights = [spacer] + pesos + [spacer]
                cols = st.columns(col_weights, gap="small")
                for idx, opc in enumerate(opciones):
                    with cols[idx + 1]:
                        if st.button(opc, key=f"resp_opt_{idx}", use_container_width=True):
                            st.session_state["sispe_respuesta"] = (consulta, payload["pregunta"], opc)
                            st.rerun()

    # 2. TARJETAS DE OCUPACIONES
    pinta_tarjetas(ocupaciones)

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
        for trozo in modelo.flujo_modelo(cli, texto + contexto, candidatos):
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
    with st.popover(":material/tune:", use_container_width=True):
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

        if not MANTENIMIENTO:
            st.caption(
                f"{len(motor.IDX['registros'])} ocupaciones del catálogo oficial. "
                "Describe solo el puesto: sin datos identificativos."
            )
            st.caption(f"Versión {version.commit()}")
            return
        st.caption(f"Versión {version.commit()}")

        tiempos = st.session_state.get("sispe_tiempos", [])
        if tiempos:
            st.caption("Última consulta, segundo a segundo:")
            for etiqueta, seg in tiempos:
                st.caption(f"· {etiqueta}: **{seg:.1f} s**")
            st.caption(f"· Total esperando al modelo: **{sum(t for _, t in tiempos):.1f} s**")

        if st.button("Probar la conexión con la IA", use_container_width=True):
            correcto, detalle = ia.prueba()
            (st.success if correcto else st.error)(detalle)

        if gist.activo():
            st.markdown("**Diccionario compartido**")
            st.caption(f"{len(aprendizaje.lexico())} términos aprendidos.")
            if st.button("Comprobar que guarda", use_container_width=True):
                correcto, detalle = aprendizaje.prueba()
                (st.success if correcto else st.error)(detalle)


def usar_ejemplo(texto_ejemplo):
    st.session_state["sispe_pendiente"] = texto_ejemplo
    st.session_state["consulta"] = ""
    st.session_state["sispe_actual"] = None
    st.session_state["sispe_ultima"] = ""


def botones_carrito(ocupaciones):
    """Botones reales bajo las tarjetas: mandan la ocupación al generador de CV.

    No pueden ir dentro: las tarjetas se dibujan con components.html, en un
    marco aislado, y un botón de ahí dentro no puede avisar a la aplicación.
    Es la conexión entre las dos herramientas: pasa por `herramientas.cv.estado`.
    """
    if not ocupaciones:
        return
    # La clave la usa el CSS de comun/estilo.py: en el movil, donde Streamlit
    # apila las columnas, invierte cada fila para que el nombre vaya ENCIMA de
    # su boton. Sin eso el boton salia primero, pegado al nombre del anterior,
    # y no se sabia a cual de los dos pertenecia.
    try:
        zona = st.container(key="carrito")
    except TypeError:
        zona = st.container()
    with zona:
        st.markdown('<div class="seccion">Añadir al currículo</div>', unsafe_allow_html=True)
        for o in ocupaciones:
            ya = cv_estado.en_lista(o["codigo"])
            boton, texto = st.columns([1.5, 8.5], gap="small")
            boton.button(
                "Añadido" if ya else "+ CV",
                key=f"addcv_{o['codigo']}", use_container_width=True, disabled=ya,
                type="secondary" if ya else "primary",
                on_click=cv_estado.anade_experiencia,
                args=(o["codigo"], o["denominacion"], o.get("motivo", "")),
            )
            # El nombre oficial manda, pero entre parentesis va como se llamaria
            # el puesto en un curriculo. De momento sale de convertir la
            # denominacion; el nombre de mercado de verdad ("montador de placa
            # de pladur") lo tiene que proponer el modelo, y eso va en el paso
            # siguiente.
            sugerencia = cv_motor.a_oracion(o["denominacion"])
            texto.markdown(
                f'<div style="padding-top:.35rem;line-height:1.3">'
                f'<span style="font-size:.82rem;font-weight:600">{o["denominacion"]}</span><br>'
                f'<span style="font-size:.78rem;color:var(--suave)">'
                f'En el currículo: <b>{sugerencia}</b> · {o["codigo"]}</span></div>',
                unsafe_allow_html=True,
            )
        n = len(cv_estado.experiencias())
        if n:
            st.page_link(
                cv_estado.PAGINA, icon=":material/description:",
                label=f"Abrir el generador de CV ({n} experiencia{'s' if n != 1 else ''})",
            )


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
# Banda de cabecera
# ---------------------------------------------------------------------------

banda = estilo.banda(
    "sispe", "Codificador de ocupaciones",
    "Describe el puesto con las palabras de la persona y te propone el código oficial.",
    al_pulsar_titulo=empezar_de_nuevo,
)
with banda:
    campo, boton, ajustes = st.columns([6.4, 1.1, 0.5], gap="small")
    with campo:
        texto = st.text_input(
            "Consulta", label_visibility="collapsed", key="consulta",
            placeholder="Describe el puesto o introduce un código de 8 cifras...",
        )
    with boton:
        buscar = st.button("Buscar", key="buscar", use_container_width=True)
    with ajustes:
        panel_ajustes()

    escrito = (texto or "").strip()
    if escrito and not entrada:
        if buscar or escrito != st.session_state.get("sispe_ultima", ""):
            entrada = escrito
            contexto, busqueda, rotulo = "", None, None

if entrada:
    st.session_state["sispe_ultima"] = entrada

# ---------------------------------------------------------------------------
# Cuerpo
# ---------------------------------------------------------------------------

if entrada:
    st.markdown(
        f'<div class="consulta-box"><div class="consulta-texto">{rotulo or entrada}</div></div>',
        unsafe_allow_html=True,
    )
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
    st.markdown(
        f'<div class="consulta-box"><div class="consulta-texto">{consulta}</div></div>',
        unsafe_allow_html=True,
    )
    pinta_resultado(payload, interactivo=True, consulta=consulta)
    botones_carrito(payload.get("ocupaciones", []))

    st.markdown('<div class="separa"></div>', unsafe_allow_html=True)
    st.button("↺", key="reinicio", help="Nueva búsqueda", on_click=empezar_de_nuevo)
    st.markdown('<div class="pie-nueva">Nueva búsqueda</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="seccion">Prueba con</div>', unsafe_allow_html=True)
    arranque = "Una persona que "
    # La clave la usa el CSS de comun/estilo.py para dejar que estos rotulos
    # pasen a dos lineas: en un movil estrecho no cabian y Streamlit los
    # cortaba con puntos suspensivos ("...organiza eventos para e...").
    try:
        zona_ej = st.container(key="ejemplos")
    except TypeError:
        zona_ej = st.container()
    with zona_ej:
        for i in range(0, len(EJEMPLOS), 2):
            fila = EJEMPLOS[i:i + 2]
            cols = st.columns(2, gap="small")
            for col, ej in zip(cols, fila):
                rotulo_ej = (
                    f"{arranque}**{ej[len(arranque):]}**"
                    if ej.startswith(arranque) else f"**{ej}**"
                )
                col.button(
                    rotulo_ej, use_container_width=True, key=f"ej_{i}_{ej[-14:]}",
                    on_click=usar_ejemplo, args=(ej,),
                )

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
