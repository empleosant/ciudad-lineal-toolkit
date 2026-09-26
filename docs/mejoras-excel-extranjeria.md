# Propuestas de mejora del Excel de códigos de extranjería

Rama `propuesta-pestanas` · 26/09/2026

Excel revisado: `CODIGOS_Autorizaciones_extranjeria_SEPT_2026.xlsx` (carpeta de
Drive «CURSO 2026CE310502 EXTRANJERÍA»). Cotejado celda a celda con los tres
documentos de esa carpeta:

- la **Tabla comentada de autorizaciones administrativas** (junio 2026), que es
  el documento oficial y la fuente que el propio Excel declara;
- el **Curso 2026CE310502**, partes 1 (inscripción y régimen comunitario),
  2 (RD 1155/2024 y RD 316/2026) y 3 (relación de autorizaciones, Manual v22).

**Cómo se leyeron los PDF.** El conector de Drive corta el texto en unos
65.000 caracteres y no baja archivos de más de 10 MB. La tabla comentada y las
partes 1 y 2 caben enteras; la parte 3 (125 páginas) se quedó a la mitad,
justo antes del bloque de protección internacional. Ese final se leyó de la
copia del Drive del escritorio (`/mnt/g/Mi unidad/CURSO 2026CE310502
EXTRANJERÍA/`), con el texto sacado página a página, y se cotejó aparte: sus
hallazgos van marcados «parte 3, pág. n».

Cada punto lleva la celda del Excel y la cita literal de la fuente, con la
página de la tabla comentada cuando se ve. Quien decide es la oficina: lo que
aquí se llama «error» es que el Excel dice algo distinto de una fuente, y lo
que se llama «preguntar» es que las fuentes no coinciden entre sí o no lo
dicen. La app (`herramientas/extranjeria/`) reproduce el Excel tal cual; en
cuanto el Excel cambie, se pasa `scripts/extraer_extranjeria.py` y la batería.

---

## Lo que cambiaría primero

1. **IC solo cuando la resolución lo diga.** La fórmula da IC para cualquier
   resolución si se contesta «Sí» a la pregunta del alta (IDENTIFICAR L19),
   incluidas R0, P1 o A2. La tabla lo limita a las autorizaciones «cuya eficacia
   esté condicionada al alta … (T0, T1, M3, R5…)» y solo «cuando se inscriban
   en base a la resolución concesoria … y el alta aún no se haya producido»;
   «la exigencia del alta … constará en la resolución concesoria de forma
   expresa» (pág. 21). Cambiar la pregunta a «¿La resolución condiciona
   expresamente la autorización al alta en la Seguridad Social, y aún no la
   hay?» (la app ya la hace así) y que la fórmula solo dé IC si el código que
   saldría es T0, T1, T3, M3, R5 o R5 (ex-MENA).
2. **R0 en trámite: con la presentación, no solo con la admisión.** El Excel
   (TABLA F13, EN TRÁMITE A5, reglas B33) exige «admitida a trámite». La tabla
   (pág. 3) y el curso (parte 2) dicen «con acreditación de haber presentado la
   solicitud admitida a trámite» y «con acreditación de haber presentado la
   solicitud, hasta la resolución». Para el sociolaboral y el RE sí es desde la
   admisión; para R0 basta la presentación. El curso (parte 3) llama al papel
   «comunicación de inicio de la tramitación» (art. 97.5): nombrarlo así en
   F13 para que se reconozca. Y la vigencia: el Excel suma 2 meses
   (`EDATE`), la parte 3 dice «Fecha de presentación de la solicitud + DOS
   MESES» y la tabla «60 DÍAS prorrogable hasta resolución» (pág. 3). Uno o
   dos días de diferencia: el Excel sigue al curso, que es más reciente;
   basta dejarlo anotado.
3. **El silencio administrativo, completo.** EN TRÁMITE A38 dice «el resto,
   desestimadas». La tabla dice «salvo (entre otras)» (pág. 25) y cita más
   silencios positivos: modificaciones de los arts. 190-192 «Plazo de
   resolución 1 mes. Silencio estimatorio» (pág. 23), R8 «20 días» (pág. 12).
   El curso (parte 2) añade la lista entera: positivo en prórrogas,
   renovaciones de trabajo, larga duración, modificaciones del art. 192 (1 mes)
   y movilidad internacional (20 días para R8 y R9); negativo en iniciales,
   arraigos, reagrupación y «otros no especificados». Y H26 (R9) debería
   llevar los 20 días como ya los lleva H25 (R8).
4. **F1: la renovación de la tarjeta no va con el plazo 60/90.** La fila 75
   de `reglas` (solicitud de renovación de tarjeta de familiar UE) lleva la
   marca PLAZO, así que el Excel avisa de «FUERA de plazo (60 días antes / 90
   después)». El curso (parte 1): «la solicitud de la tarjeta permanente … se
   deberá presentar dentro del mes anterior a la caducidad …, pudiendo también
   presentarse dentro de los tres meses posteriores … Fecha de vigencia se
   aumentará un mes». Quitar la marca PLAZO de esa fila (la fila 41, resguardo
   de permanente → +1 mes, está bien).
5. **R2 y la Situación Nacional de Empleo.** TABLA H16: «Modificación a
   residencia y trabajo con contrato, sin Situación Nacional de Empleo». El
   curso (parte 2) trata R1 y R2 juntos y dice lo contrario: «Se considera la
   Situación Nacional de Empleo excepto para profesiones de difícil cobertura.
   Debe tramitarse dentro de los 60 días previos a la caducidad (art. 191)».
   Es la orientación que se da a la persona: corregirlo.
