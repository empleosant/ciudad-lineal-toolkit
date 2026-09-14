"""
Registro de herramientas: la única lista que hay que tocar para añadir una.

`INICIO` es la portada; `HERRAMIENTAS`, las herramientas en el orden del menú.

La lee `app.py` para montar la navegación y `comun/estilo.py` para pintar
el menú dentro de la banda negra de cada página.
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
        "icono": ":material/manage_search:",
        "url": "sispe",
        "descripcion": "Localiza el código de ocupación del catálogo SISPE a partir "
                       "de una descripción en lenguaje corriente, antes de grabarlo "
                       "en SilcoiWeb. Manda las experiencias al generador de CV.",
    },
    {
        "id": "cv",
        "ruta": "herramientas/cv/vista.py",
        "titulo": "Generador de CV",
        "icono": ":material/description:",
        "url": "cv",
        "descripcion": "Un currículo en cuatro pasos. La IA ordena la trayectoria "
                       "contada de palabra o por escrito, sugiere funciones y redacta "
                       "el perfil. Sale en Word, listo para retocar.",
    },
]

PAGINAS = [INICIO] + HERRAMIENTAS
