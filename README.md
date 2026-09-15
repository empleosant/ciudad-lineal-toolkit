# Caja de herramientas · Oficina de Empleo de Ciudad Lineal

Aplicación Streamlit que reúne varias mini-herramientas de apoyo al trabajo
de orientación. Cada una vive en su carpeta y se registra en `app.py`.

| Herramienta | Carpeta | Estado |
|---|---|---|
| Codificador de ocupaciones SISPE | `herramientas/sispe/` | en uso |
| Generador de CV con IA en pocos pasos | `herramientas/cv/` | en uso |
| Asesor de formación | `herramientas/formacion/` | en uso |
| Generador de informes de orientación | `herramientas/informes/` | en uso |

## Estructura

```
app.py                         punto de entrada: solo la navegación
inicio.py                      portada: una tarjeta por herramienta
comun/                         lo que comparten varias herramientas
  registro.py                  la lista de herramientas (nombre, icono, ruta, descripción)
  ia.py                        cliente de IA (proveedor, modelos de relevo, genera / genera_flujo)
  gist.py                      almacén compartido en un Gist de GitHub
  estilo.py                    CSS común, el menú de la banda negra y el chip de la IA
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
    vista.py                   la pantalla: cuatro pasos (datos, experiencia, formación, documento)
    motor.py                   el currículo como datos, vista previa y el PDF. Python puro
    plantilla.py               el Word sobre el modelo de la oficina, ajustado a una página
    plantillas/Modelo_CV.docx  el modelo de CV de la oficina (fuente de verdad del diseño)
    modelo.py                  prompts: sugerir funciones, estructurar texto libre, redactar perfil
    estado.py                  el currículo en curso en la sesión; por aquí entran otras herramientas
  formacion/
    vista.py                   catálogo de cursos + perfil -> sugerencias
    motor.py                   lee el Excel, preselecciona cursos, cruza lo que devuelve la IA
    modelo.py                  el prompt del asesor
  informes/
    vista.py                   las tres fases de una orientación individual, una por pestaña
    motor.py                   tacha datos personales y arma el PDF de dos páginas. Python puro
    modelo.py                  prompts: leer el CV, preparar la sesión, redactar el correo
    PROTOCOLO_ORIENTACION.md   el protocolo del que sale todo lo anterior
    MATRIZ_TIPOLOGIAS.md       las doce casillas. La lee la app: prompt y desplegable
pruebas/
  motor_pruebas.py             importa el motor para las pruebas
  evaluar.py                   aciertos: 40 consultas con su código correcto
  casos.csv                    los 40 casos (referencia, se edita a mano)
  estres.py                    robustez: que nada se rompa por lo bajo
  informes.py                  que el documento de preparación quepa en dos páginas
  informe_evaluacion.csv       salida de --informe, regenerable, no versionado
scripts/
  enriquecer.py                genera terminos_ampliados.txt (no lo usa la app)
  despertar.py                 despertador (no lo usa la app)
.github/workflows/             programa el despertador
.streamlit/config.toml         colores del tema
requirements.txt               dependencias de Python
packages.txt                   paquetes del sistema (las fuentes del documento)
```

Reglas de la casa:

- `app.py` es el único sitio donde se llama a `st.set_page_config`.
- El motor de cada herramienta (`motor.py`) no importa Streamlit. Recibe
  datos y devuelve resultados; lo que dibuja va en `vista.py`. Así las
  pruebas lo importan tal cual, sin simular pantalla.
- Las llamadas a la IA pasan por `comun/ia.py`: `genera()` para una
  respuesta entera y `genera_flujo()` para verla llegar a trozos.

## Añadir una herramienta

1. Crea `herramientas/<nombre>/vista.py` con la pantalla. Al principio de
   su banda negra llama a `estilo.menu("<nombre>")`.
2. Añade una entrada a `HERRAMIENTAS` en `comun/registro.py`, con su
   descripción. Con eso sale en el menú de todas las páginas y como
   tarjeta en la portada.

El menú va dentro de la página, no en la barra lateral de Streamlit: la
barra se podía plegar y el botón para reabrirla quedaba oculto por el CSS
de la cabecera. Así no depende de ningún control interno.