6. **Protección internacional: los meses se cuentan desde la presentación.**
   El Excel cuenta desde la fecha de registro (reglas G47/G48, NOVEDADES B14)
   y lo marca «pendiente de confirmar con Coordinación». Ninguna de las dos
   fuentes lo respalda: la tabla dice «desde su presentación» (pág. 17) y la
   parte 3 del curso, que es de septiembre, también: «una vez TRANSCURRIDOS
   SEIS MESES desde la presentación de la solicitud» (pág. 88), «desde la
   fecha de la solicitud» (pág. 94), y sus dos casos prácticos cuentan desde
   la presentación (págs. 104-105). Con «citas de más de un año de demora
   para presentar solicitud» (pág. 82), contar desde el registro daría C1 o
   A1 meses antes de tiempo. Salvo que Coordinación diga lo contrario, volver
   a la presentación y quitar el «pendiente». Y una ambigüedad de la
   fórmula: «a partir del 6º mes» (pág. 17) puede querer decir «cumplidos seis
   meses» (lo que hace la fórmula: DATEDIF < 6 → C1) o «durante el sexto mes»
   (habría que poner < 5). Preguntar.
7. **Colectivo 17 en R1 y RF «antiguas».** El Excel (E15, E21, marca OLD17)
   lo mantiene para las concedidas antes del 20/05/2025. La tabla no hace esa
   distinción: R1 «(Ya no se codifica colectivo 17 Porque se puede modificar en
   cualquier momento)» (pág. 4), RF «(ya no se codifica colectivo 17)» (pág. 8).
   El curso sí la hace (y su caso práctico 2 graba una R1 sin Col. 17). El
   Excel sigue al curso; conviene dejar escrita la fuente en la celda para
   que no parezca un olvido.
8. **M1 o M3 lo decide la tarjeta, no la edad.** La opción «Menor no
   acompañado / régimen de menores» (reglas fila 20) es de tipo EDAD18: menor
   de 18 → M1, mayor → M3. La parte 3 dice otra cosa: M1 incluye a los
   «solicitantes de primera renovación de autorización joven extranjero
   extutelado que alcanza la mayoría de edad», que se inscriben con «TIE
   CADUCADA (M1)» y la solicitud (modelo EX01); M3 es otra autorización con
   su propia tarjeta, «habilita para trabajar por cuenta propia y por cuenta
   ajena». Un chico de 18 o 19 años con la TIE «a favor de menores no
   acompañados» en vigor o con la renovación pedida sale M3 por la edad, y es
   M1. Sustituir esa fila por dos opciones fijas, con la denominación de la
   tarjeta que da el curso: «Autorización residencia temporal a favor de
   menores no acompañados» → M1 y «Autorización de residencia Régimen de
   menores mayoría de edad» → M3 (la del ex-MENA ya existe). La edad se queda
   como aviso.
9. **P1 caducada con cita: los 100 días no son fecha fin.** TABLA G11 y
   FECHAS fila 15 ponen «fecha de la cita + 100 días» en la columna de fecha
   fin de vigencia. La parte 3: «Con la fecha de solicitud de renovación fecha
   de la cita o en fecha fin de vigencia la de personación + 1 mes, en caso
   de no tener cita». Es decir: con cita, la cita va en «solicitud de
   renovación» y la fecha fin no se toca (los 100 días salen solos de la regla
   de la próxima renovación de la demanda); sin cita, fecha fin = hoy + 1
   mes. La fórmula de IDENTIFICAR ya lo hace bien (deja la fecha de la TIE);
   es el texto de G11 y la fila 15 de FECHAS lo que lleva a grabar mal.
10. **RF y M1: la columna «¿puede trabajar?» sin distinguir.** RF: la parte
   3 mantiene dos fichas, la del RD 557 («no autoriza a trabajar
   inicialmente», y con contrato «se solicitará una autorización por
   circunstancias excepcionales tras el arraigo formativo (R5)») y la del RD
   1155 (30 h/semana). C21 dice «SÍ, con límites» para las dos; E21 y la
   marca OLD17 ya separan el Col. 17 por fecha, la columna C no. M1: C35
   dice «SÍ, con límites» y H35 «en actividades que proponga la entidad»; el
   curso: «Conlleva habilitación para trabajar por cuenta ajena y cuenta
   propia», sin límite, restricción N (D35 ya dice N, incoherente con C35).
11. **PI denegada y recurrida: la fecha fin es hoy + 180 días.** Las filas
   51 y 52 de `reglas` (denegación recurrida; resguardo de prórroga de
   derechos) graban «la del documento». Parte 3, pág. 94: «Fecha fin de
   vigencia: fecha de proceso (fecha de inscripción) + 180 días, prorrogable
   por periodos sucesivos de 180 días». El Excel ya tiene esa regla (H180,
   la de UE id. U y del identificador W): ponerla en F51 y F52, añadir la fila
   a FECHAS y anotarlo en G46/G47 y en EN TRÁMITE C18.
12. **El documento nuevo de PI se llama de otra manera y no está claro que
   inscriba.** El Excel llama «Documento de registro de la solicitud (antes
   «manifestación de voluntad»)» al que no inscribe (reglas B47) y «Nuevo
   resguardo de solicitud (desde 12/06/2026), con fecha de registro impresa»
   al que sí (B48). La parte 3 (pág. 102) lo llama «Resguardo de
   Formalización de Solicitud de Protección Internacional (art. 29.1 del
   Reglamento (UE) 2024/1348) … que acredita la condición de solicitante …
   antes de la presentación formal», y avisa (pág. 101): «Verificar siempre el
   tipo de documento entregado». No dice que inscriba. Quien traiga un
   «Resguardo de Formalización» puede casarlo con la opción B48, que inscribe.
   Poner el nombre del curso en B47 y dejar claro en B48 qué documento es el
   que inscribe (el resguardo blanco con sus tres fechas, pág. 104).
13. **El «NUEVO CAMPO» del curso.** En la parte 1, entre los colectivos y los
   datos de la demanda, hay una diapositiva que dice solo: «NUEVO CAMPO / 100
   DÍAS / "fecha de comprobación de la autorización administrativa" / 150
   DÍAS». Los 100 días cuadran con «solicitud de renovación + 100»; los 150 no
   están explicados en el texto. El Excel no menciona ese campo. Preguntar a
   quien dio el curso qué se graba ahí y añadirlo a FECHAS.

