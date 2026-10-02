"""
Copia a la app las fichas de la Guía de empleo de Madrid.

USO
    python3 scripts/traer_guia.py [RUTA_AL_REPO_DE_LA_GUIA]

Por defecto lee `~/proyectos/guia-empleo-madrid` (el repositorio privado
`empleosant/guia-empleo-madrid`). La guía es la fuente: aquí entran solo
copias, en `comun/datos/guia/`, y no se editan a mano. Cuando la guía cambie
(la próxima revisión es en abril de 2027) se vuelve a pasar este script, se
mira el diff y se pasa `pruebas/guia.py`.

Qué se copia:

    capitulos.csv   los capítulos en el orden de la guía: parte, zona, título y apartados
    fichas.csv      las fichas publicables, con las columnas que se imprimen
    edicion.json    título, edición, mes de comprobación y firma

Entran las mismas fichas que salen en el PDF de la guía, con la misma regla
que `lee_fichas()` de su `scripts/generar.py`: estado publicable, marcada
«publicable = sí» en `datos/comprobacion/` y sin los enlaces caídos. Las
columnas de trabajo (fuente, estado, notas internas) se quedan en la guía.

No lo usa la app. Python puro: corre con el python3 del sistema.
"""

import csv
import json
import os
import sys
import tomllib
from collections import Counter

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESTINO = os.path.join(RAIZ, "comun", "datos", "guia")
GUIA = os.path.expanduser("~/proyectos/guia-empleo-madrid")

# Las mismas que `PUBLICABLES` en scripts/generar.py de la guía.
PUBLICABLES = {"vigente", "vigente con cambios", "renombrada", "nueva"}

# Lo que se imprime de cada ficha. `id` y `capitulo` son para la app.
COLUMNAS = ["capitulo", "id", "apartado", "formato", "nombre", "tipo", "que",
            "direccion", "cp", "municipio", "transporte", "telefono", "correo",
            "web", "web_empleo", "como"]


def lee_fichas(guia, capitulo):
    """Las fichas publicables del capítulo, como las lee la guía para su PDF."""
    ruta = os.path.join(guia, "datos", "fichas", f"{capitulo}.csv")
    comprobacion = os.path.join(guia, "datos", "comprobacion", f"{capitulo}.csv")
    if not os.path.exists(ruta) or not os.path.exists(comprobacion):
        return []
    with open(comprobacion, newline="", encoding="utf-8") as f:
        buenas = {c["id"]: c for c in csv.DictReader(f) if c["publicable"] == "sí"}
    fichas = []
    with open(ruta, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if (fila.get("estado") or "").strip().lower() not in PUBLICABLES:
                continue
            if fila["id"] not in buenas:
                continue
            for campo in buenas[fila["id"]]["enlaces_caidos"].split():
                fila[campo] = ""            # un enlace caído no se imprime
            fila = {c: (fila.get(c) or "").strip() for c in COLUMNAS}
            fila["capitulo"] = capitulo
            fila["formato"] = fila["formato"] or "ficha"
            fichas.append(fila)
    return fichas


def main():
    guia = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else GUIA
    with open(os.path.join(guia, "datos", "capitulos.toml"), "rb") as f:
        estructura = tomllib.load(f)
    zonas = {z["id"]: z["titulo"] for z in estructura.get("zona", [])}
    parte_iv = next((p for p in estructura["parte"] if p["id"] == "IV"), {})

    os.makedirs(DESTINO, exist_ok=True)
    capitulos, fichas = [], []
    for c in estructura["capitulo"]:
        suyas = lee_fichas(guia, c["id"])
        if not suyas:
            print(f"  {c['id']}: sin fichas publicables, no se copia")
            continue
        capitulos.append([
            c["id"], c.get("parte", ""), c.get("zona", ""), zonas.get(c.get("zona"), ""),
            c["titulo"], " | ".join(c.get("apartados", [])),
        ])
        fichas += suyas

    with open(os.path.join(DESTINO, "capitulos.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "parte", "zona", "zona_titulo", "titulo", "apartados"])
        w.writerows(capitulos)
    with open(os.path.join(DESTINO, "fichas.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLUMNAS, lineterminator="\n")
        w.writeheader()
        w.writerows(fichas)
    edicion = {
        "titulo": estructura["titulo"],
        "titulo_empresas": parte_iv.get("titulo_sola", ""),
        "edicion": estructura["edicion"],
        "verificado": estructura["verificado"],
        "autor": estructura["autor"],
        "autor_enlace": estructura["autor_enlace"],
        "fichas": len(fichas),
    }
    with open(os.path.join(DESTINO, "edicion.json"), "w", encoding="utf-8") as f:
        json.dump(edicion, f, ensure_ascii=False, indent=2)
        f.write("\n")

    por_parte = Counter(c[1] for c in capitulos)
    print(f"  {len(capitulos)} capítulos ({', '.join(f'{p}: {n}' for p, n in sorted(por_parte.items()))})")
    print(f"  {len(fichas)} fichas · {edicion['edicion']} · comprobada en {edicion['verificado']}")


if __name__ == "__main__":
    main()
