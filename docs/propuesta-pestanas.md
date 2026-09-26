# Propuesta de pestañas nuevas para la caja de herramientas

Rama `pruebas-cv` · 26/09/2026

> **Estado (26/09/2026):** la pestaña 1, el codificador de extranjería, ya está
> hecha en esta misma rama (`herramientas/extranjeria/`, `pruebas/extranjeria.py`).
> Lo que se propone cambiar en el Excel tras cotejarlo con el curso está en
> `docs/mejoras-excel-extranjeria.md`.

Cuatro pestañas candidatas, ordenadas por lo que aportan al día a día de la
oficina dividido por lo que cuesta hacerlas. La primera es la que más pesa y
la que está más madura, porque su lógica ya existe: es el Excel de códigos de
extranjería de septiembre de 2026.

| # | Pestaña | Qué resuelve | IA | Esfuerzo | Utilidad |
|---|---|---|---|---|---|
| 1 | Codificador de extranjería | Qué código de autorización y qué fecha fin se graban al inscribir a una persona extranjera | No | Medio | Alta |
| 2 | Preparar la entrevista | Preguntas probables y respuestas con la experiencia real de la persona, según AtréveTE | Sí (calidad) | Medio | Alta |
| 3 | Recursos y ferias del distrito | Qué recurso de empleo hay en cada distrito y qué feria viene | No | Bajo-medio | Media |
| 4 | Autocandidatura por correo | El correo de autocandidatura de ConéctaTE, en la voz de la persona | Sí (rápido) | Bajo | Media |

Mi recomendación: hacer la 1 entera (datos, motor, batería y pantalla), y
después la 2. La 3 vale sobre todo por lo que le da a los informes, y la 4 es
mejor como un paso más del generador de CV que como pestaña.

Un aviso previo: `CLAUDE.md` dice que en esta rama las pruebas no corren en
GitHub Actions, pero `.github/workflows/pruebas.yml` está aquí desde el
17/09/2026 (commit «Las pruebas de esta rama tambien se vigilan en cada
push»). Hay que corregir ese párrafo y, con cada batería nueva, añadir su
línea al workflow.

---

## 1 · Codificador de extranjería

### El problema

Cuando llega una persona extranjera a inscribirse hay que grabar en
SilcoiWeb un código de autorización (R5, T2, A1, IC…), si tiene restricción,
un colectivo en algunos casos y una fecha de fin de vigencia. Las tarjetas no
dicen el código, la normativa ha cambiado dos veces en un año (RD 1155/2024 y
RD 316/2026) y la tabla comentada de junio de 2026 tiene 46 códigos en 20
páginas. Hoy la respuesta está en un Excel con fórmulas que solo puede usar
quien lo tenga abierto en su ordenador.

### Lo que ya está hecho

El Excel `CODIGOS_Autorizaciones_extranjeria_SEPT_2026.xlsx` (carpeta de
Drive «CURSO 2026CE310502 EXTRANJERÍA») es ya la herramienta, solo que en
hoja de cálculo. Tiene nueve pestañas y tres de ellas son la aplicación:

- **IDENTIFICAR**: el árbol de decisión. Paso 1, qué documento trae (siete
  tipos: TIE, resolución sin TIE, solicitud en trámite, documento de
  protección internacional, visado, ciudadano UE o familiar, otro). Paso 2,
  qué pone (la lista depende del documento). Paso 3, fechas: emisión o
  presentación, válido hasta, nacimiento, solicitud de renovación, y si la
  resolución está condicionada al alta en la Seguridad Social. A la derecha
  sale el código, si puede trabajar, restricción y colectivo, la fecha fin a
  grabar, con qué se inscribe y los avisos.
- **CONSULTAR CÓDIGO**: elige un código y salen sus siete campos.
- **FECHAS**: la calculadora de la próxima renovación de la demanda y de si
  la renovación de la autorización se pidió en plazo.

Debajo hay dos hojas de datos que son la fuente de todo: `reglas` (83 filas:
lista, opción, tipo de regla, código o códigos, regla de vigencia, aviso y
marca) y `TABLA DE CÓDIGOS` (46 códigos con sus siete columnas). El resto
son consulta: EN TRÁMITE, TEXTOS TIE, ENLACES, NOVEDADES.

La fórmula central (`IDENTIFICAR!L19`) reparte las opciones en nueve tipos
de regla, y eso es lo que hay que traducir a Python:

| Tipo | Qué hace | Ejemplo |
|---|---|---|
| FIX | Un código fijo | «ARTÍCULO 50 TUE» → P0 |
| DUR | Dos códigos según la duración de la tarjeta (hasta 1,3 años o más) | No lucrativa: R1 o R2 |
| EDAD18 | Dos códigos según la edad | Régimen de menores: M1 o M3 |
| REAG | Reagrupación «no autoriza a trabajar»: R3 o R7 según edad al expedirse y hoy | |
| GEN | La tarjeta no dice el motivo: sugiere por duración y pide la resolución | «RESIDENCIA TEMPORAL AUTORIZA A TRABAJAR» |
| PIMES | Protección internacional: por meses desde el registro (1.º no; 2.º-5.º C1; 6.º+ A1) | |
| PREV | El código de su autorización anterior | Renovación en plazo |
| NO | No se inscribe | Turista, recurso de reposición |
| MSG | Un mensaje en vez de código | «Pide la resolución» |

Y diez reglas de vigencia: la del documento, 01/01/2200, presentación + 2
meses, + 3 meses, + 5 años, hoy + 180 días, nacimiento + 18 años + 90 días,
validez + 1 mes, la anterior, ninguna. Más las marcas que disparan avisos:
RE (concedida tras el 16/04/2026 puede ser regularización extraordinaria),
OLD17 (colectivo 17 en R1 y RF anteriores al 20/05/2025), R6 (no existe
después del 20/05/2025), PLAZO (renovación en los 60 días antes o 90
después), y el aviso de duración rara («la tarjeta dura 4 años: no es
habitual en R5»). Y el bloque de caducidad: caducada sin resguardo, con
resguardo en plazo o fuera de plazo, más de 3 meses sin resolver, menor de
16, entre 16 y 18.

Nada de eso necesita IA. Es un codificador, como el SISPE, pero determinista.

### Cómo encaja en la rama

```
herramientas/extranjeria/
  vista.py              tres pestañas: «¿Qué código es?», «Consultar un código», «Plazos»
  motor.py              codifica(), consulta(), plazos_demanda(). Python puro
  modelo.py             (no hace falta: no hay IA; se omite)
  datos/
    reglas.csv          las 83 filas de la hoja `reglas`
    codigos.csv         los 46 códigos de TABLA DE CÓDIGOS
    duraciones.csv      mínimo, máximo y «lo normal» por código (reglas N:Q)
    tramite.csv         EN TRÁMITE: qué se inscribe en trámite y qué no
    textos_tie.csv      TEXTOS TIE: literal → código
    enlaces.csv         ENLACES: consultas, teléfonos, oficinas, normativa
    novedades.md        NOVEDADES, tal cual, para la pantalla
scripts/extraer_extranjeria.py   lee el .xlsx y reescribe los CSV
pruebas/extranjeria.py            la batería
pruebas/casos_extranjeria.csv     casos comprobados a mano contra la tabla comentada
```

**El Excel sigue siendo el documento de la oficina y no entra en el repo.**
Lo que entra son los CSV, y el script los regenera cuando el Excel cambie
(igual que `scripts/enriquecer.py` genera `terminos_ampliados.txt`). Así
quien mantiene el Excel no tiene que saber nada de la app, y la app no
depende de openpyxl ni de que el Excel esté a mano.

El motor, a grandes rasgos:

```python
from datetime import date
from herramientas.extranjeria import motor

r = motor.codifica(
    documento="TIE",
    opcion="Circunstancias excepcionales / arraigo (social, sociolaboral, familiar, 2ª oportunidad)",
    emision=date(2026, 5, 4),
    valido_hasta=date(2027, 5, 4),
    nacimiento=None,
    solicitud_renovacion=None,
    sin_alta_ss=False,
    hoy=date(2026, 9, 26),
)
r.codigo           # "R5"
r.puede_trabajar   # "SÍ"
r.restriccion      # "N"
r.colectivo        # "—"
r.fecha_fin        # date(2027, 5, 4)
r.se_inscribe_con  # "TIE o resolución (si la resolución exige alta en SS y aún no hay alta: IC)…"
r.avisos           # ["Concedida después del 16/04/2026: si viene de la regularización…"]
r.notas            # ["Edad: —", "Desde la emisión: 4 meses", "Duración de la tarjeta: 1 año"]
```

`hoy` es un parámetro, no `date.today()`: el Excel usa `HOY()` y eso hace
imposible probar la caducidad; aquí la batería fija la fecha. Las sumas de
meses replican `EDATE` de Excel (31/01 + 1 mes = 28/02), que no es lo que
hace `timedelta`, y eso lleva su propia prueba.

`motor.consulta("R5")` devuelve la fila de la tabla de códigos.
`motor.plazos_demanda(hoy, fin_vigencia, solicitud_renovacion)` devuelve la
próxima renovación de la demanda, si es normal o especial, si la solicitud
está en plazo y si han pasado más de 3 meses. El ejemplo de la hoja FECHAS
sirve de primer caso: renovando el 14/09/2026 una T2 que caduca el
14/10/2026 con renovación pedida el 20/08/2026, la próxima es el 28/11/2026 y
es ESPECIAL.

### La pantalla