---

## Errores: el Excel dice algo distinto de una fuente

Por gravedad. Alta: se grabaría mal un código o una fecha. Media: un aviso o
una orientación equivocada. Baja: redacción.

| Gravedad | Dónde | El Excel | La fuente |
|---|---|---|---|
| Baja | R0 en trámite · TABLA G13, EN TRÁMITE C5, FECHAS E5, reglas F33 | «fecha de presentación + 2 meses» | Tabla pág. 3: «VIGENCIA: 60 DÍAS prorrogable hasta resolución». Curso partes 1 y 3: «+ DOS MESES». Diferencia de 0-2 días según el mes; el Excel sigue al curso. |
| Media | IC · IDENTIFICAR L19 y B13 | IC para cualquier resolución con «Sí» | Tabla pág. 21: solo autorizaciones condicionadas al alta, «T0, T1, M3, R5..», con la exigencia «de forma expresa» en la resolución. |
| Media | R0 en trámite · TABLA F13, EN TRÁMITE A5, reglas B33 | «admitida a trámite» | Tabla pág. 3 y curso parte 2: basta «acreditación de haber presentado la solicitud». |
| Media | Silencio · EN TRÁMITE A38 | «el resto, desestimadas» | Tabla pág. 25 «(entre otras)»; pág. 23 modificaciones 190-192: 1 mes, estimatorio; curso parte 2: lista completa (arriba, punto 3). |
| Media | F1 renovación · reglas fila 75 (marca PLAZO) | avisa «FUERA de plazo (60/90)» | Curso parte 1: «dentro del mes anterior … o tres meses posteriores», vigencia + 1 mes. |
| Media | R2 · TABLA H16 | modificación «sin Situación Nacional de Empleo» | Curso parte 2: «Se considera la Situación Nacional de Empleo excepto para profesiones de difícil cobertura». |
| Alta | PI, cómputo · reglas G47/G48, NOVEDADES B14 | desde la fecha de registro | Tabla pág. 17 y parte 3 págs. 88, 94, 104-105: desde la presentación. El Excel lo marca pendiente. |
| Alta | PI recurrida · reglas F51/F52, TABLA G46/G47, EN TRÁMITE C18 | «la del documento» | Parte 3 pág. 94: «fecha de proceso (fecha de inscripción) + 180 días, prorrogable por periodos sucesivos de 180 días». |
| Media-alta | Documento de registro de PI · reglas B47/B48, EN TRÁMITE A21, NOVEDADES B14 | «documento de registro» que no inscribe / «nuevo resguardo» que sí | Parte 3 pág. 102: «Resguardo de Formalización de Solicitud de Protección Internacional», sin decir que inscriba; pág. 101: «Verificar siempre el tipo de documento entregado». |
| Media | R8 y la TIE · TABLA H25, reglas G63 | «a los 6 meses debe tener TIE» | Parte 3 pág. 122: si la autorización «tuviera una vigencia superior a seis meses, se deberá solicitar la tramitación de la TIE». Es la duración, no el tiempo pasado. |
| Media | Col. 17 en R1/RF · TABLA E15, E21, NOVEDADES B8, reglas H10/H17 | solo en las anteriores al 20/05/2025 | Tabla págs. 4 y 8: ya no se codifica, sin distinguir fechas. El curso sí distingue: el Excel sigue al curso. |
| Media | M1/M3 · reglas fila 20 (EDAD18) | por la edad | Parte 3: M1 sigue con 18 cumplidos y la renovación pedida; M3 es otra tarjeta («habilita para trabajar por cuenta propia y por cuenta ajena»). |
| Media | P1 caducada con cita · TABLA G11, FECHAS E15 | «cita + 100 días» como fecha fin | Parte 3: la cita va en «solicitud de renovación»; sin cita, «personación + 1 mes». |
| Media | M1 · TABLA C35, H35 | «SÍ, con límites», «actividades que proponga la entidad» | Parte 3: «habilitación para trabajar por cuenta ajena y cuenta propia», restricción N. |
| Media | RF del RD 557 · TABLA C21 | «SÍ, con límites» para todas | Parte 3: las del RD 557 «no autoriza a trabajar inicialmente». |
| Baja | R5 por PI o humanitarias · TABLA C20 | «SÍ» (cuenta ajena y propia) | Parte 3, en las dos fichas: «autorización de trabajo por cuenta ajena». |
| Baja | E3 · TABLA G42 | «12 meses o lo que dure el convenio. Renovable 1 vez, máx. 2 años» | Tabla pág. 17: «no excederá de 1 año en caso de convenio y en caso del contrato el de su duración». El tope de 1 año es del convenio; lo que dura es el contrato. |
| Baja | P0 duración · reglas Q3, FECHAS C49/C50 | «5 o 10 años» | Tabla pág. 3: «TIE 10 AÑOS RENOVABLES POR OTROS 10». Solo afecta a la pista de duración. |
| Baja | A1 · TABLA B47 | «desde el 6º mes hasta la resolución» | Tabla pág. 17: «entre el 6º y el 9º mes desde su presentación», vigencia la del documento. |
| Baja | R9 · TABLA H26 | no dice el silencio | Curso parte 1: «20 días para códigos R8 y R9». H25 (R8) sí lo lleva. |

---

## Faltas: está en las fuentes y sirve en el mostrador

Ordenadas por lo que evitan: primero lo que evita no inscribir a quien sí se
inscribe, o inscribir mal.

### Opciones que faltan en `reglas` (el árbol de decisión)

- **Ciudadano UE con la solicitud de inscripción en el registro central, con
  NIE.** El curso (parte 1) lista cinco documentos válidos: DNI, pasaporte,
  «solicitud de inscripción en el registro central con N.I.E», certificado de
  registro y certificado de residencia permanente; los tres últimos sin foto,
  «deben acompañarse del pasaporte o documento de identidad». Con la solicitud
  el Excel no da salida: solo «con certificado» (E, 2200) o «solo DNI» (U,
  +180). Añadir la opción → identificador E. Vigencia: preguntar (¿2200 como
  el certificado, o +180?).
