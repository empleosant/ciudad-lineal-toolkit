"""
Batería del codificador de extranjería.

El motor traduce las fórmulas del Excel de códigos de autorizaciones a
Python. Lo que se comprueba aquí es que la traducción es fiel y que no se
rompe por lo bajo:

  · los casos de `casos_extranjeria.csv`, uno a uno;
  · que las 82 opciones responden sin excepción y con códigos que existen;
  · que las fechas se suman como en Excel (EDATE, DATEDIF);
  · la calculadora de plazos de la demanda, con el ejemplo del Excel;
  · que el motor no importa Streamlit;
  · y la pantalla: que elegir el documento cambia la lista de «qué pone».

`casos_extranjeria.csv` SOLO SE EDITA A MANO, con el resultado comprobado
contra la tabla comentada de autorizaciones (junio 2026) o contra la regla
del Excel, nunca copiado de lo que conteste el motor. Los 37 primeros los
dedujo Claude de las reglas el 26/09/2026 y llevan en «fuente» dónde
comprobarlos: están pendientes de que la oficina los revise.

USO
    python3 extranjeria.py            # todo menos la pantalla vale con el python3 del sistema
    ~/.venvs/sispe/bin/python extranjeria.py     # también la pantalla (AppTest)

No llama a la IA ni gasta cuota: el codificador no la usa.
"""

import csv
import os
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

if "streamlit" in sys.modules:
    del sys.modules["streamlit"]
from herramientas.extranjeria import motor  # noqa: E402

if "streamlit" in sys.modules:
    sys.exit("El motor ha importado Streamlit. Tiene que ser Python puro: lo que\n"
             "necesite Streamlit va en vista.py, no en motor.py.")

CASOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "casos_extranjeria.csv")
RESUMEN = []


def informe(nombre, fallos, total):
    pasa = not fallos
    RESUMEN.append((nombre, pasa))
    print(f"[{' OK ' if pasa else 'MAL'}] {nombre:52} {total - len(fallos):2}/{total}")
    for f in fallos:
        print(f"          · {f}")
    return pasa


def _f(texto):
    return motor._fecha(texto) if texto else None


def p_los_casos():
    """Cada fila del CSV: código, fecha fin, puede trabajar y un trozo de aviso."""
    with open(CASOS, encoding="utf-8", newline="") as f:
        casos = list(csv.DictReader(f))
    fallos = []
    for c in casos:
        try:
            r = motor.codifica(
                c["documento"], c["opcion"],
                emision=_f(c["emision"]), valido_hasta=_f(c["valido_hasta"]),
                nacimiento=_f(c["nacimiento"]), solicitud_renovacion=_f(c["solicitud_renovacion"]),
                sin_alta_ss=(c["sin_alta_ss"] == "Sí"), hoy=_f(c["hoy"]),
            )
        except Exception as e:  # noqa: BLE001
            fallos.append(f"{c['caso']}: {type(e).__name__}: {e}")
            continue
        if not r.valido:
            fallos.append(f"{c['caso']}: el motor no reconoce la opción ({r.mensaje})")
            continue
        if r.codigo != c["codigo"]:
            fallos.append(f"{c['caso']}: código {r.codigo!r}, esperado {c['codigo']!r}")
        if r.fecha_fin_texto != c["fecha_fin"]:
            fallos.append(f"{c['caso']}: fecha fin {r.fecha_fin_texto!r}, esperada {c['fecha_fin']!r}")
        if r.puede_trabajar != c["puede_trabajar"]:
            fallos.append(f"{c['caso']}: puede trabajar {r.puede_trabajar!r}, esperado {c['puede_trabajar']!r}")
        todo = " ".join(r.avisos + r.notas)
        if c["aviso_contiene"] and c["aviso_contiene"] not in todo:
            fallos.append(f"{c['caso']}: falta el aviso «{c['aviso_contiene']}» en {todo[:90]!r}")
    return informe(f"Los {len(casos)} casos de casos_extranjeria.csv", fallos, len(casos))