Regla de la casa: lo obligatorio a la vista, lo opcional plegado.

- **¿Qué código es?** Un desplegable de documento, otro de «qué pone» que
  cambia con el primero (con la línea «Dónde mirar» debajo), y las fechas
  que hagan falta: solo se enseñan las que la regla usa. A la derecha, el
  resultado con el código en grande, y los avisos en su color: el rojo para
  «no se inscribe» y «caducado», el ámbar para «mira la resolución».
  Plegado: la fila entera del código (qué es, se inscribe con, ojo).
- **Consultar un código**: desplegable y ficha. Plegados: EN TRÁMITE (las
  dos listas) y TEXTOS TIE.
- **Plazos**: la calculadora de renovación de la demanda y las causas de
  baja relacionadas (071, 110, 111, 112).

En la banda negra, «datos de septiembre de 2026 · tabla comentada de junio
de 2026 · Manual v22», para que se vea de un vistazo si está desactualizado.
Y un pie fijo que ya está en el Excel: «Es una ayuda para decidir: ante la
duda manda la tabla comentada y la consulta del expediente».

Para el móvil: el codificador se usa en el mostrador, con la tarjeta en la
mano. Tres desplegables y dos fechas caben en una pantalla de teléfono.

### La batería (`pruebas/extranjeria.py`)

Python puro, corre con el `python3` del sistema, salvo la última.

1. **Casos comprobados a mano**: `casos_extranjeria.csv` con documento,
   opción, fechas y el código y fecha fin esperados, comprobados uno a uno
   contra la tabla comentada, nunca copiados de lo que diga el motor. La
   misma regla que `casos.csv`. Empezaría con unos 25: uno por tipo de regla,
   los dos ejemplos que ya trae el Excel, y los casos límite (1,3 años, 16 y
   18 años, 1.º/2.º/6.º mes de protección internacional, renovación el día
   61 antes y el 91 después).
2. **Todas las opciones responden**: recorrer las 83 filas de `reglas` con
   fechas verosímiles y comprobar que ninguna lanza una excepción y que cada
   código que sale existe en `codigos.csv`.
3. **Las listas del Excel y las del CSV coinciden**: que el script de
   extracción no ha perdido filas (se compara el recuento y las claves).
4. **EDATE**: fin de mes, años bisiestos, +216 meses.
5. **Caducidad**: caducada sin resguardo, en plazo, fuera de plazo, más de 3
   meses, larga duración caducada con y sin cita.
6. **Duración rara**: una R5 de 4 años avisa; una P1 de 5 no.
7. **El motor no importa Streamlit** (por `motor_pruebas`).
8. **La pantalla**: con `AppTest`, como en `cv.py`, elegir «TIE» cambia la
   lista de «qué pone» y elegir una opción pinta un código.

### Conexiones con las otras herramientas

Pocas y no urgentes. La útil es hacia los informes: «puede trabajar: con
límites, 30 h/semana» es un dato que condiciona toda la orientación y que el
protocolo dice que hay que preguntar. Un botón «Anotar en el informe» podría
dejar esa línea, sin datos personales, para la fase de preparación. Se hace
después, si se ve que se usa.

### Lo que hay que decidir

1. **Texto libre en «qué pone».** El Excel obliga a elegir de una lista. La
   app podría admitir teclear lo que pone la tarjeta y proponer la opción
   con el mismo `normaliza` del SISPE. Lo dejaría para una segunda vuelta:
   la lista cerrada es lo que hace que la respuesta sea fiable.
2. **Los textos de TIE que añade la oficina.** En el Excel hay una zona
   amarilla para apuntarlos. En la app podrían ir al Gist, como el léxico del
   SISPE, y verse desde cualquier ordenador. Segunda vuelta también.
3. **El cómputo de meses en protección internacional** desde la fecha de
   registro está marcado en el Excel como «pendiente de confirmar con
   Coordinación». La app lo enseña como aviso hasta que se confirme.
4. **Quién la ve.** No es una herramienta de orientación, es de inscripción.
   Va en la portada como las demás, salvo que se quiera una portada por
   perfil, que hoy no existe.

### Esfuerzo

Dos sesiones: una para datos, motor y batería (la lógica ya está escrita en
las fórmulas, es traducirla y comprobarla caso a caso), otra para la
pantalla y la prueba con `AppTest`. El coste real es la comprobación a mano
de los casos contra la tabla comentada, y eso es trabajo tuyo, no mío.

---

## 2 · Preparar la entrevista

### El problema

Después de AtréveTE la persona sale con el método (STAR, preguntas de
cierre, errores típicos), pero en la cita individual lo que hace falta es
**su** entrevista: las preguntas que le van a hacer por el puesto que busca y
las respuestas con su experiencia de verdad, con las palabras puestas. Hoy
eso se hace de viva voz o no se hace.

### Qué haría