- **Familiar de UE con NIE y documentos del vínculo.** La fila 74 dice «(sin
  NIE)» → W. El curso: «Caso 3: Documentación de vínculo. Con o sin NIE (con
  identificador E + NIE o W) · F1 · fecha de registro + 180 días». Falta el
  caso con NIE (E, misma vigencia). Y que la documentación va «traducida y
  apostillada».
- **Solicitud de E1 con una residencia previa.** Tabla pág. 23: «La solicitud
  de autorización de estancia … (E1) prorroga la autorización de residencia
  que tenga la persona hasta su resolución (art. 54)». Ni en EN TRÁMITE ni en
  `reglas` (L_TRAM): añadir fila → PREV.
- **Autorizaciones concedidas por la DT 5ª.** NOVEDADES B15 dice solo
  «derogada». Tabla pág. 18 y curso parte 2: «En vigor autorizaciones en
  trámite hasta entrada en vigor nuevo RD o concedidas bajo la vigencia de la
  Disposición», «vigentes como máximo hasta 20/05/2027». Siguen inscribiéndose
  (por su naturaleza, R5; la fuente no da el código: preguntar).
- **Prestaciones transnacionales de servicios.** Las fuentes no coinciden: la
  tabla (pág. 22) dice «Ojo, pasan a poder estar inscritos con autorización
  D1, con restricciones»; el curso (parte 2) los lista con temporada,
  deportistas y fronterizos entre los que no se inscriben. Preguntar y, según
  la respuesta, fila en L_OTRO → D1 o línea en EN TRÁMITE.
- **C1 · certificación en desuso.** Tabla pág. 21: «Certificación para la
  inscripción expedida por Área de Trabajo … Suprimido. Supuesto no utilizado.
  En desuso». A la sección de códigos que ya no se usan, por si aparece.

### Opciones y documentos que la parte 3 añade

- **P0 · familiar de británico con la tarjeta caducada.** «Tarjeta
  temporal/permanente de familiar de ciudadano de la UE caducada + Solicitud
  de la TIE acuerdo de Retirada familiar RU (si no han pasado más de 3 meses
  desde la solicitud)», fecha fin «la que consta en la citada TIE». Ni en F9
  ni en `reglas`.
- **R5 ex-MENA de 18 a 23 años.** B38 dice «excepcionalmente hasta los 20».
  La parte 3 añade otro titular: «Joven extranjero extutelado entre 18 y 23,
  que al cumplir 18 no tenía autorización de residencia … o teniendo
  autorización residencia, no pudo renovarla». Con la tabla en la mano, un
  extutelado de 22 años parece imposible.
- **E3 con visado.** F42 dice «TIE o resolución» y L_VIS no tiene entrada
  para prácticas; la parte 3: «Titulares de un visado o una autorización de
  residencia (inicial o renovada) para prácticas».
- **M1 al cumplir 18 · documentos.** EN TRÁMITE A9 y reglas B37 solo dicen
  que el M1 queda prorrogado; la parte 3: «TIE CADUCADA (M1). Solicitud de
  autorización de residencia temporal no lucrativa y régimen de menores
  (Modelo EX01)».
- **E1 · modificación a residencia con excepción de trabajo.** EN TRÁMITE
  A11 y reglas B39 solo hablan de «residencia y trabajo»; la parte 3 incluye
  también la modificación «de residencia con excepción de la autorización de
  trabajo», con trabajo provisional desde la admisión.
- **IC · qué vale como prueba del alta.** Parte 3: «Por cualquier medio de
  prueba válido en derecho». Es la pregunta del mostrador (¿vida laboral,
  contrato?): ponerlo en F32.

### Datos que faltan en TABLA DE CÓDIGOS

- **RF · la prórroga.** Tabla pág. 8: «Si se termina la formación antes de
  finalizar el año de vigencia, la prórroga se condicionará a la prueba del
  título o certificado obtenido y a encontrarse inscrito en el SPE y en BAE».
  Curso parte 2: «Renovación: Condicionada a la obtención del título,
  inscripción en los SPE y búsqueda activa de empleo si finaliza antes del
  año». Es justo el motivo por el que un RF viene al mostrador; H21 no lo
  dice. Y H20 (R5) deja fuera el socioformativo de los arraigos que necesitan
  inscripción para prorrogar (pág. 6), con las excepciones «enfermedad,
  discapacidad, próxima jubilación».
- **R5 · arraigo familiar es de familiares de nacionales de otro estado UE.**
  Tabla pág. 6: «No entran en este supuesto familiares de españoles (R0), sino
  de nacionales UE». Curso parte 2 igual. B20 dice «arraigo familiar» sin más:
  una resolución de 2025 en adelante que diga «arraigo familiar» puede ser R5
  o, si el menor es español, R0. Añadir «(de nacional de otro país UE; si es
  español, R0)».
- **R5 · el tiempo como solicitante de PI no cuenta.** Tabla pág. 6 y curso
  parte 2: «Para el período de estancia no computa el tiempo de tramitación de
  PI». Evita orientar hacia un arraigo a quien no llega a los dos años.
- **RE · tras la concesión hay que desistir de la PI.** Tabla pág. 9:
  «Concedida la autorización, deben solicitar el desistimiento de la PI en el
  plazo de un mes. Durante la tramitación … no tienen que renunciar». H23 no lo
  dice.
- **RE · al concederse, desistir de la PI y pedir la TIE en un mes.** Parte
  3 (DA 20ª): «Deben desistir de la solicitud de PI y solicitar TIE en el
  plazo de 1 mes desde la concesión». Y la prórroga de 4 años «por razones
  justificadas que impidan el acceso al empleo» está en reglas Q16 pero no en
  H23.