Las claves de `st.session_state` de cada herramienta llevan su prefijo
(`sispe_`, `cv_`) para que dos páginas no se pisen.

## Cómo se conectan las herramientas

Cada herramienta hace una cosa. Cuando una necesita pasarle algo a otra,
lo hace a través del módulo `estado.py` de la herramienta que recibe,
nunca tocando sus claves de sesión a mano.

Conexiones que hay:

- Codificador → generador de CV (abajo).
- Generador de CV → asesor de formación: el botón «Tomar el perfil del
  generador de CV» construye el perfil con lo que hay en el currículo,
  sin nombre ni contacto.
- Generador de CV → generador de informes: el mismo perfil sirve de
  entrada a la fase de preparación, para no volver a teclear la
  trayectoria.

La primera conexión es codificador → generador de CV: el botón «+ CV» bajo
las tarjetas llama a `herramientas.cv.estado.anade_experiencia()`, y al
lado aparece un enlace para abrir el generador con lo que lleva. Como la
sesión de Streamlit es la misma para todas las páginas, el currículo se
conserva al cambiar de herramienta.

# Generador de CV

Cuatro pasos. Los datos de contacto nunca se mandan a la IA; solo van al
documento. La IA hace tres cosas, todas revisables antes de que entren en
el currículo:

- **Transcribir** lo que se cuente por el micrófono, para no tener que
  teclearlo. El grabador es el de Streamlit; el audio lo transcribe Gemini
  con la misma clave. Hace falta HTTPS (Streamlit Cloud lo es) y dar
  permiso al micrófono en el navegador.
- **Estructurar la trayectoria** contada en texto libre en fichas de
  experiencia y formación. Solo ordena lo que se le ha contado.
- **Sugerir funciones** habituales de un oficio, como vocabulario de
  partida. No son las de la persona: hay que quitar lo que no hiciera.
- **Redactar el objetivo profesional**: la frase que cierra «Otros datos
  de interés», en primera persona y en tres líneas como máximo. El modelo
  de la oficina no lleva apartado de perfil.

El documento sigue el **modelo de CV de la oficina**
(`herramientas/cv/plantillas/Modelo_CV.docx`, convertido de la plantilla
`.dotx`): Trebuchet MS, nombre a 27 pt, contacto con sangría, cabeceras en
barra azul con texto blanco, sectores subrayados, experiencias con viñeta
(puesto en negrita, fechas en cursiva, «Empresa:» y «Funciones:» debajo),
formación y otros datos con viñeta.

Cómo se construye el Word: se abre el modelo, se toman sus párrafos como
prototipos, se vacía y se rellena copiando esos prototipos con los datos.
Así conserva estilos, fuentes, viñetas y márgenes exactos. Si se cambia
el modelo, hay que revisar los índices de párrafo en `plantilla.py`.

**Una página siempre.** Sin Word en el servidor, la altura se estima con
métricas de fuente (DejaVu Sans corregida hacia Trebuchet, con holgura) y
se reduce el tamaño de letra proporcionalmente. Orden de sacrificios,
decidido con la oficina:

1. Se mantienen los bloques por sector y la letra baja hasta el 85 %.
2. Si no basta, se dejan fuera las experiencias más antiguas (las últimas
   de la lista), una a una, hasta quedarse con tres.
3. Solo si aun así no cabe, se quitan los rótulos de sector y la letra
   sigue bajando hasta el 55 %.

La pantalla dice qué se ha aplicado y qué experiencias han quedado fuera;
una casilla permite forzar que entren todas con la letra más pequeña.

El PDF (`reportlab`) replica el modelo con DejaVu Sans, porque Trebuchet
MS es de Microsoft y no está en el servidor; para el documento definitivo
con la fuente exacta, el Word.

# Asesor de formación

Dos entradas: un Excel o CSV con una fila por curso (vale cualquier
estructura de columnas) y el perfil de la persona, como archivo `.md` o
`.txt`, pegado a mano, o tomado del generador de CV. Sin datos
identificativos: el perfil se manda a la IA.

De dónde sale cada cosa:

- El Excel de cursos, del portal de formación de la Comunidad de Madrid:
  <https://vialaboris.comunidad.madrid/Formacion/>.