def p_todas_las_opciones_responden():
    """Las 82 opciones, con fechas verosímiles, sin excepción y con código de la tabla."""
    fallos = []
    hoy = date(2026, 9, 26)
    juegos = [
        dict(),
        dict(emision=date(2026, 1, 10), valido_hasta=date(2027, 1, 10), nacimiento=date(1990, 5, 5)),
        dict(emision=date(2022, 1, 10), valido_hasta=date(2024, 1, 10), nacimiento=date(2009, 5, 5),
             solicitud_renovacion=date(2024, 2, 1), sin_alta_ss=True),
    ]
    for doc in motor.NOMBRES_DOCUMENTOS:
        for opcion in motor.opciones(doc):
            for juego in juegos:
                try:
                    r = motor.codifica(doc, opcion, hoy=hoy, **juego)
                except Exception as e:  # noqa: BLE001
                    fallos.append(f"{doc[:20]} / {opcion[:40]}: {type(e).__name__}: {e}")
                    continue
                if not r.valido or not r.codigo:
                    fallos.append(f"{doc[:20]} / {opcion[:40]}: sin código")
                tipo = r.regla.get("tipo")
                if tipo in ("FIX",) and r.codigo not in motor._FICHA and r.codigo != "IC":
                    fallos.append(f"{opcion[:40]}: el código {r.codigo!r} no está en codigos.csv")
                if tipo in ("DUR", "EDAD18", "REAG") and juego and r.codigo not in motor._FICHA:
                    fallos.append(f"{opcion[:40]}: el código {r.codigo!r} no está en codigos.csv")
    n = sum(len(motor.opciones(d)) for d in motor.NOMBRES_DOCUMENTOS)
    return informe(f"Las {n} combinaciones documento/opción responden", fallos, n)


def p_los_datos_estan_enteros():
    """Que el script de extracción no se ha dejado nada por el camino."""
    fallos = []
    listas = {r["lista"] for r in motor.REGLAS}
    for d in motor.DOCUMENTOS:
        if d["lista"] not in listas:
            fallos.append(f"el documento «{d['documento']}» apunta a la lista {d['lista']}, que no existe")
    for codigo in motor.DURACIONES:
        if codigo not in motor._FICHA:
            fallos.append(f"duraciones.csv tiene {codigo!r}, que no está en codigos.csv")
    for r in motor.REGLAS:
        if r["tipo"] not in ("GEN", "FIX", "DUR", "EDAD18", "REAG", "PIMES", "NO", "PREV", "MSG"):
            fallos.append(f"tipo de regla desconocido {r['tipo']!r} en «{r['opcion'][:40]}»")
        if r["vigencia"] not in ("DOC", "2200", "E2M", "E3M", "E5Y", "H180", "NAC", "V1M", "PREV", "NA"):
            fallos.append(f"regla de vigencia desconocida {r['vigencia']!r} en «{r['opcion'][:40]}»")
    if len(motor.DOCUMENTOS) != 7:
        fallos.append(f"{len(motor.DOCUMENTOS)} documentos, y el Excel tiene 7")
    if not motor.TRAMITE or not motor.TEXTOS_TIE or not motor.ENLACES or not motor.NOVEDADES:
        fallos.append("alguna tabla de consulta está vacía")
    for clave in ("titulo", "fuente", "aviso", "leyenda"):
        if not motor.NOTAS.get(clave):
            fallos.append(f"falta «{clave}» en notas.json")
    return informe("Los datos extraídos del Excel están enteros", fallos, 8)