- **RE · lo que pone la tarjeta de la DA 20.** Tabla pág. 8: a los
  solicitantes de PI «se les concede una autorización … por razón de arraigo
  social (RE)»; solo la DA 21 es «arraigo extraordinario». Una TIE de la DA 20
  puede decir literalmente «arraigo social». El aviso de la fecha (16/04/2026)
  lo salva solo si se rellena la emisión: decirlo también en la opción B14 y
  en H20.
- **Art. 190 (estudios → residencia y trabajo).** Tabla pág. 23: «Solicitud
  posible dos meses antes o tres después de finalizar estudios»; «1 año si la
  residencia temporal previa es menor a 1 año; si es igual o superior, 4 años
  renovables». El Excel solo tiene los 4 años (FECHAS C48).
- **T1 · puede no tener TIE.** Tabla pág. 13: «Si es inferior a 6 meses podrá
  no tener TIE». Un T1 corto que llega solo con resolución no es sospechoso.
  Y los plazos del que no llega a contratar (curso parte 2): «El trabajador
  debe solicitar a la Oficina de Extranjería en máximo 15 días un documento
  para buscar empleo a través de los SPE»; «El nuevo empleador debe notificar
  el cambio a extranjería en tres meses».
- **R1 · cuándo puede pedir la modificación.** Curso parte 2: «tras 90 días,
  si se obtiene oferta de empleo que cumpla requisitos», «dentro de los 60
  días previos a la caducidad (art. 191)».
- **R3 · supuesto omitido.** Tabla pág. 5: «menores de 18 representados
  legalmente … o > con discapacidad o que objetivamente no sean capaces de
  proveer sus necesidades». B17 dice solo «menores representados». Y la
  vigencia: el curso se contradice («al menos 1 año» y «máx. 2 años»); el
  Excel sigue la primera. Preguntar.
- **R0 · detalles.** Tabla pág. 3: «hijos/as de ambos <26 o > a cargo, o con
  discapacidad» (B13 dice «hijos»); curso parte 2: «5 años, salvo solicitud
  expresa de menor duración», «Renovación: solicitar 60 días antes», «mantiene
  su vigencia incluso tras el fallecimiento del español o disolución
  matrimonial después de 3 años de convivencia», formulario EX-19, «Plazo: 2
  meses (silencio negativo)». «Hijos de español de origen» sí está en R0: la
  parte 3 lista los ocho supuestos (a-h) y termina en ellos.
- **R6 · el arraigo social sin contrato.** Parte 3: «Titulares de
  autorización por arraigo social, exentos de contrato por acreditar medios
  económicos no derivados de actividad por cuenta propia (art. 129)». B22 no
  lo nombra.
- **P1 sin cinco años de residencia.** Parte 3, supuesto 2: pensión
  contributiva de jubilación; nacidos en España con «los tres años
  consecutivos inmediatamente anteriores»; «personas extranjeras que fueron
  españoles de origen»; tutelados «durante los cinco años anteriores».
- **T2 · por qué la tarjeta parece de «3 y pico».** FECHAS A43 lo constata;
  la parte 3 lo explica: «Los efectos de la autorización renovada se
  retrotraerán al día inmediatamente siguiente al de la caducidad de la
  autorización anterior».
- **R8 · traslado intraempresarial.** Tabla pág. 12: «3 años
  directivos/especialistas. 1 año trabajadores en formación». G25 solo
  excepciona el visado de teletrabajo.
- **D1 · el supuesto original.** Tabla pág. 19: «solicitantes de prestaciones
  por desempleo a los que se les haya concedido la excepción … Con vigencia
  vinculada al tiempo de prestación o hasta su denegación». B33 no lo
  menciona.
- **E1 · familiares del estudiante.** Tabla pág. 16: «podrán solicitar
  autorización para entrar o permanecer … No autoriza a trabajar (art. 56)».
  Sin opción en `reglas`.
- **A4 · la prórroga fue automática y pueden pedir otras autorizaciones.**
  Curso parte 2: «Automáticamente se ha actualizado la fecha de fin de todas
  las autorizaciones A4 al 4 de marzo de 2027» (Orden INT/96/2026); tabla
  pág. 19: «podrán solicitar las autorizaciones de estancia y residencia cuyo
  procedimiento pueda iniciarse desde territorio nacional … (DA 19)».
- **A2 en las duraciones.** Tabla pág. 17: «1 AÑO, PRÓRROGA OTRO AÑO»; A2 no
  está en FECHAS C45 ni en reglas N:Q.
- **F1 · condiciones.** Curso parte 1: el fallecimiento no afecta «siempre que
  éstos hayan residido en España, en calidad de miembros de la familia, antes
  del fallecimiento» (H8 dice «se renueva igual» sin condición); de un
  estudiante UE solo se extiende al cónyuge, pareja e hijos a cargo, no a los
  ascendientes.
- **Medida cautelar · qué tiene que decir.** Curso parte 1: «Debe reconocer el
  mantenimiento de la vigencia del permiso que permite al extranjero residir
  y trabajar hasta que se dicte sentencia». Plazos de recurso: reposición un
  mes, contencioso dos meses.

### Protección internacional (parte 3, págs. 80-125)

- **La declaración responsable también en la fase C1.** TABLA F46 y reglas
  G49 solo la piden desde el 6.º mes (A1); G48 sí dice «en ambos casos».
  Parte 3, pág. 86: «Requisito adicional. Declaración responsable del
  ciudadano especificando esta circunstancia»; caso 1 (pág. 104): «C1,
  Colectivo 17 y restricción al trabajo, previa declaración responsable de
  que no se le ha inadmitido a trámite».
- **Las tres fechas del resguardo blanco, y cuál va en «Válido hasta».**
  Pág. 104: «la de solicitud + un mes para la inadmisión; la de caducidad del
  documento a los 9 meses de la solicitud y la de la autorización a trabajar
  transcurridos 6 meses». Se graba la de caducidad (Fecha 2); la Fecha 3 ya
  marca el paso a A1. El Excel no dice cuál de las tres.