- El perfil `.md`, de Teams: por protección de datos es la única
  herramienta autorizada en la Comunidad de Madrid para subir el CV de la
  persona. Se le pide un perfil sin datos identificativos en Markdown y se
  arrastra aquí. La pantalla lleva el texto de encargo listo para pegar.

El Excel del portal trae una fila por EDICIÓN (mismo curso en otro
centro u otra fecha). Se agrupa por denominación y la IA razona sobre
cursos; cada tarjeta enseña luego todas las ediciones. Se lee con
`python-calamine`, porque a `openpyxl` le fallan los estilos de ese
archivo. Si la cabecera no está en la primera fila, se busca.

Garantía sobre los cursos: la IA solo elige por número y la app muestra
los datos reales del Excel. Lo que no corresponda a ningún curso se
descarta y se avisa. Con más de 250 cursos distintos se le mandan a la
IA los 250 que más palabras comparten con el perfil.

El prompt conoce la estructura del catálogo: qué es un certificado
profesional (y sus niveles de acceso), un módulo formativo o una
especialidad; que la persona es de Ciudad Lineal salvo que el perfil
diga otra cosa, así que Madrid capital o teleformación antes que
Getafe o Paracuellos; y la fecha de hoy, para no proponer ediciones
ya empezadas.

# Generador de informes de orientación

Traslada a la aplicación el protocolo de orientación individual. Tres
fases, una por pestaña, y la del medio no la escribe la máquina.

El protocolo entero está en `herramientas/informes/PROTOCOLO_ORIENTACION.md`,
que es de donde salen los prompts. Si cambia el protocolo, cambian los prompts.

**Regla de la pantalla: lo obligatorio a la vista, lo opcional plegado.** Esto
no lo usa solo quien lo montó. La calibración de la matriz, la firma o el
expediente no hacen falta para el trabajo de un día corriente, y teniéndolos
delante la herramienta parece mucho más difícil de lo que es. Quien los
necesita abre su desplegable. Para el trabajo del día quedan a la vista once
controles: el currículo y un botón; las notas, el objetivo y la zona; y otro
botón.

**1 · Preparación.** Entra el currículo **sin datos personales**: pegado,
arrastrado como `.md` o `.txt`, o tomado del generador de CV. Como con el
asesor de formación, el CV de la persona solo puede subirse a Teams, que es
la única herramienta autorizada en la Comunidad de Madrid; la pantalla lleva
el texto de encargo para pedir allí el volcado ya anonimizado.

Salen dos cosas: la lectura de la trayectoria en prosa, para leerla en
pantalla, y un **PDF de dos páginas A4** para llevar impreso a la entrevista.

**2 · La cita.** Lo que se habló entra **en prosa o dictado por el micrófono**,
en bruto: se sale de una entrevista y lo último que apetece es rellenar nueve
cajas. El guion de lo que hay que preguntar ya va impreso en la §4 del documento
de preparación, que es donde sirve. Aparte se piden solo los datos que no se
pueden dejar a interpretación: el objetivo acordado y **dónde busca empleo**, que
es lo que decide qué empresas tienen sentido. Y la fila de calibración de la
matriz, en CSV.

Un solo botón hace las dos llamadas —leer y montar— y salen el PDF arriba y la
lectura debajo. Eran dos botones, pero el paso intermedio no decidía nada: quien
prepara una cita quiere el papel.

Cada una de las llamadas a la IA lleva debajo su chip: qué modelo ha
contestado y cuánto ha tardado. Son de tamaños muy distintos, así que un único
cronómetro no diría nada. Al recuperar un expediente de otro día no sale chip:
el tiempo de entonces no se guarda y no se inventa.

**3 · Cierre.** El cuerpo del correo para la persona, con las recomendaciones y
**las empresas para autocandidatura dentro**. En segunda persona y sin jerga:
nunca aparecen las casillas de la matriz ni el diagnóstico técnico. Firma el
orientador, no la oficina. Sale en markdown, se selecciona y se pega en Outlook
con el formato puesto.

El correo se escribe viendo **todo el hilo**: el currículo, la lectura previa y
lo anotado en la cita. Y lo anotado en la cita manda: si contradice la lectura,
gana la cita, porque la lectura eran hipótesis sobre un papel.

## El expediente

