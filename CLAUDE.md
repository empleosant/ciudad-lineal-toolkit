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
python3 estres.py           # robustez del buscador: 10 comprobaciones
~/.venvs/sispe/bin/python informes.py   # la herramienta de informes: 16 comprobaciones
~/.venvs/sispe/bin/python cascada.py    # la cascada de proveedores: 21 comprobaciones
~/.venvs/sispe/bin/python cv.py         # el generador de CV: 10 comprobaciones

python3 evaluar.py --detalle    # los tres primeros de cada caso
python3 evaluar.py --informe    # vuelca a informe_evaluacion.csv (no versionado)
python3 estres.py --rapido      # salta las pruebas que recorren el catálogo

~/.venvs/sispe/bin/streamlit run app.py   # la app en local (sin claves: solo lo que no usa IA)

cd ..
~/.venvs/sispe/bin/python scripts/comprobar_ia.py            # ¿existen los modelos de PROVEEDORES?
~/.venvs/sispe/bin/python scripts/comprobar_ia.py --llamar   # y además, ¿responden?
```

`scripts/comprobar_ia.py` **no es una batería**: habla con las APIs de verdad y
necesita claves (del entorno o de `.streamlit/secrets.toml`). Es lo único que
puede decir si los nombres de modelo de `comun/ia.py` siguen existiendo, porque
los proveedores cierran modelos antes de la fecha que anuncian. Sin ninguna
clave que responda avisa de que no ha comprobado nada y sale con 2, en vez de
dar por bueno lo que no ha mirado.

**No todas las herramientas usan los mismos modelos.** `comun/ia.py` tiene dos
cadenas: `modelos` (perfil `RAPIDO`, de fábrica) empieza por los Flash-Lite,
que es lo que necesita el codificador —cientos de consultas al día y respuesta
en un segundo—, y `modelos_calidad` (perfil `CALIDAD`) empieza por los modelos
completos, con mucho menos cupo diario pero mejor redacción. Lo piden
**informes y asesor de formación**, que redactan tres o cuatro veces al día:
ahí no se nota el segundo de espera y sí se nota lo vago que escribe un Lite.
Cuando el bueno se queda sin cupo, la misma cadena sigue por los rápidos y el
informe sale igual. Los castigos de una cadena no tocan a la otra.

**En local no hay claves, así que lo normal es comprobarlo en el despliegue**:
`?mantenimiento=1` → «Probar TODOS los modelos», que hace lo mismo a base de
llamar (16 tokens por modelo) y señala los que ya no existen. Es el botón que
hay que pulsar después de tocar la lista de `PROVEEDORES`.

`informes.py`, `cascada.py` y `cv.py` **necesitan las dependencias instaladas**, y no
solo `reportlab`: las dos acaban importando `comun/ia.py`, que importa Streamlit
en la primera línea (`informes.py` por los prompts de
`herramientas/informes/modelo.py`; `cascada.py` porque es justo `ia.py` lo que
prueba; `cv.py` porque el motor del CV importa reportlab para el PDF). Con el
`python3` del sistema no corren (no trae ni `pip` ni
`ensurepip`); se lanzan con el entorno `~/.venvs/sispe` (Python 3.13, creado con
`uv`), que es también el que hay que usar para levantar la app entera. Las otras
dos baterías sí son Python puro y corren con el `python3` de siempre.

Las cinco baterías **son** la suite: no hay pytest, ni linter, ni formateador.
No llaman a la IA y no gastan cuota: `cascada.py` le pone proveedores de mentira
que contestan, tardan o fallan a la orden.

`cv.py` es la única que además **pulsa botones**: sus dos últimas
comprobaciones levantan la pantalla del generador con el banco de pruebas de
Streamlit (`streamlit.testing.v1.AppTest`, sin navegador) y comprueban que al
marcar «Carnet B» cambia de verdad la caja de texto de al lado. La pantalla se
ejecuta con un envoltorio que desactiva `page_link`, que solo existe con la
navegación de `app.py` montada.

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
comun/plazos.py              cuánto se espera a una llamada colgada (Python puro)
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

## El motor SISPE, ya al día con `main`

El 18/09/2026 se trajo el buscador de `main` en un solo sentido: los 127
sinónimos del vocabulario, los términos ampliados (2.239 ocupaciones), los tres
factores que le faltaban a `busca` (bonus por denominación exacta, el de las
ocupaciones «, EN GENERAL» y la densidad) y el colapso de espacios de
`normaliza`. `evaluar.py` da **39/40 (97 %)** y «cada ocupación se encuentra a
sí misma», 2218/2218: los mismos números que `main`. El catálogo era ya
idéntico byte a byte.

Ese mismo día se trajo también la **cascada de proveedores**. `comun/ia.py` ya
no habla con uno solo: recorre `ORDEN` (Gemini → Mistral → Groq → OpenRouter)
saltando los que no tengan clave, aparta una hora al que dice que se le ha
agotado el cupo del DÍA, degrada cinco minutos el modelo que tropieza y vuelve a
probar el bueno cuando el castigo caduca. Un tope por minuto no aparta a nadie:
se pasa solo.

El respaldo y los plazos viven aparte, en **`comun/plazos.py`**, que es Python
puro: `con_plazo` se rinde a los `PLAZO_INTENTO` segundos y a los
`PLAZO_RESPALDO` lanza una segunda petición igual sin tirar la primera, porque
lo que pasa no es que el modelo tarde, sino que una de cada cinco peticiones se
queda colgada. **Solo el codificador pide plazo**: las herramientas que redactan
(informes, formación) tardan mucho más y esperan sin corte.

Con eso esta rama pasa las mismas diez pruebas de estrés que `main`, la del
respaldo incluida. Lo que `main` no tiene es `pruebas/cascada.py`: allí la
cascada vive dentro de `app.py` y no hay forma de probarla sin levantar la app.

**Antes de tocar el buscador, seguir mirando cómo está resuelto en `main`**: el
traspaso es en un solo sentido, no se fusionan ramas.

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