- **El canje a la fecha de caducidad.** Pág. 90: «A la fecha de caducidad
  del documento blanco (Fecha 2) el titular deberá comparecer … y le
  sustituirán dicho documento por la tarjeta roja con la inscripción
  «autoriza a trabajar»». El aviso de caducidad del Excel (IDENTIFICAR L23)
  habla de «resguardo de renovación» y «silencio positivo», que no existen
  en PI: para los documentos de la lista L_PI el aviso tendría que decir
  «canje por la tarjeta roja».
- **Fin del recurso de reposición en PI.** Pág. 99: «Las solicitudes
  formalizadas desde el 12 de junio de 2026 ya no pueden recurrirse mediante
  reposición. Las resoluciones desfavorables se impugnan directamente ante
  los tribunales». TABLA H47, EN TRÁMITE A36 y reglas B51/G45 siguen
  diciendo que en PI vale la reposición, sin fecha de corte. Y pág. 101:
  «queda por aclarar si los solicitantes con recursos judiciales pendientes
  mantienen residencia y autorización de trabajo»; el Excel lo afirma sin
  matiz («cualquier recurso en PI prorroga la solicitud»).
- **La manifestación de voluntad puede cambiar.** Pág. 82: la Instrucción
  SEM 1/2025 dice que «la condición de solicitante … se adquiere desde el
  momento de la manifestación de la voluntad», «Hasta la fecha 14 sept. 2026
  no se pueden inscribir. Puede haber modificaciones al respecto en breve».
  El Excel lo niega en seco (reglas G47, EN TRÁMITE A21): añadir el aviso.
- **D1 · el solicitante de prestación sigue en el curso.** Pág. 106: «la
  demanda de empleo tendrá una validez temporal que coincidirá con el tiempo
  en que sean beneficiarios de prestaciones, o hasta la resolución
  denegatoria». El Excel dice que el nombre cambió (H33) pero no cómo grabar
  ese caso ni su fecha fin.
- **C1 penados · certificación y «otros servicios».** Pág. 110: hace falta
  «una certificación expedida por las oficinas de extranjeros o por las
  áreas de Trabajo y Asuntos Sociales», y «la demanda … queda excluida de los
  servicios ofertados (Demandantes de Otros Servicios). Colectivo 10». F46 y
  reglas B78 solo piden la resolución o el auto. Y C46 («NO») frente a H46
  («sí trabajan en lo autorizado»): el curso también lo dice de las dos
  formas (págs. 110-111); una sola frase evitaría la contradicción.
- **R8 · inversores y renovaciones de 5 años.** Págs. 112-113: las
  solicitudes anteriores al 03/04/2025 (LO 1/2025) «se tramitarán y podrán
  ser concedidas», «tres años, renovable por periodos sucesivos de cinco
  años». Una renovación de 5 años dispara el aviso de duración rara (reglas
  P17 = 3,5). Y los visados de movilidad duran «un año o igual a la duración
  de la autorización» todos, no solo el de teletrabajo (G25).
- **Plazos del recurso** (pág. 92: «un mes y dos meses respectivamente si es
  reposición o contencioso-administrativo»), **Instrucciones de 11 de junio
  de 2026 del Ministerio del Interior** (pág. 83), **D1 colectivos que faltan
  en B33** (págs. 107-108: personal de instituciones culturales o docentes de
  otros Estados, funcionarios de Administraciones extranjeras, misiones
  científicas), **investigadores con 12 meses para buscar empleo al acabar**
  (pág. 118).
- **Sin respaldo en el curso**: el número de expediente LARES
  «ES_EA0054388_2026_EXP_» (NOVEDADES B14; el curso solo habla de «número
  de expediente OAR», pág. 85). Las páginas 93 (modelo de declaración
  responsable) y 95 («Instrucciones para OOEE en caso de recurso») son
  imágenes sin texto: mirarlas en el PDF, sobre todo la 95.
- **Los dos casos prácticos de PI salen igual en el Excel**: resguardo del
  02/04/26 inscrito el 09/05/26 → C1 con Col. 17; del 02/10/25 inscrito el
  19/05/26 → A1 sin colectivo (págs. 104-105).

### Lo que la parte 3 da para TEXTOS TIE

Es lo que más falta hace en la hoja, porque es lo que se lee en la tarjeta:

- M1: «Autorización residencia temporal a favor de menores no acompañados».
- M3: «Autorización de residencia Régimen de menores mayoría de edad».
- R5 ex-MENA: «Autorización de residencia y trabajo por circunstancias
  excepcionales EX MENA (art. 174)». Con estas tres, el error M1/M3 de arriba
  se resuelve solo.
- T0 Canadá: «Acuerdo de movilidad entre jóvenes España-Canadá»; ejemplo de
  documento «Autorización de estancia temporal y trabajo. Acuerdo Movilidad
  Canadá» (dice *estancia*, no residencia).
- T0 Chile, Perú y art. 40: «Autorización de residencia temporal y trabajo
  por cuenta ajena Inicial (Nacionalidad Chile, Perú y art 40)». La palabra
  «Inicial» y el motivo separan un T0 de un R5 con el mismo texto de B8.
- R3: «En la TIE constará la inscripción No autoriza a trabajar» (la hoja
  solo tiene la de R7).
- R5 víctimas y colaboradores: la TIE «de un año de duración, en la que no
  figura el carácter provisional ni su condición de colaborador».
- RE: DA 20ª «arraigo social de 1 año»; DA 21ª «arraigo extraordinario, 1
  año de vigencia». B18 lo tiene como pendiente.