Entre preparar la cita y tenerla pasan días, y Streamlit se olvida de todo al
cerrar la pestaña. El expediente es un `.json` que se descarga y se vuelve a
subir: recupera el currículo, la lectura, el documento y lo que llevaras anotado.
Se nombra por el rasgo del perfil, como el PDF, y **se queda en el equipo de
quien lo descarga**: aquí no se guarda nada de nadie, que es lo único compatible
con protección de datos.

Un expediente es un archivo suelto en un disco: puede llegar editado a mano, a
medio copiar o de otra versión. `lee_expediente` acepta cada campo solo si es de
su tipo y descarta el resto, porque lo que pase de ahí se le entrega tal cual al
widget que lo espera y ahí ya no hay red.

## Las empresas para autocandidatura

**Las propone la IA de su memoria, y puede equivocarse.** Es una decisión
tomada a sabiendas: un listado verificado sería mejor, pero no lo hay. Lo que se
hace para que el riesgo sea manejable:

- Cada empresa va con **su tipo y su zona**, no solo con el nombre. Si el nombre
  falla, con «contrata de limpieza, polígono de Julián Camarillo» la búsqueda
  sigue sirviendo.
- Se le pasa **dónde vive y hasta dónde se mueve** la persona, que se pregunta
  en cada caso, para que lo que proponga esté a su alcance.
- Sin direcciones postales, sin teléfonos, sin webs y sin personas de contacto:
  ahí es donde la invención hace daño de verdad.
- El correo dice una vez que conviene confirmarlas, y la pantalla avisa al
  orientador de que las repase antes de enviar.

## Datos personales

El protocolo pide el CV ya anonimizado, pero llega como llega. Lo que se
cuele se avisa y, si es un identificador —correo, teléfono, DNI o NIE—, se
tacha antes de que el texto salga hacia la IA, de modo que no puede aparecer
en ninguna salida. **Lo mismo con las notas de la cita**, que se escriben
deprisa y son donde es más fácil que se escape un nombre. Las fechas, las empresas, las localidades y las
titulaciones se quedan: de ahí sale el diagnóstico. Una dirección postal solo
se avisa, porque tacharla se llevaría por delante la localidad. **El nombre
propio no hay forma de detectarlo**, y eso se dice en pantalla.

## El documento de dos páginas

Sin firma, sin logotipo, sin mención institucional y sin nombre de la
persona, metadatos incluidos: es material de trabajo, no un documento de la
oficina. El archivo se llama por el rasgo del perfil,
`Preparacion_sesion_<rasgo>.pdf`, nunca por la persona, y no lleva sufijo de
versión: se sustituye entero.

| Página | Contenido |
|---|---|
| 1 | Título y entradilla · § 1 La trayectoria en una lectura · recuadro con la tensión central · § 2 Hipótesis de partida · § 3 Direcciones posibles |
| 2 | § 4 Lo que hay que preguntar · § 5 Acciones de arranque · recuadro con el riesgo a evitar |

La forma está copiada de los documentos que se venían haciendo a mano, midiendo
los PDF buenos. Cada pieza es como es por algo:

- **La trayectoria** es una tabla sin cabecera: periodo, qué pasó y cuánto
  duró. Entran también los hitos de formación, con el año suelto y la edad
  aproximada en la columna de la derecha: de ahí sale la edad de la persona.
  Los huecos son filas como las demás y abren con el motivo en negrita
  («**Sin datos.**»), porque son el dato más importante del documento.
- **Los recuadros de aviso** no llevan una etiqueta fija: abren con una frase
  en negrita que cambia con el caso («El desajuste que explica el bloqueo»,
  «Las dos cosas que ordenan esta sesión»).
- **Las direcciones** van en una tabla de tres columnas —qué acredita ya, qué
  falta y por dónde entrar— con el papel y la familia en la primera
  («Principal — Limpieza») y debajo las variantes concretas.
- **Lo que hay que preguntar** son bloques de prosa con el rótulo en negrita y
  **dos líneas de puntos debajo**, para escribir a mano durante la entrevista.
  El rótulo nombra lo que pasa en ese caso («El hueco de 1992 a 2012»), no una
  etiqueta genérica.
- **El riesgo a evitar** cierra la segunda página en un recuadro, y se escribe
  siempre.

