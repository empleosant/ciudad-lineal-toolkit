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
~/.venvs/sispe/bin/python informes.py   # la herramienta de informes: 17 comprobaciones
~/.venvs/sispe/bin/python cascada.py    # la cascada de proveedores: 21 comprobaciones
~/.venvs/sispe/bin/python cv.py         # el generador de CV: 10 comprobaciones
~/.venvs/sispe/bin/python extranjeria.py   # el codificador de extranjería: 7 comprobaciones
~/.venvs/sispe/bin/python guia.py          # la guía en las cinco herramientas y las pantallas: 13 comprobaciones

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
tres (`evaluar.py`, `estres.py` y `extranjeria.py`) son Python puro y corren con el
`python3` de siempre; `extranjeria.py` solo se salta, sin ese entorno, la
comprobación de la pantalla, y `guia.py`, el PDF y las pantallas.

Las siete baterías **son** la suite: no hay pytest, ni linter, ni formateador.
No llaman a la IA y no gastan cuota: `cascada.py` le pone proveedores de mentira
que contestan, tardan o fallan a la orden.

`cv.py`, `extranjeria.py` y `guia.py` son las que además **pulsan botones**: sus últimas
comprobaciones levantan la pantalla (el generador de CV, el codificador de
extranjería) con el banco de pruebas de Streamlit (`streamlit.testing.v1.AppTest`, sin navegador) y comprueban que al
marcar «Carnet B» cambia de verdad la caja de texto de al lado. La pantalla se
ejecuta con un envoltorio que desactiva `page_link`, que solo existe con la
navegación de `app.py` montada.

**Las pruebas corren en GitHub Actions desde el 17/09/2026**:
`.github/workflows/pruebas.yml` pasa las siete baterías con cada push que toque
`comun/`, `herramientas/` o `pruebas/`. Cada batería nueva necesita su paso allí:
`cascada.py` y `cv.py` estuvieron nueve días sin él.

## Arquitectura

Una herramienta por carpeta, y una sola forma de añadir otra:

```
inicio.py                    portada: una tarjeta por herramienta
app.py                       monta la navegación a partir de comun/registro.py
comun/registro.py            LA LISTA: lo único que se toca para añadir una herramienta
comun/{estilo,ia,gist,texto,version}.py    lo que comparten varias
comun/plazos.py              cuánto se espera a una llamada colgada (Python puro)
comun/guia.py                la Guía de empleo de Madrid dentro de la app (Python puro)
comun/datos/                 la copia de la guía y la tabla ocupación → sector
herramientas/<nombre>/vista.py    la pantalla; lo ÚNICO que usa Streamlit
herramientas/<nombre>/motor.py    la lógica, Python puro
herramientas/<nombre>/modelo.py   los datos de la herramienta
herramientas/<nombre>/datos/      catálogos, vocabularios, plantillas
pruebas/                     las siete baterías
scripts/                     despertar.py, enriquecer.py, extraer_extranjeria.py y traer_guia.py
```

**`motor.py` no puede importar Streamlit.** `pruebas/motor_pruebas.py` lo
comprueba al cargar y aborta con un mensaje si lo ha hecho. Eso sustituyó a la
marca `# === FIN DEL MOTOR ===` de `main`, donde el motor y la interfaz viven en
el mismo archivo y hay que cortarlo con un Streamlit de mentira. **Aquí esa marca
no existe y no hace falta.**

## La interfaz (rediseñada el 26/09/2026)

Cada página empieza por `estilo.aplica()` y `estilo.banda(id, título, frase,
acciones=...)`: una barra negra fina de lado a lado con la marca y el menú
(chips; en el móvil una tira que se desliza, con la activa primera), y debajo
el título en el cuerpo. `banda` devuelve un contenedor bajo el título para lo
que cada herramienta ponga ahí (el codificador, su buscador). El menú no va
en la barra lateral de Streamlit y todos los saltos entre páginas son
`st.page_link`: un `<a href>` recargaría la app y perdería la sesión.

- **Lo que puede el tema, lo hace el tema** (`.streamlit/config.toml`:
  `primaryColor`, `borderColor`, `showWidgetBorder`, `baseRadius`). El CSS a
  mano de `estilo.py` queda para lo que el tema no cubre, y cada regla que
  depende de un `data-testid` de Streamlit lleva su comentario.
- `estilo.fila(clave)` es un `st.container(horizontal=True, wrap=False)`:
  no se apila en el móvil (las columnas sí, por debajo de 640 px). Ojo:
  con `vertical_alignment="center"` Streamlit mide el texto como de una
  línea y lo que se parte se sale por abajo; para texto largo, `"top"` o
  columnas.
- La portada (`inicio.py`) pinta las tarjetas en filas de tres, un
  `st.columns` por fila, para que en el móvil salgan en orden; y usa
  sentencias, no expresiones sueltas, porque Streamlit pinta el valor de una
  expresión suelta (salía un «None» bajo cada tarjeta).
- Las tarjetas del codificador tienen el dibujo de antes del rediseño
  (vuelto el 03/10/2026 a petición de Álvaro): compactas, número de orden,
  filo a la izquierda (rojo la recomendada), nivel en etiqueta gris y los
  botones pequeños arriba a la derecha. Son contenedores de Streamlit:
  «+ CV» es un `st.button` y «Copiar» un marco de 26 px (`estilo.marco`), lo
  único que necesita JavaScript. Las fichas de la guía usan el mismo dibujo
  (`.gu-ficha`, en rejilla de dos), y el indicador de pasos vuelve a ser un
  recuadro por paso: negro el actual, verde lo hecho.
