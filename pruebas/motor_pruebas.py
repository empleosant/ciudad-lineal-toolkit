"""
Cargador del motor para las pruebas.

Importa `herramientas/sispe/motor.py`, que es Python puro, y lo devuelve con
`busca`, `raiz`, `normaliza`, `IDX`, `VACIAS` y `SINONIMOS` listos para usar.
No llama a la IA ni gasta cuota.

Lo usan `evaluar.py` (aciertos) y `estres.py` (robustez).

Antes el motor vivía dentro de la app y había que cargarla hasta una marca
de corte con un Streamlit de mentira. Desde que el motor es un módulo aparte,
esto se reduce a un import: si alguien mete Streamlit en el motor, el import
falla aquí a la vista, en vez de romper las pruebas en silencio.
"""

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


def carga_motor():
    if "streamlit" in sys.modules:
        del sys.modules["streamlit"]
    from herramientas.sispe import motor

    if "streamlit" in sys.modules:
        sys.exit(
            "El motor ha importado Streamlit. Tiene que ser Python puro: lo que\n"
            "necesite Streamlit va en vista.py, no en motor.py."
        )
    return motor


def cabecera(motor):
    n = len(motor.IDX["registros"])
    ampliado = motor.IDX.get("ampliado", 0)
    return (
        f"Catálogo: {n} ocupaciones · {ampliado} con vocabulario ampliado\n"
        f"Vocabulario: {len(motor.VACIAS)} vacías, {len(motor.SINONIMOS)} sinónimos"
    )
