# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

El repositorio está escrito íntegramente en español: código, comentarios,
documentación y mensajes de commit. Sigue esa convención.

## Comandos

```bash
python3 evaluar.py              # aciertos: los 40 casos de casos.csv
python3 estres.py               # robustez: 10 comprobaciones del buscador
python3 evaluar.py && python3 estres.py   # las dos, antes de subir nada

python3 evaluar.py --detalle    # los tres primeros de cada caso
python3 evaluar.py --informe    # vuelca a informe_evaluacion.csv (no versionado)
python3 estres.py --detalle     # cada caso que falla
python3 estres.py --rapido      # salta las dos pruebas que recorren el catálogo

streamlit run app.py            # la app en local (sin claves: solo buscador local)
python3 enriquecer.py           # regenera terminos_ampliados.txt (gasta cuota de Gemini)
```

No hay pytest, linter ni formateador. Las dos baterías **son** la suite; no
llaman a la IA, no gastan cuota y tardan segundos. No existe forma de ejecutar
"un solo test": `estres.py` filtra con `--rapido`, `evaluar.py` no filtra.

Las mismas dos baterías corren en GitHub Actions con cada push
(`.github/workflows/pruebas.yml`), solo si cambia alguno de los archivos del
motor o de los datos.

## Arquitectura

**`app.py` es un único archivo Streamlit de ~4.800 líneas partido en dos por la
marca `# === FIN DEL MOTOR ===`** (línea ~3582). Arriba, el motor: catálogo,
buscador, proveedores de IA, `resuelve()`. Abajo, la interfaz. `motor_pruebas.py`
lee el archivo, lo corta por esa marca, instala un Streamlit y un google-genai de
mentira, y ejecuta solo la mitad de arriba. **Nunca borres ni muevas esa marca**:
si desaparece, las pruebas ejecutan la interfaz entera. Cualquier cosa que el
motor llame (p. ej. `pinta_resultado`, `MANTENIMIENTO`) tiene que estar definida
*antes* del corte aunque conceptualmente sea interfaz.

### Camino de una consulta — `resuelve()` (app.py:3200)

1. **Ocho dígitos** → se busca el código en el catálogo y se contesta.
2. **`busca()`** (app.py:1619): puntuación local tipo TF-IDF sobre el índice
   invertido. Suma por palabra exacta (×3.0), por raíz (×2.2), por término
   ampliado (×1.6), por prefijo compartido y por parecido difflib; multiplica por
   núcleo (coincidencia con las tres primeras palabras de la denominación),
   cobertura, familia CNO, coincidencia exacta y densidad. Los refuerzos del Gist
   entran aquí con 14 puntos por palabra.
3. **Atajo sin IA**: si el primero supera al segundo por más de `VENTAJA_CLARA`
   *y* explica todas las palabras con contenido de la consulta *y* la consulta
   cubre al menos `ENCAJE_MINIMO` del candidato, se contesta al instante. Las dos
   condiciones hacen falta: hay comentarios en el código con el caso concreto que
   cada una evita.
4. **IA**: se le mandan `N_CANDIDATOS` (24) líneas de catálogo y elige. Con
   `UNA_LLAMADA = True` (lo actual) es un solo viaje con `INSTRUCCIONES` +
   `REFUERZO_UNA_LLAMADA`; con `False`, dos viajes secuenciales (`INTERPRETE`
   traduce y luego se rebusca). El interruptor existe para poder medir las dos
   formas con la prueba masiva; el modo entra en la clave del caché para que la
   segunda tanda no salga del caché de la primera.
5. **`verifica()`** (app.py:2365) descarta todo código que no esté en el
   catálogo y toma la denominación de `IDX["por_codigo"]`, nunca del modelo.
   **Ninguna denominación procede de la IA.** Es la garantía de la herramienta.

### Cascada de proveedores

`ORDEN = ["gemini", "mistral", "openrouter"]`. `flujo_modelo()` (app.py:2291)
recorre la cadena y solo puede relevar **antes de haber emitido nada**. Dentro de
cada proveedor, `PROVEEDORES[prov]["modelos"]` es otra cadena de relevo.

Los plazos son la parte delicada y están medidos, no elegidos:

- `ESPERA_MAXIMA = 10` — plazo del transporte (httpx). Mide **silencio, no
  duración**, así que nunca cortó nada. **No lo bajes de 10**: google-genai ≥2.21
  lo manda también al servidor como `X-Server-Timeout` y Google rechaza con 400
  cualquier valor menor.