- Denominaciones oficiales del bloque final, para la fila «Pendiente» (A18),
  como denominaciones y no como textos de tarjeta confirmados: A2 «Documento
  de identidad de derecho de asilo» / «de derecho a protección subsidiaria»
  (pág. 96); A3 «Documento de Identidad de Apátrida» y «documento
  acreditativo de permanencia provisional» (pág. 97); D1 «Autorización de
  Residencia Temporal con Excepción de la Autorización de Trabajo»; R8
  «Autorización de residencia para emprendedor inicial Ley 14/2013», «para
  Profesional Altamente cualificado», «para investigación UE / nacional»,
  «por traslado intraempresarial ICT UE» (págs. 114-120); R9 «Autorización de
  residencia inicial o renovada de familiar por movilidad» (pág. 123). Y los
  documentos de PI: «Manifestación de Voluntad» (pág. 81), «Resguardo de
  presentación de solicitud» o «documento blanco» (pág. 83), «Resguardo de
  Formalización» (pág. 102), «Resguardo de prórroga de derechos» (pág. 92).

### Lo que la parte 3 enseña como novedad y NOVEDADES no tiene

- T1, documento de intermediación: «tres meses … (OJO. Con el RD 557 la
  vigencia era de 60 días hábiles)».
- RF con contrato: «modificación a residencia y trabajo (4 años). OJO. ANTES
  CCIAS EXCEPCIONALES TRAS ARRAIGO FORMATIVO» (H21 ya lo aplica; falta como
  cambio).
- R5 por PI: «A partir del 16 de abril de 2026 los titulares de
  autorizaciones anuales pueden tramitar su modificación a otras
  autorizaciones de residencia y trabajo», nota de la DG de Protección
  Internacional de 06/05/2026 (B6 solo tiene el 12/06/2026).
- E1: «Estudios de especialización en el ámbito sanitario (Novedad)». RF:
  contratos de formación en alternancia (DA 3ª RD 1065/2025).

### Lo que falta en FECHAS y ENLACES

- **Los mensajes del sistema para U y W** (curso parte 1), además de «ACTZAR
  FCH. AUTORIZ.»: en oficina, primera renovación «MODIFICAR IDENTIFICADOR EN
  LA PRÓXIMA RENOVACIÓN» y segunda «RENOV.PTE.CAMBIO IDEN» (se impide); por
  Internet, «ACTUALICE SU DEMANDA: ACUDA A SU OFICINA» y «DEMANDA NO RENOVADA,
  DISPONE DE UN PLAZO DE DOS DÍAS DESDE LA FECHA PREVISTA PARA SU RENOVACIÓN.
  ACUDA A SU OFICINA DE EMPLEO», que sale también en las renovaciones
  especiales por Internet. Los dos días son lo que hay que saber. Y que las
  bajas 111/112 «se producen automáticamente por proceso Batch».
- **Identificador U repetido**: «Si hay nueva inscripción con identificador U
  distinto: Agrupación de datos» (parte 1).
- **El ejemplo de FECHAS, el del curso.** El caso práctico 1 (parte 1) es «T2
  que caduca el 14/10/26. Aporta solicitud de renovación del 10/08/26»,
  renovando el 14/09/26, respuesta «10/08/2026 + 100 días». El Excel usa
  20/08. Con 10/08, quien vino al curso reconoce el ejemplo.
- **Consulta del expediente en los primeros 7 días** (parte 1): si sale «NO SE
  HA ENCONTRADO LA INFORMACIÓN SOLICITADA» con una solicitud de menos de 7
  días, «es normal. Debe esperar unos días». Y del caso práctico 3: «Si no
  consta registro alguno, no será posible la renovación». Las dos juntas
  evitan negar una renovación por una solicitud recién presentada.
- **Países UE/EEE sin documento de identidad** (parte 1): «Dinamarca,
  Irlanda, Islandia, Noruega». Ahorra la consulta a PRADO.
- **Normativa que el curso cita**: Instrucciones SEM 2/2025 (R0), SEM 1/2025
  (menores nacidos en España, art. 159), Orden INT/96/2026 (A4), Ley 14/2013,
  Reglamento (UE) 2017/1954 (modelo de TIE), Reglamentos 883/2004 y 1231/2010
  (exportación de prestaciones), Directiva 2004/38/CE.
- **Teléfonos**: «902 022 222 (coste de llamada no incluido en tarifa plana)»;
  «060: 24/7 para información general, 8:00-20:00 para atención
  personalizada».
- **Fechas orientativas de tramitación a 1 de septiembre de 2026 en
  Madrid**: la parte 1 tiene esa diapositiva, pero es una imagen y el texto no
  se extrae. Si se consigue, va a ENLACES.
- **Nacionalidad por presunción**: el caso práctico 3 (parte 2) da por buena la
  opción de informar en la oficina; el curso lista los países (Argentina,
  Colombia, Costa Rica, Chile, Ecuador antes de 2008, Guinea-Bissau, Perú,
  Sáhara, Suiza, Santo Tomé y Príncipe) y avisa: «Si se quiere la nacionalidad
  española para el niño, no inscribirle en el consulado del país de origen».
  Cabe una nota en R0.
- **Exportación de prestaciones desde España** (parte 1): inscripción en el
  otro estado «en el plazo máximo de 7 días», «al menos cuatro semanas
  inscrito», «hasta 3 meses, prorrogable por otros 3»; los británicos del
  Acuerdo de Retirada sí pueden exportar. El Excel solo cubre la importación.

---

## Matices de redacción

- **E1 · las 30 horas.** H40 y reglas G24 atribuyen «máx. 30 h/semana, en su
  comunidad o limítrofes» al trabajo automático de estudios superiores. La
  tabla (pág. 16) es ambigua; el cuadro de restricciones del curso (parte 2)
  dice «RF, E1: Máximo 30 horas semanales» para todo E1. Decirlo así.
- **M3 · «sin SNE».** H37 lo dice de M3; en la tabla esa frase está en la fila
  R5 (ex-MENA) (pág. 14) y la de M3 solo habla del alta/IC.
- **T2 · renovación tras una inicial corta.** G30 «1 año si la inicial fue de
  menos de 1 año»; tabla pág. 13: «la duración de la actividad a desarrollar,
  con el máx. de 1 año».