La IA puede marcar **negrita** y *cursiva* en cualquier campo de texto; el
motor lo traduce a marcado de `reportlab` **después** de escapar el texto, que
si no un `&` del currículo dejaría el párrafo sin pintar.

### Medidas y fuentes

Se genera con `reportlab`, como el PDF del generador de CV. Las medidas son las
de los documentos buenos: caja de texto de 178 mm, márgenes de 16 mm y 17 mm
arriba, cuerpo de 9,22 pt con interlineado 1,43, tabla a 8,64 pt, y las columnas
de las dos tablas a sus anchos exactos.

Las fuentes son **Caladea** para los títulos y **Carlito** para el texto, que
son las del protocolo. Se instalan con `packages.txt`
(`fonts-crosextra-caladea` y `fonts-crosextra-carlito`), que es como Streamlit
Cloud instala paquetes del sistema. Si faltan, el documento se dibuja igual con
DejaVu o Liberation, pero esas son más anchas: el texto corre más y el ajuste
tiene que bajar la letra un punto.

> **`packages.txt` no admite comentarios.** Streamlit Cloud le pasa el archivo
> entero a `apt-get`, palabra por palabra: una línea que empiece por `#` no se
> ignora, se intenta instalar. El despliegue muere con «Error installing
> requirements» antes de arrancar la aplicación. Solo nombres de paquete, uno
> por línea. Si algún día da problemas, se puede borrar el archivo: la
> aplicación funciona sin él, con la fuente de reserva.

**Dos páginas siempre**: si el contenido se pasa, se baja la letra y se vuelve a
montar, igual que el generador de CV con su página única. Los topes que se le
piden al modelo están calculados para que el peor caso quepa bajando poco
(factor 0,88, aún a tamaño legible), y `pruebas/informes.py` lo comprueba
midiendo.

El anexo del protocolo describe la otra cadena, HTML → `wkhtmltopdf`, con su
factor de 1,307 para compensar que `wkhtmltopdf` maquete a 1038 px en vez de
a 794. **Aquí ese factor no se aplica y no debe aplicarse**: `reportlab` dibuja
en puntos y los milímetros son milímetros. Los tamaños del código son los YA
escalados que se midieron en los PDF buenos, no los del anexo.

## La matriz de tipologías

Vive en `herramientas/informes/MATRIZ_TIPOLOGIAS.md`, al lado del protocolo, y
**no dentro del código**: es una «versión de trabajo pendiente de calibración»,
o sea que va a cambiar, y cambiarla no debería pedir tocar Python.

De ese archivo salen dos cosas:

- **El texto que se le pasa a la IA**: todo lo que hay por encima de la marca
  `<!-- FIN DE LO QUE VE LA IA -->`. Lo de debajo —la hoja de calibración— es
  para quien usa la herramienta, no para el modelo.
- **Las doce casillas del desplegable** de la pestaña de la cita, leídas de los
  encabezados `### A1. Problema de canal`. Si se reescribe el documento hay que
  mantener ese formato: código, punto, nombre.

`pruebas/informes.py` comprueba las dos cosas: que salgan doce casillas con sus
códigos de A1 a D3, que cada una traiga su intervención y su riesgo, y que la
hoja de calibración no se le esté colando al modelo.

### Qué hace la matriz en cada sitio

- **El riesgo a evitar del documento sale de la casilla**, no de una frase fija.
  En A1 y A3 es derivar a formación lo que es posicionamiento; en B1, mandar a
  formación genérica en vez de acreditar lo que ya sabe hacer; en C1, el
  abandono a mitad de itinerario; en D1, dejar a la persona esperando el
  trámite. Antes se escribía siempre el de A1, que es el más frecuente pero no
  el único.
- **Las acciones de arranque salen de la intervención central** de la casilla.
- **La frecuencia real es una pista, no una regla**: se le dice que en una
  oficina urbana se concentran en A1, A3, B1, B3 y C3, y que D1 depende del
  distrito, pero que si el caso pide otra, manda el caso.
- **D1 y D3 nunca se dan por descartadas desde el papel.** En un currículo no se
  ve un trámite pendiente ni una carga de cuidado: se hace constar que hay que
  descartarlas en la sala, y por eso van entre las preguntas.