def p_las_fechas_como_excel():
    """EDATE y DATEDIF: fin de mes, bisiestos, y los 216 meses de M2."""
    fallos = []
    esperado = [
        (motor.edate(date(2026, 1, 31), 1), date(2026, 2, 28)),
        (motor.edate(date(2024, 1, 31), 1), date(2024, 2, 29)),
        (motor.edate(date(2026, 3, 31), -1), date(2026, 2, 28)),
        (motor.edate(date(2026, 11, 15), 2), date(2027, 1, 15)),
        (motor.edate(date(2010, 8, 31), 216), date(2028, 8, 31)),
        (motor.anos_entre(date(2009, 6, 1), date(2026, 9, 26)), 17),
        (motor.anos_entre(date(2009, 9, 27), date(2026, 9, 26)), 16),
        (motor.anos_entre(date(2009, 9, 26), date(2026, 9, 26)), 17),
        (motor.meses_entre(date(2026, 9, 1), date(2026, 9, 26)), 0),
        (motor.meses_entre(date(2026, 8, 26), date(2026, 9, 26)), 1),
        (motor.meses_entre(date(2026, 8, 27), date(2026, 9, 26)), 0),
        (motor.meses_entre(date(2026, 3, 1), date(2026, 9, 26)), 6),
    ]
    for i, (real, bueno) in enumerate(esperado, 1):
        if real != bueno:
            fallos.append(f"comprobación {i}: {real!r}, esperado {bueno!r}")
    return informe("Las fechas se suman como en Excel", fallos, len(esperado))


def p_plazos_de_la_demanda():
    """El ejemplo de la hoja FECHAS y un caso sin solicitud de renovación."""
    fallos = []
    p = motor.plazos_demanda(date(2026, 9, 14), date(2026, 10, 14), date(2026, 8, 20))
    if p.proxima != date(2026, 11, 28):
        fallos.append(f"ejemplo del Excel: próxima {p.proxima}, esperada 28/11/2026")
    if not p.tipo.startswith("ESPECIAL"):
        fallos.append(f"ejemplo del Excel: tipo {p.tipo!r}, esperado ESPECIAL")
    if p.en_plazo is not True or p.mas_de_tres_meses is not False:
        fallos.append(f"ejemplo del Excel: en plazo {p.en_plazo}, +3 meses {p.mas_de_tres_meses}")
    p = motor.plazos_demanda(date(2026, 2, 1), date(2026, 6, 30))
    if p.proxima != date(2026, 5, 3) or p.tipo != "Normal":
        fallos.append(f"sin solicitud: {p.proxima} {p.tipo!r}, esperado 03/05/2026 Normal")
    if p.en_plazo is not None:
        fallos.append("sin solicitud no se puede decir si está en plazo")
    p = motor.plazos_demanda(date(2026, 9, 26), date(2026, 5, 1), date(2026, 1, 15))
    if p.en_plazo is not False or p.mas_de_tres_meses is not True:
        fallos.append(f"fuera de plazo y más de 3 meses: {p.en_plazo} {p.mas_de_tres_meses}")
    return informe("La calculadora de plazos de la demanda", fallos, 6)


def p_sin_avisos_de_mas():
    """Un caso limpio no lleva avisos, solo la nota de la regla."""
    fallos = []
    r = motor.codifica("TIE (tarjeta de identidad de extranjero)",
                       "Residencia y trabajo por cuenta ajena – SIN limitación de comunidad ni ocupación",
                       emision=date(2025, 6, 15), valido_hasta=date(2029, 6, 15), hoy=date(2026, 9, 26))
    if r.avisos:
        fallos.append(f"T2 de 4 años lleva avisos: {r.avisos}")
    if r.restriccion != "N" or r.colectivo != "—":
        fallos.append(f"restricción {r.restriccion!r}, colectivo {r.colectivo!r}")
    r = motor.codifica("", "", hoy=date(2026, 9, 26))
    if r.valido or r.mensaje != "Empieza por el documento":
        fallos.append(f"sin documento: {r.mensaje!r}")
    r = motor.codifica("TIE (tarjeta de identidad de extranjero)", "esto no existe", hoy=date(2026, 9, 26))
    if r.valido or r.mensaje != "Elige qué pone el documento":
        fallos.append(f"opción inexistente: {r.mensaje!r}")
    return informe("Sin avisos de más, y lo incompleto se dice", fallos, 4)