Entrada: el perfil sin datos personales (tomado del generador de CV, como
hacen ya el asesor de formación y los informes) y el puesto u oferta a la
que va, pegado. Salida: entre ocho y diez preguntas probables ordenadas por
probabilidad, cada una con una respuesta en primera persona construida con
su trayectoria, tres o cuatro STAR de sus experiencias reales, las preguntas
para el cierre y los errores que más le acechan a ese perfil. Todo en un
texto copiable y en un PDF de una página para llevar.

El prompt sale de los materiales de AtréveTE (el resumen del taller y los
ejemplos STAR por ocho sectores) igual que los de informes salen de
`PROTOCOLO_ORIENTACION.md`: se guardan en
`herramientas/entrevista/GUION_ATREVETE.md` y son la fuente.

### Cómo encaja

```
herramientas/entrevista/
  vista.py        perfil + puesto → botón → texto y PDF
  motor.py        limpia el perfil, convierte la respuesta JSON en secciones, monta el PDF
  modelo.py       el prompt, sobre el perfil CALIDAD (redacta, no clasifica)
  GUION_ATREVETE.md
pruebas/entrevista.py
```

Usa la cadena `modelos_calidad`, sin plazo, como informes. Una llamada por
cita: el cupo no es problema. La batería: que el motor traduce respuestas
completas y a medias sin romperse, que el PDF cabe en una página con el
perfil más largo del banco, que el motor no importa Streamlit.

### Esfuerzo y riesgo

Medio. Lo que cuesta no es el código sino calibrar el prompt hasta que las
respuestas dejen de ser genéricas, como pasó con el correo de cierre: la
prueba que tiene que pasar cada frase es la misma («si vale para cualquier
otra persona, sobra»). Cuenta con dos o tres pruebas reales.

---

## 3 · Recursos y ferias del distrito

### El problema

El correo de cierre de los informes ya dice a qué empresas ir y cómo. Lo que
no dice es qué recurso del distrito le pilla cerca (la Agencia para el
Empleo, la Mesa de Empleo, el centro de formación del barrio) ni qué feria
de empleo viene. Eso está en la web de Empleo Comunitario Madrid, repartido
por 21 distritos y con las ferias en un PDF.

### Qué haría

Pestaña sencilla: eliges distrito y salen sus recursos, con dirección, qué
ofrece y enlace; debajo, las próximas ferias. Sin IA. Y el valor de verdad:
`motor.recursos(distrito)` alimenta el prompt del correo de cierre de
informes, que ya pide «dónde busca empleo», para que las recomendaciones
incluyan el recurso concreto.

### Cómo encaja

```
herramientas/recursos/
  vista.py
  motor.py        filtra y ordena; próximas ferias por fecha
  datos/recursos.csv    distrito, nombre, tipo, dirección, qué ofrece, web, actualizado
  datos/ferias.csv      fecha, distrito, lugar, organiza
pruebas/recursos.py     que todos los distritos tienen algo, que las fechas son fechas, que no hay ferias pasadas sin avisar
```

### Esfuerzo y riesgo

Bajo en código, medio en datos: hay que sacar a mano los recursos de la web
y las ferias del PDF, y **caducan**. Sin alguien que lo actualice cada
trimestre, en un año enseña ferias pasadas. Por eso llevaría un sello de
«actualizado el» bien visible y la batería avisaría si el archivo tiene más
de seis meses.

---

## 4 · Autocandidatura por correo

ConéctaTE gira sobre esto: escribir a las empresas del sector con el CV en
PDF. Una pestaña haría el correo (asunto y cuerpo, corto, en la voz de la
persona, con su experiencia y sin fórmulas) a partir del perfil del CV y del
sector y zona.

Pero es un paso, no una herramienta: encaja mejor como quinto paso del
generador de CV, «Enviar», justo después de descargar el documento. Y el
correo de cierre de informes ya trae las empresas por niveles. Así que lo
propondría como mejora del generador de CV, con el prompt en su `modelo.py`
y la cadena rápida (es corto y se pide muchas veces). Esfuerzo bajo.

---

## Lo que he descartado

- **Leer la TIE por foto.** Ahorraría los desplegables, pero es mandar un
  documento con nombre, NIE y foto a un proveedor de IA. No.
- **Calculadora de prestaciones.** No hay materiales de la oficina de los que
  partir y el riesgo de decir un importe mal es alto.
- **Los temas de oposición** que hay en Drive. Son tuyos, no de la oficina.

## Orden propuesto

1. Codificador de extranjería, entero.
2. Preparar la entrevista.
3. Recursos del distrito, si se ve que los informes lo aprovechan.
4. «Enviar» en el generador de CV.

En cuanto digas, empiezo por el script de extracción y el motor de
extranjería con su batería: es lo que se puede comprobar sin pantalla y sin
claves.