- `PLAZO_INTENTO = 6` — el corte real de un intento, con reloj propio en
  `_con_plazo()` (app.py:1773), usando un hilo demonio porque una llamada HTTP
  bloqueada no se puede cancelar.
- `PLAZO_RESPALDO = 2.5` — a los 2,5 s sin respuesta sale una segunda petición
  idéntica en paralelo y gana la que vuelva antes. Una de cada cinco peticiones a
  Gemini se queda colgada y no vuelve nunca. Cada respaldo queda anotado en
  `relevos` como `modelo:2.5s:Respaldo`.
- `CADUCIDAD_CASTIGO = 3600` aparta un proveedor (solo si el error dice que el
  cupo del **día** está agotado); `CADUCIDAD_DEGRADACION = 300` baja de modelo.
  Un tope por minuto no aparta ni degrada nada.

Dentro de los hilos **no se toca Streamlit**: `session_state` no es para hilos
secundarios. Apuntar uso, fijar modelo y anotar relevos ocurre siempre fuera.

### Las cuatro capas de vocabulario

Ninguna se edita desde `app.py`:

| Capa | Dónde | Quién |
|---|---|---|
| Palabras vacías y sinónimos | `vocabulario.json` | a mano |
| Jerga por ocupación | `terminos_ampliados.txt` | `enriquecer.py`, una vez |
| Jerga traducida al vuelo | `lexico.json` (Gist) | la IA |
| Correcciones de orden | `refuerzos.json` (Gist) | el uso diario |

Los dos archivos de datos son `codigo:texto` por línea. El catálogo
(`ocupaciones_sispe_ultraligero.txt`, 2.218 ocupaciones) es la fuente oficial y
no se toca. Los Gists son compartidos por toda la oficina: lo que se escriba ahí
cambia los resultados de todos.

### Modo mantenimiento

`?mantenimiento=1` en la URL abre ajustes, diagnóstico y prueba masiva.
**En mantenimiento no se aprende**: ni las búsquedas sueltas ni la prueba masiva
escriben en el Gist, porque ahí se trastea con modelos que no son el de
producción. El corte está en el punto de escritura, no donde se generan los
refuerzos.

## Reglas que ya costaron una sesión

- **`casos.csv` solo se edita a mano**, con el código comprobado contra el
  catálogo oficial, nunca copiado de lo que contesta el motor. Existió un
  `--actualizar` que lo reescribía con la salida del propio motor y consagraba
  las regresiones; hoy el script aborta si se usa.
- `evaluar.py` mide dos cosas: acierto (columna `tope`: 1 o 3) y cobertura (que
  el código correcto entre en los 24 candidatos, mínimo 90 %). La columna
  `resuelto_ia` marca casos que la búsqueda local falla pero la IA resuelve: se
  ven pero no tumban la batería.
- `estres.py` existe porque `evaluar.py` no lo ve todo: el 21/08/2026 un cambio
  en `raiz()` dejó 216 ocupaciones inalcanzables desde el singular con los 40
  casos en verde.
- **Colores**: `TOKENS_CLARO` / `TOKENS_OSCURO` en `app.py`, interpolados en las
  dos hojas de estilo. `.streamlit/config.toml` es el único duplicado, y es
  inevitable: Streamlit lo lee antes de que `app.py` exista.
- **En local no hay claves.** `_credenciales()` levanta
  `StreamlitSecretNotFoundError` sin `secrets.toml`; basta con crear uno vacío
  (ya está en `.gitignore`). El circuito con IA solo se puede medir desplegado.
- El despliegue sale solo desde `main` a <https://buscador-codigos-sispe.streamlit.app>.
  Los horarios de GitHub Actions (el despertador) solo se lanzan desde la rama
  por defecto.

## TRASPASO.md

Es el estado vivo del proyecto: qué se midió, con qué números, qué quedó
pendiente y por qué. Léelo antes de tocar plazos, prompts o la cascada, y
actualízalo al cerrar una sesión que cambie alguna de esas cosas.

## Commits

Mensaje en español, una frase que dice qué cambia y por qué, sin prefijo de
tipo ni scope. Ejemplos reales: «El despertador buscaba la interfaz solo en el
marco principal», «ESPERA_MAXIMA sube a 10: Google rechaza con 400 cualquier
plazo menor».
