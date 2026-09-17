# CLAUDE.md

Guía para Claude Code (claude.ai/code) en la rama **`pruebas-cv`**.

**Esta rama no es `main`.** Aquí el proyecto es una caja de herramientas
repartida en módulos; en `main` sigue siendo un `app.py` único de ~4.800 líneas.
Las dos ramas se separaron el 21/08/2026 y han seguido cada una por su lado, así
que **nada de lo que se lea sobre la estructura de `main` vale aquí**.

El repositorio está escrito íntegramente en español: código, comentarios,
documentación y mensajes de commit. Sigue esa convención.

## Comandos

```bash
cd pruebas
python3 evaluar.py          # aciertos del buscador: los 40 casos de casos.csv
python3 estres.py           # robustez del buscador: 8 comprobaciones
~/.venvs/sispe/bin/python informes.py   # la herramienta de informes: 16 comprobaciones

python3 evaluar.py --detalle    # los tres primeros de cada caso
python3 evaluar.py --informe    # vuelca a informe_evaluacion.csv (no versionado)
python3 estres.py --rapido      # salta las pruebas que recorren el catálogo

~/.venvs/sispe/bin/streamlit run app.py   # la app en local (sin claves: solo lo que no usa IA)
```

`informes.py` necesita `reportlab`, que **no está en el `python3` del sistema**
(no trae ni `pip` ni `ensurepip`). Está en el entorno `~/.venvs/sispe`
(Python 3.13, creado con `uv`), que es también el que hay que usar para levantar
la app entera, porque el generador de CV necesita `python-docx`. Las otras dos
baterías son Python puro y corren con el `python3` de siempre.

Las tres baterías **son** la suite: no hay pytest, ni linter, ni formateador. No
llaman a la IA y no gastan cuota.

**Aquí las pruebas no corren en GitHub Actions.** Esta rama solo tiene
`.github/workflows/mantener-despierta.yml`; el `pruebas.yml` que vigila cada push
está únicamente en `main`. Hasta que se añada, las baterías solo las pasa quien
se acuerde de pasarlas.

## Arquitectura

Una herramienta por carpeta, y una sola forma de añadir otra:

```
inicio.py                    portada: una tarjeta por herramienta
app.py                       monta la navegación a partir de comun/registro.py
comun/registro.py            LA LISTA: lo único que se toca para añadir una herramienta
comun/{estilo,ia,gist,texto,version}.py    lo que comparten varias
herramientas/<nombre>/vista.py    la pantalla; lo ÚNICO que usa Streamlit
herramientas/<nombre>/motor.py    la lógica, Python puro
herramientas/<nombre>/modelo.py   los datos de la herramienta
herramientas/<nombre>/datos/      catálogos, vocabularios, plantillas
pruebas/                     las tres baterías
scripts/                     despertar.py y enriquecer.py
```

**`motor.py` no puede importar Streamlit.** `pruebas/motor_pruebas.py` lo
comprueba al cargar y aborta con un mensaje si lo ha hecho. Eso sustituyó a la
marca `# === FIN DEL MOTOR ===` de `main`, donde el motor y la interfaz viven en
el mismo archivo y hay que cortarlo con un Streamlit de mentira. **Aquí esa marca
no existe y no hace falta.**

El menú de herramientas no va en la barra lateral de Streamlit, sino dentro de la
banda negra de cada página (`comun/estilo.py`), para que se vea igual en el móvil
y no dependa de ningún control interno de Streamlit.

Las cuatro herramientas: **Codificador SISPE** (el buscador de códigos, que es lo
que hay en producción en `main`), **Generador de CV**, **Asesor de formación** e
**Informes de orientación**. Se pasan datos entre sí: el codificador manda las
experiencias al generador de CV, y el de CV manda el perfil al asesor de
formación.

## El motor SISPE de esta rama va por detrás de `main`

Medido el 17/09/2026: `herramientas/sispe/datos/vocabulario.json` tiene **110
sinónimos frente a los 127 de `main`**, y se nota en las pruebas —
`evaluar.py` da **35/40 (87 %)** aquí y **39/40 (97 %)** en `main`; «cada
ocupación se encuentra a sí misma» da 2208/2218 frente a 2218/2218. A esta rama
también le faltan dos pruebas de estrés que `main` ya tiene (la de la petición de
respaldo y «el modelo no puede tumbar la app»).

`main` lleva 123 commits desde la separación, casi todos del motor y de la
cascada de proveedores. **Antes de tocar el buscador de esta rama, mirar cómo
está resuelto en `main`**: lo previsto es traer aquí el motor y los datos de
`main` en un solo sentido, no fusionar ramas.

## Reglas que ya costaron una sesión

- **`pruebas/casos.csv` solo se edita a mano**, con el código comprobado contra
  el catálogo oficial, nunca copiado de lo que contesta el motor. Existió un
  `--actualizar` que lo reescribía con la salida del propio motor y consagraba
  las regresiones; hoy el script aborta si se usa.
- El catálogo (`herramientas/sispe/datos/ocupaciones_sispe_ultraligero.txt`,
  2.218 ocupaciones) es la fuente oficial y no se toca.
- **En local no hay claves.** Las claves de IA y las del Gist (`GIST_ID`,
  `GITHUB_TOKEN`) salen de los Secrets de Streamlit o del entorno; sin
  `secrets.toml` la app levanta pero solo sirve lo que no llama a la IA. Basta un
  `.streamlit/secrets.toml` vacío (ya está en `.gitignore`).
- Las **fuentes del protocolo** (Caladea y Carlito) las instala `packages.txt` en
  el despliegue. En local no están y los informes salen con DejaVu, que la
  batería avisa por pantalla: el PDF no es idéntico al de producción.
- `packages.txt` **no admite comentarios**: una línea con `#` tumbaba el
  despliegue.

## Commits

Mensaje en español, una frase que dice qué cambia y por qué, sin prefijo de tipo
ni scope. Ejemplos reales de esta rama: «El correo de cierre, calibrado contra
los de verdad», «packages.txt sin comentarios: tumbaban el despliegue».
