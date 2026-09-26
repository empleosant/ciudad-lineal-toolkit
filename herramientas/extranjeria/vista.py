"""
Codificador de extranjería: la pantalla.

Qué código de autorización y qué fecha fin de vigencia se graban al inscribir
a una persona extranjera. Es el Excel de la oficina («CÓDIGOS Autorizaciones
extranjería», septiembre 2026) hecho pantalla: la lógica está en `motor.py`
(Python puro, sin Streamlit) y los datos en `datos/`, que salen del Excel con
`scripts/extraer_extranjeria.py`.

Tres pestañas: «¿Qué código es?» (el árbol de decisión), «Consultar un
código» (la tabla) y «Plazos de la demanda» (cuándo toca renovar). Lo
obligatorio a la vista; lo de consulta, plegado. Se usa en el mostrador con
la tarjeta en la mano, muchas veces desde el móvil: tres desplegables y dos
fechas caben en una pantalla de teléfono.

No usa IA. Claves de sesión con prefijo `ext_`; las de widgets, `ext_w_`.
"""

from datetime import date

import streamlit as st

from comun import estilo
from comun.texto import esc as e
from herramientas.extranjeria import motor

MIN_FECHA = date(1930, 1, 1)
MAX_FECHA = date(2200, 12, 31)
TIE = "TIE (tarjeta de identidad de extranjero)"

estilo.aplica()
st.markdown("""
<style>
.ext-codigo{ font-size:2.1rem; font-weight:700; letter-spacing:-.02em; line-height:1.1; }
.ext-codigo.largo{ font-size:1.15rem; line-height:1.3; }
.ext-codigo.no{ color:var(--rojo); }
.ext-aviso{ font-size:.86rem; line-height:1.45; padding:.5rem .7rem; border-radius:6px;
            margin:.3rem 0; border:1px solid var(--linea); }
.ext-aviso.rojo{ background:#FEF2F2; border-color:#FECACA; color:#991B1B; }
.ext-aviso.ambar{ background:#FFF7ED; border-color:#FFEDD5; color:#9A3412; }
.ext-aviso.gris{ background:var(--gris); color:var(--suave); }
.ext-ficha .l{ font-size:.68rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
               color:var(--suave); margin:.6rem 0 .1rem; }
.ext-ficha .v{ font-size:.88rem; line-height:1.45; }
.ext-tabla{ width:100%; border-collapse:collapse; font-size:.8rem; margin:.3rem 0 .6rem; }
.ext-tabla th{ text-align:left; font-size:.64rem; letter-spacing:.1em; text-transform:uppercase;
               color:var(--suave); border-bottom:1px solid var(--linea); padding:.3rem .4rem; }
.ext-tabla td{ vertical-align:top; padding:.35rem .4rem; border-bottom:1px solid var(--linea); line-height:1.4; }
.ext-tabla td:first-child{ font-weight:600; white-space:nowrap; }
.ext-pie{ font-size:.78rem; color:var(--tenue); line-height:1.45; margin-top:1.2rem; }
</style>
""", unsafe_allow_html=True)



def tarjeta(rotulo, valor, nota=""):
    st.markdown(
        f'<div class="estado-doc"><div class="l">{e(rotulo)}</div>'
        f'<div class="g" style="font-size:1.15rem">{e(valor)}</div>'
        + (f'<div class="n">{e(nota)}</div>' if nota else "") + "</div>",
        unsafe_allow_html=True,
    )


def aviso(texto, tono):
    st.markdown(f'<div class="ext-aviso {tono}">{e(texto)}</div>', unsafe_allow_html=True)


def tono_de(texto):
    """Rojo para lo que impide inscribir; ámbar para lo que hay que mirar."""
    t = texto.lower()
    if "⚠" in texto or "fuera de plazo" in t or "no sirve" in t or "no se puede inscribir" in t:
        return "rojo"
    return "ambar"


def tabla(cabeceras, filas):
    cab = "".join(f"<th>{e(c)}</th>" for c in cabeceras)
    cuerpo = "".join("<tr>" + "".join(f"<td>{e(v)}</td>" for v in f) + "</tr>" for f in filas)
    st.markdown(f'<table class="ext-tabla"><thead><tr>{cab}</tr></thead><tbody>{cuerpo}</tbody></table>',
                unsafe_allow_html=True)


