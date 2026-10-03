"""
El prompt de «Más empresas con IA» y la llamada con búsqueda en Google.

La respuesta la convierte en fichas `motor.interpreta`, que es quien decide
qué enlaces se enseñan: aquí solo se pregunta.
"""

from comun import ia

SISTEMA = """Eres documentalista de una oficina pública de empleo de Madrid. Tu trabajo es \
encontrar, buscando en la web, empresas a las que una persona puede enviar su currículum \
para un puesto concreto.

Reglas:
- Solo empresas u organizaciones reales que hayas visto en los resultados de la búsqueda, \
con sede, estudio, oficina o centro de trabajo en Madrid capital o en su área metropolitana \
(Comunidad de Madrid). Si una empresa es de fuera y no tiene centro en Madrid, no la pongas.
- Que contraten ese puesto o perfiles muy próximos. Mejor empresas concretas del oficio que \
grandes nombres genéricos.
- No pongas portales de empleo, empresas de trabajo temporal, academias ni cursos.
- No repitas las que te diga que ya tengo.
- No inventes: si dudas de que exista o de que esté en Madrid, déjala fuera. Mejor seis \
seguras que diez dudosas.

Responde SOLO con un objeto JSON, sin texto antes ni después y sin marcas de cita:
{"empresas": [{"nombre": "...", "que": "una frase: a qué se dedica y qué perfiles del puesto \
contrata", "donde": "municipio o zona de Madrid donde está", "como": "una frase: cómo se \
presenta la candidatura (portal de empleo propio, correo, formulario...)", "dominio": \
"dominio de su web tal como sale en la búsqueda, sin https ni rutas"}]}
Entre 6 y 10 empresas. Si no encuentras ninguna segura, {"empresas": []}."""


ENTRADA_SIN_EXPERIENCIA = (
    "Solo puestos de entrada: empresas que contratan para ese trabajo a personas SIN experiencia "
    "previa y SIN titulación, y que suelen formar al entrar. Descarta las que pidan título, "
    "habilitación o años de experiencia."
)


def entrada(puesto, sector="", ya=(), para_empezar=False):
    lineas = [f"Puesto: {puesto.strip()}", "Zona: Madrid capital y área metropolitana."]
    if para_empezar:
        lineas.append(ENTRADA_SIN_EXPERIENCIA)
    if sector:
        lineas.append(f"Sector de la guía de empleo que más se le parece: {sector}.")
    if ya:
        lineas.append("Ya tengo, no las repitas: " + "; ".join(list(ya)[:40]) + ".")
    return "\n".join(lineas)


def busca(puesto, sector="", ya=(), al_relevar=None, para_empezar=False):
    """(texto, fuentes, apoyos) de `ia.busca_en_la_web` para ese puesto."""
    return ia.busca_en_la_web(SISTEMA, entrada(puesto, sector, ya, para_empezar), al_relevar=al_relevar)
