"""
Registro de herramientas: la única lista que hay que tocar para añadir una.

`INICIO` es la portada; `HERRAMIENTAS`, las herramientas en el orden del menú
y de la portada.

La lee `app.py` para montar la navegación, `comun/estilo.py` para pintar el
menú de la barra negra y `inicio.py` para las tarjetas de la portada.

Cada herramienta lleva:

    titulo   el nombre, el mismo en la portada, en el menú y en su página
    corto    lo que cabe en el menú del móvil; si falta, se usa el título
    ia       si llama a la IA (sin claves solo funcionan las que no)
    icono    un icono de Material, para el menú y la portada
"""

INICIO = {
    "id": "inicio",
    "ruta": "inicio.py",
    "titulo": "Inicio",
    "icono": ":material/home:",
    "url": None,          # la página por defecto se sirve en la raíz (/)
}

HERRAMIENTAS = [
    {
        "id": "sispe",
        "ruta": "herramientas/sispe/vista.py",
        "titulo": "Codificador SISPE",
        "corto": "Codificador SISPE",
        "icono": ":material/manage_search:",
        "url": "sispe",
        "ia": True,
        "descripcion": "El código de ocupación del catálogo SISPE a partir de una "
                       "descripción en lenguaje corriente, antes de grabarlo en "
                       "SilcoiWeb. Manda las experiencias al generador de CV.",
    },
    {
        "id": "extranjeria",
        "ruta": "herramientas/extranjeria/vista.py",
        "titulo": "Codificador de extranjería",
        "corto": "Extranjería",
        "icono": ":material/badge:",
        "url": "extranjeria",
        "ia": False,
        "descripcion": "Qué código de autorización y qué fecha fin de vigencia se graban "
                       "al inscribir a una persona extranjera, a partir de lo que pone "
                       "su documento. Es el Excel de la oficina hecho pantalla.",
    },
    {
        "id": "cv",
        "ruta": "herramientas/cv/vista.py",
        "titulo": "Generador de CV",
        "corto": "Generador de CV",
        "icono": ":material/description:",
        "url": "cv",
        "ia": True,
        "descripcion": "Un currículo en cuatro pasos sobre el modelo de la oficina, "
                       "siempre en una página. La IA ordena la trayectoria contada de "
                       "palabra o por escrito, sugiere funciones y redacta el objetivo.",
    },
    {
        "id": "formacion",
        "ruta": "herramientas/formacion/vista.py",
        "titulo": "Asesor de formación",
        "corto": "Formación",
        "icono": ":material/school:",
        "url": "formacion",
        "ia": True,
        "descripcion": "Sube el Excel de cursos y el perfil de la persona, o tómalo del "
                       "generador de CV, y la IA propone los cursos que más le convienen "
                       "y explica por qué.",
    },
    {
        "id": "informes",
        "ruta": "herramientas/informes/vista.py",
        "titulo": "Informes de orientación",
        "corto": "Informes",
        "icono": ":material/assignment:",
        "url": "informes",
        "ia": True,
        "descripcion": "Las tres fases de una orientación individual: lee el currículo y "
                       "prepara la cita en un PDF de dos páginas, recoge lo que solo se "
                       "ve en la sala y redacta el correo de cierre.",
    },
]

PAGINAS = [INICIO] + HERRAMIENTAS


def por_id(id_):
    """La entrada del registro con ese id, o None."""
    return next((h for h in PAGINAS if h["id"] == id_), None)
