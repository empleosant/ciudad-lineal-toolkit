# Caja de herramientas · Oficina de Empleo de Ciudad Lineal

Aplicación Streamlit que reúne varias mini-herramientas de apoyo al trabajo
de orientación. Cada una vive en su carpeta y se registra en `app.py`.

| Herramienta | Carpeta | Estado |
|---|---|---|
| Codificador de ocupaciones SISPE | `herramientas/sispe/` | en uso |
| Generador de CV con IA | `herramientas/cv/` | en construcción |

## Estructura

```
app.py                         punto de entrada: solo la navegación
comun/                         lo que comparten varias herramientas
  ia.py                        cliente de IA (proveedor, modelos de relevo, genera / genera_flujo)
  gist.py                      almacén compartido en un Gist de GitHub
  estilo.py                    CSS común: colores, cabecera, bloques repetidos
  texto.py                     normaliza()
herramientas/
  sispe/
    vista.py                   la pantalla del codificador: lo único que dibuja
    motor.py                   búsqueda en el catálogo. Python puro, sin Streamlit
    modelo.py                  prompts y llamadas a la IA del codificador
    aprendizaje.py             lo que guarda en el Gist: léxico y refuerzos
    datos/
      vocabulario.json         palabras vacías y sinónimos base
      ocupaciones_sispe_ultraligero.txt   catálogo oficial (nombre exacto)
      terminos_ampliados.txt   jerga por ocupación (lo genera scripts/enriquecer.py)
  cv/
    vista.py                   página provisional del generador de CV
pruebas/
  motor_pruebas.py             importa el motor para las pruebas
  evaluar.py                   aciertos: 40 consultas con su código correcto
  casos.csv                    los 40 casos (referencia, se edita a mano)
  estres.py                    robustez: que nada se rompa por lo bajo
  informe_evaluacion.csv       salida de --informe, regenerable, no versionado
scripts/
  enriquecer.py                genera terminos_ampliados.txt (no lo usa la app)
  despertar.py                 despertador (no lo usa la app)
.github/workflows/             programa el despertador
.streamlit/config.toml         colores del tema
requirements.txt               dependencias
```

Reglas de la casa:

- `app.py` es el único sitio donde se llama a `st.set_page_config`.
- El motor de cada herramienta (`motor.py`) no importa Streamlit. Recibe
  datos y devuelve resultados; lo que dibuja va en `vista.py`. Así las
  pruebas lo importan tal cual, sin simular pantalla.
- Las llamadas a la IA pasan por `comun/ia.py`: `genera()` para una
  respuesta entera y `genera_flujo()` para verla llegar a trozos.

## Añadir una herramienta

1. Crea `herramientas/<nombre>/vista.py` con la pantalla.
2. Añade un `st.Page` a la lista `HERRAMIENTAS` de `app.py`.

Las claves de `st.session_state` de cada herramienta llevan su prefijo
(`sispe_`, `cv_`) para que dos páginas no se pisen.

# Codificador de ocupaciones SISPE

Herramienta de apoyo para localizar códigos del catálogo SISPE antes de
grabarlos en SilcoiWeb.

## Las cuatro capas de vocabulario

De más estable a más viva. Ninguna se toca desde `app.py`.

| Capa | Dónde | Quién la mantiene |
|---|---|---|
| Palabras vacías y sinónimos base | `vocabulario.json` | tú, a mano |
| Jerga de cada ocupación | `terminos_ampliados.txt` | `enriquecer.py`, una vez |
| Jerga traducida sobre la marcha | `lexico.json` (Gist) | la IA, sola |
| Correcciones de orden | `refuerzos.json` (Gist) | el uso diario |

## Secrets de Streamlit

```toml
GEMINI_API_KEY = "..."
GIST_ID = "..."        # opcional: activa el aprendizaje compartido
GITHUB_TOKEN = "..."   # token classic, solo con permiso "gist"
```

## Modo mantenimiento

Añade `?mantenimiento=1` a la dirección para ver correcciones manuales,
diccionarios aprendidos y diagnóstico. Sin ese parámetro la herramienta se ve
limpia.

## Dónde se toca cada cosa

- **Modelo de IA**: bloque `PROVEEDORES` de `comun/ia.py`. Es una lista con relevo automático.
- **Proveedor**: constante `PROVEEDOR` en el mismo archivo (`gemini`, `groq`, `mistral`).
- **Prompts del codificador**: `herramientas/sispe/modelo.py`.
- **Puntuación del buscador**: `busca()` en `herramientas/sispe/motor.py`.
- **Vocabulario**: `herramientas/sispe/datos/vocabulario.json`. Si falta, la app arranca en modo mínimo.

## Las dos baterías de pruebas

Antes de subir cualquier cambio en `vocabulario.json` o en el buscador, las dos.
Ninguna llama a la IA ni gasta cuota; entre las dos tardan unos segundos.

```
python pruebas/evaluar.py && python pruebas/estres.py
```

**`evaluar.py` — aciertos.** Pasa los 40 casos de `casos.csv`. Dice si el
código correcto sale donde debe.

- `--detalle` enseña los tres primeros de cada caso.
- `--informe` vuelca a `informe_evaluacion.csv` lo que devuelve el motor:
  esperado, estado, en qué posición salió el código correcto y los tres
  primeros resultados. No toca `casos.csv`.

`casos.csv` es la referencia y **solo se edita a mano**. Existió un flag
`--actualizar` que la reescribía con la salida del propio motor: eso convertía
en «correcto» lo que el buscador contestara ese día, de modo que una regresión
quedaba consagrada como verdad en la siguiente pasada. Ya no existe; si alguien
lo usa, el script aborta y explica por qué.

**Cada consulta real que falle debería acabar en `casos.csv`**, con el código
comprobado contra el catálogo oficial o contra un caso ya grabado en SilcoiWeb,
nunca copiado de lo que contesta el motor. La columna `tope` admite 1 (tiene que
salir el primero) o 3 (basta con que esté entre los tres primeros).

**`estres.py` — robustez.** No afirma qué código es correcto: comprueba que el
buscador se comporta con sensatez pase lo que pase. Ocho pruebas: que no
reviente con basura, que dé igual escribir con acentos o sin ellos, que el
singular encuentre lo que el catálogo guarda en plural, que cada ocupación se
encuentre a sí misma, que ningún código salga inventado, que dos consultas
iguales den lo mismo, que la segunda mitad de una consulta coordinada cuente y
que la búsqueda siga siendo rápida.

- `--detalle` enseña cada caso que falla.
- `--rapido` salta las dos pruebas que recorren el catálogo entero.

Hace falta porque `evaluar.py` no lo ve todo. El 21/08/2026 un cambio en el
lematizador dejó 216 ocupaciones inalcanzables desde el singular y `evaluar.py`
solo detectó dos casos raros. La prueba de convergencia lo canta entero.

### El motor es un módulo aparte

Las dos baterías hacen `from herramientas.sispe import motor` y prueban
`busca()` directamente. Si alguien mete Streamlit en `motor.py`,
`motor_pruebas.py` lo detecta y para. Antes el motor vivía dentro de la app
y había que cargarla hasta una marca de corte con un Streamlit de mentira;
ya no hace falta.

## Garantía sobre los datos

Ninguna denominación procede del modelo: se toma del catálogo a partir del
código. Los códigos inexistentes se descartan antes de mostrarse.