# ---------------------------------------------------------------------------
# La pantalla
# ---------------------------------------------------------------------------

ENVOLTORIO = """
import os, sys
RAIZ = {raiz!r}
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
DeltaGenerator.page_link = lambda self, *a, **k: None
st.page_link = lambda *a, **k: None
ruta = os.path.join(RAIZ, "herramientas/extranjeria/vista.py")
exec(compile(open(ruta, encoding="utf-8").read(), ruta, "exec"),
     {{"__name__": "__main__", "__file__": ruta}})
"""


def abre_pantalla():
    import tempfile
    from streamlit.testing.v1 import AppTest
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(ENVOLTORIO.format(raiz=RAIZ))
    tmp.close()
    at = AppTest.from_file(tmp.name, default_timeout=120)
    at.run()
    return at


def _selector(at, clave):
    cajas = [s for s in at.selectbox if s.key == clave]
    return cajas[0] if cajas else None


def p_pantalla():
    """Elegir el documento cambia «qué pone», y elegir una opción pinta un código."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print("[ -- ] La pantalla: sin Streamlit no se prueba (usa ~/.venvs/sispe)")
        return True
    at = abre_pantalla()
    fallos = []
    if at.exception:
        fallos.append(f"excepción al abrir: {str(at.exception[0].value)[:100]}")
        return informe("En la pantalla: documento, opción y código", fallos, 4)
    doc = _selector(at, "ext_w_documento")
    if doc is None:
        fallos.append("no está el desplegable del documento")
        return informe("En la pantalla: documento, opción y código", fallos, 4)
    doc.select("TIE (tarjeta de identidad de extranjero)").run()
    opcion = _selector(at, "ext_w_opcion")
    if opcion is None or len(opcion.options) != len(motor.opciones("TIE (tarjeta de identidad de extranjero)")):
        fallos.append("la lista de «qué pone» no es la de la TIE")
    else:
        opcion.select("«ARTÍCULO 50 TUE» (anverso) · «EMITIDO BAJO ART. 18.4 ACUERDO RETIRADA» (reverso)").run()
        textos = " ".join(m.value for m in at.markdown)
        if "P0" not in textos:
            fallos.append("elegida la opción del Brexit, no aparece P0")
    _selector(at, "ext_w_documento").select("Visado pegado en el pasaporte").run()
    opcion = _selector(at, "ext_w_opcion")
    if opcion is None or len(opcion.options) != len(motor.opciones("Visado pegado en el pasaporte")):
        fallos.append("al cambiar a visado no cambia la lista de «qué pone»")
    if at.exception:
        fallos.append(f"excepción en la pantalla: {str(at.exception[0].value)[:100]}")
    return informe("En la pantalla: documento, opción y código", fallos, 4)


PRUEBAS = [
    p_los_casos,
    p_todas_las_opciones_responden,
    p_los_datos_estan_enteros,
    p_las_fechas_como_excel,
    p_plazos_de_la_demanda,
    p_sin_avisos_de_mas,
    p_pantalla,
]


def main():
    print(f"Codificador de extranjería: {len(motor.DOCUMENTOS)} documentos · {len(motor.REGLAS)} opciones · "
          f"{len(motor.CODIGOS)} códigos · {motor.NOTAS['titulo'].split('·')[-1].strip()}\n")
    for prueba in PRUEBAS:
        try:
            prueba()
        except Exception as e:  # noqa: BLE001
            nombre = prueba.__name__.removeprefix("p_").replace("_", " ")
            RESUMEN.append((nombre, False))
            print(f"[MAL] {nombre:52} {type(e).__name__}: {e}")
    bien = sum(1 for _, ok in RESUMEN if ok)
    print(f"\n{bien} de {len(RESUMEN)} pruebas pasan")
    return 0 if bien == len(RESUMEN) else 1


if __name__ == "__main__":
    sys.exit(main())
