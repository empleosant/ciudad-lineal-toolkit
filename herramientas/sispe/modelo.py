"""
Llamadas a la IA del codificador SISPE: los prompts y las dos consultas.

    interpreta_consulta(cli, texto, memoria)   vocabulario oficial de la descripción
    flujo_modelo(cli, texto, candidatos)        elige entre candidatos, a trozos

No usa Streamlit: el cliente y la memoria de sesión se reciben como
parámetros. El cliente lo da `comun.ia.cliente()`.
"""

from comun import ia
from comun.texto import normaliza
from herramientas.sispe import motor

INSTRUCCIONES = """Eres un técnico de codificación de ocupaciones para SilcoiWeb (SEPE).

Recibes la descripción de un puesto y una lista cerrada de ocupaciones candidatas.
Selecciona entre 3 y 5, de mayor a menor afinidad.

REGLAS
1. Usa únicamente códigos y denominaciones literales de la lista de candidatos. No inventes ni modifiques ninguno.
2. Los candidatos llegan ordenados por coincidencia de palabras, NO por acierto. Ese orden es solo una pista: elige siempre la ocupación cuya denominación describa la actividad real, aunque esté al final de la lista.
3. Devuelve SIEMPRE entre 3 y 5 ocupaciones, aunque dudes.
4. Nivel profesional: 90 aprendices (sin experiencia) / 00 técnicos o sin categoría (estándar con experiencia) / 10 dirección / 20 mandos intermedios / 30 jefes de equipo / 70 auxiliares / 80 peones.
5. El campo "motivo" explica en menos de 10 palabras por qué encaja, en español con acentuación correcta.
6. No propongas ocupaciones de dirección, jefatura ni mando (niveles 10, 20, 30) salvo que la descripción diga expresamente que dirigía equipos, centros o departamentos.
7. Respeta el entorno de trabajo que indique la descripción: domicilio particular frente a institución, centro o residencia.
8. PREGUNTA Y OPCIONES (DESAMBIGUACIÓN):
   - Rellena "pregunta" y "opciones" solo si hay duda para desempatar entre las DOS PRIMERAS ocupaciones. Si no hay duda, deja "pregunta": "" y "opciones": [].
   - La pregunta debe plantear una elección clara y directa (máximo 15 palabras).
   - El campo "opciones" DEBE contener una lista con las 2 alternativas concretas (ej. ["Atención en caja / mostrador", "Cocina y preparación de comida"], ["Casas particulares", "Residencias / Centros"], o ["Sí", "No"]). NUNCA dejes "opciones" vacío si hay "pregunta".
9. Si ninguna de las candidatas describe con precisión la actividad, rellena "otros_terminos" con entre 6 y 10 palabras sueltas de la CNO.

EJEMPLO DE RESPUESTA:
{"ocupaciones":[{"codigo":"51201027","denominacion":"CAMAREROS DE BARRA Y/O DEPENDIENTES DE CAFETERÍA","nivel":"00","motivo":"Atención en mostrador y servicio de comida rápida."},{"codigo":"93101024","denominacion":"PINCHES DE COCINA","nivel":"00","motivo":"Elaboración y preparación de alimentos en restauración."}],"pregunta":"¿A qué tarea dedicaba la mayor parte de su jornada?","opciones":["Atención en caja y mostrador","Preparación de comida en cocina"],"otros_terminos":""}
"""


INTERPRETE = """Eres experto en el catálogo de ocupaciones del SEPE (CNO).

Lees la descripción de un puesto escrita por un orientador laboral, con las
palabras de la persona atendida, y devuelves el VOCABULARIO OFICIAL de los
oficios que podría estar describiendo.

Una descripción corriente admite varias lecturas: "cuidado de niños en una
escuela" puede ser guardería, comedor escolar o tiempo libre. Devuelve entre
2 y 3 lecturas distintas, de más a menos probable.

Si la descripción incluye dos funciones distintas o tareas combinadas
(ej. "cobro en caja y repongo", "conduzco y reparto"), genera una lectura
específica para cada una de las actividades.

Responde SOLO con este JSON:
{"lecturas":[{"terminos":"...","grupos":"5"},{"terminos":"...","grupos":"3"}]}
"""


def interpreta_consulta(cli, texto, memoria=None):
    """Lecturas [(términos, grupos), ...] de más a menos probable.

    `memoria` es un diccionario donde se guardan las respuestas por consulta
    para no volver a preguntar lo mismo en la misma sesión.
    """
    clave = normaliza(texto)
    if memoria is not None and clave in memoria:
        return memoria[clave]
    try:
        bruto = ia.genera(cli, INTERPRETE, texto)
    except Exception:  # noqa: BLE001
        return []

    # Dar forma a lo que conteste el modelo es cosa del motor: allí es Python
    # puro y lo prueba `estres.py` con las formas raras que manda de verdad.
    lecturas = motor.lecturas_de(bruto)
    if memoria is not None:
        memoria[clave] = lecturas
    return lecturas


def flujo_modelo(cli, texto, candidatos):
    """La respuesta JSON del modelo, a trozos, para pintar el avance."""
    prompt = f"CANDIDATOS (única fuente válida):\n{candidatos}\n\nDESCRIPCIÓN: {texto}"
    yield from ia.genera_flujo(cli, INSTRUCCIONES, prompt, json=True)