- **Claves de contenedor únicas por pasada.** El codificador pinta las
  tarjetas dos veces en la misma pasada cuando usa la IA (las del catálogo
  mientras piensa, luego las buenas), y Streamlit no admite dos contenedores
  con la misma `key` en una pasada: paró producción el 03/10/2026 con
  StreamlitDuplicateElementKey (latente desde el rediseño, `oc_2`). Cada
  pintada lleva su sufijo (`_otra_pintada()`) y el CSS busca por el principio
  de la clave. En local no se ve sin claves de IA: lo cubre
  `p_pantalla_codificador_con_ia` de `pruebas/guia.py`, con un modelo de
  mentira.
- **Tres trampas de Streamlit que ya rompieron la pantalla** (03/10/2026):
  el markdown lleva `margin-bottom:-16px` para compensar un párrafo final, y
  con HTML propio (`<div>`) la caja encoge y lo de abajo la pisa (el titular
  tachado del codificador, «Con IA» cortado en la portada): se anula con
  `margin-bottom:0` en ese contenedor. Las píldoras puestas directamente en
  una columna ya no pasan de línea: usar `estilo.pildoras()`, que pide
  `wrap=True`. Y a tamaños pequeños Chromium descolocaba letras («Co dificado
  r SISPE») hasta poner `text-rendering:geometricPrecision`.
- **Al tocar `comun/estilo.py` hay que reiniciar `streamlit run`**: recarga
  las páginas al vuelo, pero no los módulos importados.
- Para verlo de verdad: `~/.venvs/sispe/bin/streamlit run app.py` y capturas
  con Playwright a 1280 y 390 px (Chromium está en `~/.cache/ms-playwright`,
  se lanza con `LD_LIBRARY_PATH=~/apps/libshim/ext/usr/lib/x86_64-linux-gnu`).

Las cinco herramientas: **Codificador SISPE** (el buscador de códigos, que es lo
que hay en producción en `main`), **Codificador de extranjería** (sin IA: el
Excel de códigos de autorizaciones de la oficina, hecho pantalla; las fórmulas
viven en su `motor.py` y los datos en CSV), **Generador de CV**, **Asesor de
formación** e **Informes de orientación**. Se pasan datos entre sí: el codificador manda las
experiencias al generador de CV, y el de CV manda el perfil al asesor de
formación.

## La guía de empleo dentro de la app (02/10/2026)

La Guía de empleo de Madrid (repo privado `empleosant/guia-empleo-madrid`, en
`~/proyectos/guia-empleo-madrid`) entra en la app como **copia**:
`scripts/traer_guia.py` saca de ella `comun/datos/guia/` (capítulos, las 2.040
fichas publicables con la misma regla que su PDF, y la edición). No se edita a
mano: cuando la guía cambie (revisión de abril de 2027) se pasa el script, se
mira el diff y se pasa `pruebas/guia.py`.

Lo único hecho a mano es `comun/datos/ocupaciones_sectores.csv`: prefijo del
código SISPE → capítulo y, si hace falta, apartado. Manda el prefijo más largo;
capítulo «-» quita el sector. Hoy tiene sector el 84 % del catálogo; lo que no
(campo, minas, mar, ciencia) cae en portales generalistas y grandes ETT.
`pruebas/casos_guia.csv` se edita a mano como `casos.csv`.

Dónde sale:

- **Codificador**: un desplegable cerrado «Dónde enviar el CV» bajo las
  tarjetas (sectores en píldoras, fichas y la lista en PDF).
- **Generador de CV**: «Dónde enviarlo» en el paso 4, con los sectores de todas
  las experiencias (las escritas a mano, por el buscador sin IA:
  `cv/estado.codigos_sispe()`). La lista es siempre una hoja **aparte** del
  currículo, en blanco y negro y a dos columnas, con el guion de la llamada de
  la guía y el puesto ya puesto. El PDF se genera solo al pulsar.
- **Informes**: el correo de cierre recibe la lista comprobada del sector del
  objetivo (deducido sin IA y corregible en un selector) y el prompt le pide
  que los nombres salgan de ahí. La IA sigue sin escribir enlaces: las webs
  de empleo de las empresas que nombra en negrita, y los recursos que quien
  orienta marque para la situación de la persona, los añade
  `motor.con_la_guia()` antes de la firma. Los nombres en negrita que no están
  en la guía se señalan para revisarlos.
- **Centros especiales de empleo, aparte** (pedido el 03/10/2026):
  `guia.secciones()` saca a su propia sección los que la guía clasifica como
  centro especial, deja en su sector (y repite en la sección aparte) las
  empresas que dicen tener uno, y añade los del capítulo 9 cuya actividad
  casa con el sector (`CEE_ACTIVIDAD`, hecho a mano). Va antes de los
  portales, con la nota de la guía (70 % de plantilla, discapacidad del 33 %).
  En el CV no sale marcada de entrada, y en los informes solo va al correo si
  se marca «Con discapacidad».
- **Formación** y **extranjería**: plegado, lo que la guía dice de dónde más
  formarse (con el sector del CV en curso ya elegido) y las entidades para
  quien viene de otro país. Las fichas se pintan con `guia.apartados_html()`
  y las clases `.gu-*` de `comun/estilo.py`.

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
- El Excel de extranjería (`CODIGOS_Autorizaciones_extranjeria_SEPT_2026.xlsx`,
  en la carpeta de Drive del curso 2026CE310502) **no entra en el repo**: entran
  los CSV de `herramientas/extranjeria/datos/`, que genera
  `scripts/extraer_extranjeria.py`. Cuando cambie el Excel se pasa el script y se
  mira el diff. `pruebas/casos_extranjeria.csv` solo se edita a mano, como
  `casos.csv`, con cada caso comprobado contra la tabla comentada.
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