- **T3 · «un sector».** Tabla pág. 13: «ocupación determinada», y «>18 años»
  (T1: «>16 años»).
- **R8 y la TIE.** H25 «a los 6 meses debe tener TIE»; el curso: quien va a
  estar más de seis meses «deberán solicitar … la TIE en el plazo de un mes».
- **Sociolaboral en trámite: solo cuenta ajena.** C20 dice «SÍ» para todo R5;
  EN TRÁMITE C6 sí lo precisa. Poner «(solo cuenta ajena hasta la resolución)»
  en F20.
- **R5 · cinco duraciones en una celda.** G20 mezcla «1 año + prórrogas», «5
  años», «provisionales 1 / definitivas 5» y «admisión + 3 meses». Tres
  líneas (arraigos / víctimas / sociolaboral en trámite) evitan confundir la
  prórroga de un arraigo con la de un trámite.
- **P1 · quien tiene pedida la larga duración.** La tabla lo lista como
  supuesto de P1 (pág. 3) y a la vez dice que la solicitud en plazo prorroga
  la anterior (págs. 3 y 24). El Excel graba «el código anterior»; para el
  pensionista sin autorización temporal previa ese código no existe. Fijar el
  criterio.
- **«Excepcionalmente» con la resolución.** Curso parte 1: «con la TIE o,
  excepcionalmente, con la resolución». Una nota en A2 de TABLA.
- **R5 provisionales · «1 año» es la tarjeta, no la autorización.** G20
  dice «Provisionales: 1 año; definitivas: 5 años». Parte 3: «La vigencia de
  la autorización provisional alcanza hasta la concesión de la definitiva»;
  «La TIE será renovable con carácter anual». Decir «TIE anual renovable
  mientras dura el procedimiento».
- **R7 · «hijos en edad laboral».** B18. La parte 3 dice «el hijo o hija»
  sin condición de edad, y añade los no nacidos en España que acompañan al
  progenitor. Mejor «hijos (aunque la TIE diga «No autoriza a trabajar» si
  se expidió siendo menor)».
- **P1 · plazos de renovación en meses.** EN TRÁMITE A4 usa 60/90 días para
  todo; para la larga duración la parte 3 dice «los dos meses inmediatamente
  anteriores o tres posteriores». Diferencia de días.
- **E1 · tipos que faltan en B40.** Parte 3: «Educación secundaria
  postobligatoria», «Estudiante Convenio Andorra», «Estancia en base a
  instrucciones dictadas Consejo Ministros».
- **E2 «improrrogables»** (G41), **M2 «NIE + pasaporte»** (F36), **R6
  duración** (reglas N8:Q8), **RF «contrato de formación en alternancia»**
  (H21), **R7 «16+»** (G7/G9: la tabla dice «edad laboral» y «mayoría de
  edad»): ninguna fuente lo dice así. No es que esté mal; es que no se puede
  comprobar con esta documentación. Dejar la fuente en la celda o quitarlo.

---

## Lo que las fuentes sí confirman

Para que se sepa que se ha mirado: el indicador de restricción S/N de los 46
códigos coincide con la tabla en todos; los colectivos (C1 con 17, penados con
10, A1 quita el 17, R0 solo «otros a cargo»); las fechas fijas y sumadas (IC
+6 meses, RE y sociolaboral +3 meses prorrogables, T1 intermediación +3 meses,
M2 nacimiento + 18 años + 90 días, certificado UE 01/01/2200, A4 04/03/2027,
U y W +180 días, F1 desfavorable +5 años, permanente +1 mes, P1 caducada cita
+100 días o hoy +1 mes); las duraciones de todos los códigos; los documentos
con los que se inscribe cada uno; la lista de lo que no se inscribe; el plazo
60/90 y los 3 meses del silencio; la fórmula de la próxima renovación de la
demanda (+91, +7, +100) con las bajas 071/110/111/112 y el aviso «ACTZAR FCH.
AUTORIZ.»; y los enlaces, correos, teléfonos y oficinas.

---

## Mejoras de forma del Excel

- **Una columna FUENTE en TABLA DE CÓDIGOS** (tabla pág. X / curso parte N),
  como ya tiene TEXTOS TIE. Es lo que permite, dentro de un año, saber de
  dónde salió cada celda y si sigue vigente.
- **Una pestaña PENDIENTE** con lo que está por confirmar (cómputo de PI, el
  campo de 150 días, R3 «1 o 2 años», prestaciones transnacionales, R0 «60
  días o 2 meses», vigencia del UE con solicitud de registro), con quién lo
  confirma y cuándo. La app puede enseñarla tal cual.
- **La pregunta del alta en SS**, redactada como la tabla (arriba, punto 1).
- **Las opciones nuevas de `reglas`** (UE con solicitud de registro, familiar
  UE con NIE, solicitud de E1, DT 5ª) y la marca PLAZO fuera de la fila 75.
- **El ejemplo de FECHAS**, el del curso (10/08/2026).
- **Una celda de versión** («revisado el dd/mm/aaaa») que la app pueda leer y
  enseñar en la banda, en vez de «actualizado septiembre 2026» dentro del
  título.

## Qué cambia en la app con cada propuesta

El motor reproduce el Excel, así que casi todo lo anterior es cambiar el Excel
y pasar `scripts/extraer_extranjeria.py`: las opciones nuevas, los textos, la
vigencia H180 de la PI recurrida (punto 11) y las dos filas M1/M3 (punto 8)
son datos. Tres propuestas necesitan además tocar `motor.py`, porque cambian
la lógica: limitar IC a los códigos condicionados al alta (punto 1), un
plazo distinto para la renovación de la tarjeta F1 (punto 4) y un aviso de
caducidad propio para los documentos de protección internacional (canje por
la tarjeta roja en vez de resguardo de renovación). Cada una llevaría su caso
en `pruebas/casos_extranjeria.csv`.
