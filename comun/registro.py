"""
Registro de herramientas: la única lista que hay que tocar para añadir una.

La lee `app.py` para montar la navegación y `comun/estilo.py` para pintar
el menú dentro de la banda negra de cada página.
"""

HERRAMIENTAS = [
    {
        "id": "sispe",
        "ruta": "herramientas/sispe/vista.py",
        "titulo": "Codificador SISPE",
        "icono": ":material/manage_search:",
        "url": None,          # la página por defecto se sirve en la raíz (/)
    },
    {
        "id": "cv",
        "ruta": "herramientas/cv/vista.py",
        "titulo": "Generador de CV",
        "icono": ":material/description:",
        "url": "cv",
    },
]