def ficha(codigo):
    f = motor.consulta(codigo)
    if not f:
        return
    st.markdown(f'<div class="ext-ficha"><div class="l">Qué es</div><div class="v">{e(f["que_es"])}</div>'
                f'<div class="l">Grupo</div><div class="v">{e(f["grupo"])}</div></div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        tarjeta("¿Puede trabajar?", f["puede_trabajar"])
    with c2:
        tarjeta("Restricción", f["restriccion"])
    with c3:
        tarjeta("Colectivo", f["colectivo"])
    partes = [("Se inscribe con", f["se_inscribe_con"]),
              ("Fecha fin de vigencia a grabar", f["fecha_fin"]),
              ("Ojo / claves", f["ojo"])]
    st.markdown('<div class="ext-ficha">' + "".join(
        f'<div class="l">{e(r)}</div><div class="v">{e(v)}</div>' for r, v in partes if v
    ) + "</div>", unsafe_allow_html=True)


def fecha(etiqueta, clave, col=st, valor=None):
    return col.date_input(etiqueta, value=valor, format="DD/MM/YYYY", key=clave,
                          min_value=MIN_FECHA, max_value=MAX_FECHA)


# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------

estilo.banda(
    "extranjeria", "Codificador de extranjería",
    "Qué código de autorización y qué fecha fin de vigencia se graban al inscribir "
    "a una persona extranjera. Datos de septiembre de 2026.",
)

que_codigo, consultar, plazos = st.tabs(["¿Qué código es?", "Consultar un código", "Plazos de la demanda"])

# ---------------------------------------------------------------------------
# 1 · ¿Qué código es?
# ---------------------------------------------------------------------------

with que_codigo:
    izq, der = st.columns([5, 6], gap="large")
    with izq:
        st.markdown('<div class="seccion">1 · Qué trae y qué pone</div>', unsafe_allow_html=True)
        documento = st.selectbox("Documento", motor.NOMBRES_DOCUMENTOS, index=None,
                                 placeholder="Elige el documento", key="ext_w_documento")
        opcion = st.selectbox("Qué pone", motor.opciones(documento) if documento else [],
                              index=None, placeholder="Elige qué pone el documento",
                              key="ext_w_opcion", disabled=not documento)
        if documento:
            st.caption("Dónde mirar: " + motor.donde_mirar(documento))

        st.markdown('<div class="seccion">2 · Fechas (las que traiga el documento)</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        emision = fecha("Emisión / presentación", "ext_w_emision", c1)
        valido_hasta = fecha("Válido hasta", "ext_w_valido", c2)
        nacimiento = fecha("Fecha de nacimiento", "ext_w_nacimiento", c1)
        solicitud = fecha("Solicitud de renovación", "ext_w_solicitud", c2)
        sin_alta = False
        if documento == motor.DOC_RESOLUCION:
            sin_alta = st.radio("¿La resolución condiciona expresamente la autorización al alta en la Seguridad Social, y aún no la hay?",
                                ["No", "Sí"], horizontal=True, key="ext_w_alta") == "Sí"
        with st.expander("Otra fecha de referencia"):
            hoy = fecha("Hoy", "ext_w_hoy", valor=date.today())

    r = motor.codifica(documento, opcion, emision=emision, valido_hasta=valido_hasta,
                       nacimiento=nacimiento, solicitud_renovacion=solicitud,
                       sin_alta_ss=sin_alta, hoy=hoy)

    with der:
        st.markdown('<div class="seccion">Resultado</div>', unsafe_allow_html=True)
        if not r.valido:
            st.markdown(f'<div class="estado-doc"><div class="l">Código</div>'
                        f'<div class="ext-codigo largo" style="color:var(--tenue)">{e(r.mensaje)}</div></div>',
                        unsafe_allow_html=True)
        else:
            clase = "ext-codigo" + ("" if len(r.codigo) <= 16 else " largo") + \
                    (" no" if r.codigo == motor.NO_SE_INSCRIBE else "")
            que_es = r.ficha.get("que_es", "") if r.ficha else ""
            st.markdown(f'<div class="estado-doc"><div class="l">Código</div>'
                        f'<div class="{clase}">{e(r.codigo)}</div>'
                        + (f'<div class="n">{e(que_es)}</div>' if que_es else "") + "</div>",
                        unsafe_allow_html=True)
            if r.se_inscribe:
                c1, c2 = st.columns(2, gap="small")
                with c1:
                    tarjeta("¿Puede trabajar?", r.puede_trabajar or "—")
                    tarjeta("Restricción · colectivo",
                            (f"Restricción {r.restriccion}" if r.restriccion else "—"),
                            (f"Colectivo: {r.colectivo}" if r.colectivo else ""))
                with c2:
                    tarjeta("Fecha fin a grabar", r.fecha_fin_texto or "—")
                    if r.datos:
                        tarjeta("Lo que dicen las fechas", " · ".join(r.datos))
            for a in r.avisos:
                aviso(a, tono_de(a))
            for n in r.notas:
                aviso(n, "gris")
            if not r.avisos and not r.notas:
                aviso("Nada especial.", "gris")
            if r.ficha:
                with st.expander("Más detalle del código"):
                    ficha(r.codigo)

    st.markdown(f'<div class="ext-pie">{e(motor.NOTAS["aviso"])}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2 · Consultar un código
# ---------------------------------------------------------------------------

with consultar:
    codigo = st.selectbox("Código", motor.NOMBRES_CODIGOS, index=None,
                          placeholder="Elige el código", key="ext_w_codigo")
    if codigo:
        ficha(codigo)
    st.caption(" · ".join(f"{k}: {v}" for k, v in motor.NOTAS["leyenda"]))

    with st.expander("Solicitudes en trámite: qué se inscribe y qué no"):
        st.markdown('<div class="seccion">Se puede inscribir aunque esté en trámite</div>',
                    unsafe_allow_html=True)
        tabla(["Situación", "Código", "Cómo se graba"],
              [(t["situacion"], t["codigo"], t["como_se_graba"]) for t in motor.TRAMITE if t["apartado"] == "SI"])
        st.markdown('<div class="seccion">No se puede inscribir (para ningún servicio)</div>',
                    unsafe_allow_html=True)
        for t in motor.TRAMITE:
            if t["apartado"] == "NO":
                st.markdown(f"- {t['situacion']}")
        for n in motor.NOTAS["tramite"]:
            st.caption(n)

    with st.expander("Qué pone la tarjeta (TIE) y qué código suele ser"):
        st.caption(motor.NOTAS["textos_tie"])
        tabla(["Dónde", "Texto", "Código", "Ojo", "Fuente"],
              [(t["donde"], t["texto"], t["codigo"], t["ojo"], t["fuente"]) for t in motor.TEXTOS_TIE])

    with st.expander("Enlaces, teléfonos y oficinas"):
        apartado = None
        for en in motor.ENLACES:
            if en["apartado"] != apartado:
                apartado = en["apartado"]
                st.markdown(f'<div class="seccion">{e(apartado)}</div>', unsafe_allow_html=True)
            dato = en["dato"]
            if dato.startswith("http"):
                st.markdown(f"- {en['nombre']}: [{dato}]({dato})")
            else:
                st.markdown(f"- {en['nombre']}: {dato}")

    with st.expander(motor.NOTAS["novedades"].capitalize()):
        tabla(["Código", "Qué cambia"], [(n["codigo"], n["cambio"]) for n in motor.NOVEDADES])

    st.markdown(f'<div class="ext-pie">{e(motor.NOTAS["fuente"])}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3 · Plazos de la demanda
# ---------------------------------------------------------------------------

with plazos:
    st.markdown('<div class="seccion">¿Cuándo toca la próxima renovación de la demanda?</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="small")
    hoy_p = fecha("Fecha en que renueva hoy la demanda", "ext_w_p_hoy", c1, date.today())
    fin_p = fecha("Fin de vigencia de la autorización", "ext_w_p_fin", c2)
    sol_p = fecha("Solicitud de renovación de la autorización (si la hay)", "ext_w_p_sol", c3)
    if fin_p:
        p = motor.plazos_demanda(hoy_p, fin_p, sol_p)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            tarjeta("Próxima renovación", p.proxima.strftime("%d/%m/%Y"), p.tipo)
        with c2:
            if sol_p:
                tarjeta("Solicitud de renovación",
                        "En plazo" if p.en_plazo else "FUERA de plazo (60 días antes / 90 después)",
                        ("Más de 3 meses: certificado de silencio positivo o consultar el expediente"
                         if p.mas_de_tres_meses else ""))
            else:
                tarjeta("Límite por la autorización", p.limite.strftime("%d/%m/%Y"),
                        "Fin de vigencia + 7 días")
        if p.tipo != "Normal":
            aviso(p.tipo, "ambar")
    else:
        st.caption("Rellena el fin de vigencia y sale la fecha.")

    with st.expander("Cómo se calcula, y las causas de baja"):
        for n in motor.NOTAS["plazos"]:
            st.markdown(f"- {n}")
        tabla(["Causa de baja", "Código"], [(b["causa"], b["codigo"]) for b in motor.BAJAS])

    with st.expander("Reglas de fecha fin de vigencia por supuesto"):
        tabla(["Supuesto", "Código", "Regla"], [(p["supuesto"], p["codigo"], p["regla"]) for p in motor.PLAZOS])

    with st.expander("Cuánto suele durar la tarjeta, por código"):
        for n in motor.NOTAS["duraciones_tarjeta"]:
            st.caption(n)
        tabla(["Duración", "Códigos compatibles"],
              [(d["duracion"], d["codigos"]) for d in motor.DURACIONES_TARJETA])