- **La motivación cambia el correo entero**, no solo el tono: con la persona
  activa, acuerdos exigentes; desgastada, acuerdos más pequeños y verificables y
  se nombra lo ya conseguido; desenganchada, un correo corto con una sola cosa
  pequeña. Atraviesa la matriz entera y no se deduce del currículo.
- **La calibración va plegada en la pantalla**, en un desplegable cerrado de la
  pestaña de la cita. Es investigación, no trabajo del día: el documento y el
  correo salen igual sin tocarla, porque la casilla la propone la IA por dentro.
- **Los campos que filtran recursos** —prestación y su fecha de fin, movilidad,
  disponibilidad real, discapacidad, distrito y radio, idiomas, cargas— no
  cambian la casilla, pero deciden qué se puede proponer. Por eso van entre las
  preguntas del documento, y el correo tiene orden de respetarlos.

### La casilla, de la hipótesis al registro

La IA propone una casilla en la preparación, como hipótesis y con capas. En la
pestaña de la cita viene **precargada en el desplegable**, para confirmarla o
cambiarla: quien la cierra es quien estuvo en la sala. Si se cambia a mano, el
cambio manda y no se vuelve a pisar.

De ahí sale la fila de la hoja de calibración, en CSV y con las columnas de la
hoja: Nº, referencia del caso, casilla, motivación codificada A/D/X, y encaje
con observaciones. El Nº va en blanco a propósito, porque lo lleva la hoja.

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

Sin ese parámetro sí se ve una cosa: bajo los resultados del codificador, un
chip gris con el modelo que ha contestado y lo que se ha esperado
(«Gemini 3.5 Flash Lite · 3.5 s»). Cuando el resultado sale del catálogo sin
pasar por la IA, el chip dice «Coincidencia directa»; y si la IA ha fallado y
se enseña el catálogo sin afinar, no hay chip.

## Dónde se toca cada cosa

- **Modelo de IA**: bloque `PROVEEDORES` de `comun/ia.py`. Es una lista con relevo automático.
- **Proveedor**: constante `PROVEEDOR` en el mismo archivo (`gemini`, `groq`, `mistral`).
- **Prompts del codificador**: `herramientas/sispe/modelo.py`.
- **Puntuación del buscador**: `busca()` en `herramientas/sispe/motor.py`.
- **Vocabulario**: `herramientas/sispe/datos/vocabulario.json`. Si falta, la app arranca en modo mínimo.

## Las baterías de pruebas

Antes de subir cualquier cambio en `vocabulario.json` o en el buscador, las dos
primeras. La tercera, antes de tocar el documento de preparación de sesión o su
prompt. Ninguna llama a la IA ni gasta cuota; entre las tres tardan unos segundos.

```
python pruebas/evaluar.py && python pruebas/estres.py && python pruebas/informes.py
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

**`informes.py` — el documento cabe y el expediente aguanta.** El protocolo
pide dos páginas A4 y lo dice en serio: un documento de tres deja de servir para
lo que sirve, que es llevarlo impreso y escribir encima. Comprueba que cabe
incluso con el contenido en el tope de lo que el prompt permite devolver, que
para conseguirlo no encoge la letra más de la cuenta, que el papel sale sin
membrete y con los metadatos sin autoría, que la frase de cautela va siempre, y
que un `&` del currículo no deja un párrafo sin pintar. Todo medido, no mirado.

Comprueba también el expediente: que va y vuelve entero, y que uno estropeado
—editado a mano, de otra versión, con un número donde va texto— no deja la
pantalla sin arrancar.

Sus fichas de prueba llevan los mismos topes que la sección MEDIDA de
`herramientas/informes/modelo.py`: **si allí se suben, hay que subirlos aquí**,
o la batería deja de probar el peor caso real.

### El motor es un módulo aparte

Las dos baterías hacen `from herramientas.sispe import motor` y prueban
`busca()` directamente. Si alguien mete Streamlit en `motor.py`,
`motor_pruebas.py` lo detecta y para. Antes el motor vivía dentro de la app
y había que cargarla hasta una marca de corte con un Streamlit de mentira;
ya no hace falta.

## Garantía sobre los datos

Ninguna denominación procede del modelo: se toma del catálogo a partir del
código. Los códigos inexistentes se descartan antes de mostrarse.
