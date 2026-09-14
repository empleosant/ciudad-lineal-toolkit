"""
Llamada a la IA del asesor de formación.

    sugiere(cli, perfil, cursos, cuantos)  -> (recomendaciones, observaciones, descartadas)

La IA solo puede elegir cursos por su número de la lista; la app cruza los
números con las filas reales del Excel y descarta lo que no exista.
"""

import json
import re

from comun import ia
from herramientas.formacion import motor

ASESOR = """Eres un orientador laboral de una Oficina de Empleo. Recibes el PERFIL de una
persona (sin datos identificativos) y una LISTA NUMERADA de cursos de formación
disponibles. Tienes que proponer los cursos que más le convienen.

Responde SOLO con este JSON:
{"recomendaciones":[{"n":12,"prioridad":"alta","por_que":"...","aviso":"..."}],
 "observaciones":"..."}

REGLAS:
- "n" es el número entre corchetes del curso en la lista. Usa ÚNICAMENTE números
  que estén en la lista. No inventes cursos ni cambies sus nombres.
- Propón exactamente CUANTOS cursos (te lo indican), de mayor a menor conveniencia,
  salvo que no haya tantos que encajen: entonces menos, nunca de relleno.
- "prioridad": "alta", "media" o "baja".
- "por_que": en 15-30 palabras, qué aporta ese curso a ESTA persona según su perfil:
  continuidad con su experiencia, salida laboral, requisito que le falta, etc.
- "aviso": si el curso tiene un requisito (titulación, nivel, carné, horario) que
  según el perfil podría no cumplir, dilo en pocas palabras. Si no, "".
- "observaciones": 2-3 frases para el orientador: qué línea formativa recomiendas
  en conjunto y qué convendría aclarar con la persona. Sin viñetas.
- Español con acentuación correcta. No uses el nombre de nadie.
"""


def _json(bruto):
    texto = re.sub(r"^```(?:json)?|```$", "", (bruto or "").strip(), flags=re.MULTILINE)
    try:
        return json.loads(texto)
    except Exception:  # noqa: BLE001
        bloque = re.search(r"\{.*\}", texto, re.S)
        try:
            return json.loads(bloque.group()) if bloque else {}
        except Exception:  # noqa: BLE001
            return {}


def sugiere(cli, perfil, cursos, cuantos=5):
    if cli is None:
        raise RuntimeError("No hay conexión con la IA.")
    entrada = (
        f"CUANTOS: {cuantos}\n\nPERFIL:\n{perfil.strip()}\n\n"
        f"LISTA DE CURSOS:\n{motor.lista_para_ia(cursos)}"
    )
    datos = _json(ia.genera(cli, ASESOR, entrada, max_tokens=4096, json=True, pensar=True))
    recomendaciones, descartadas = motor.resuelve(datos.get("recomendaciones"), cursos)
    return recomendaciones, str(datos.get("observaciones", "") or "").strip(), descartadas
