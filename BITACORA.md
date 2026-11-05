# Bitácora

Una entrada por sesión: qué probamos, qué esperábamos, qué pasó, qué decidimos.

---

## 2026-09 — Descarte de la v2 (reseñas de comercios de barrio)

**Qué probamos:** razonar qué señal contiene "fui y no lo tenían" en reseñas de Google Maps.
**Qué esperábamos:** detectar productos ausentes del mercado argentino.
**Qué pasó:** quien va a un local de barrio espera que el producto exista. La señal es
casi siempre falta de stock, no ausencia de mercado.
**Qué decidimos:** pasar a señales donde la persona ya tiene el producto (complementos) y,
después, a votos con los pies.

## 2026-10-29 — Prueba de acceso a fuentes de datos

**Qué probamos:** pedir datos sin credenciales desde el entorno de desarrollo en la nube.

| Fuente | Resultado |
|---|---|
| API de Mercado Libre `/sites/MLA/search` | **403** sin token |
| Listado web de Mercado Libre | muro de login para tráfico no autenticado |
| Tiendamia, Google Trends, Reddit (desde el shell) | bloqueados por la política de red del entorno |
| Rankings courier publicados en prensa | accesibles vía búsqueda web |

**Qué esperábamos:** que la API pública de Mercado Libre alcanzara para `contar_oferta`.
**Qué pasó:** no alcanza. Necesitamos una app registrada y un access token.
**Qué decidimos:** separar las fuentes en adaptadores con un contrato común, y construir y
testear el harness sobre datos sintéticos rotulados mientras se resuelve el acceso real.
El adaptador de Mercado Libre falla de forma explícita (`sin_credenciales`) y el sistema
devuelve `insuficiente` en lugar de inventar números: verificado corriendo la política
heurística contra la fuente en vivo.

## 2026-10-29 — Primer harness corriendo

**Qué probamos:** tres políticas sobre 8 pistas sintéticas con verdad etiquetada.
**Qué pasó:** fija y heurística aciertan 6 de 8; la heurística usa la mitad de llamadas a la
fuente (20 contra 40). Las dos fallan en las mismas pistas: P1 (nombre en inglés,
"nut milk maker") y P6 (un adaptador casero que apunta al consumible que falta). Son
exactamente los casos que requieren interpretación semántica.
**Qué decidimos:** esas dos pistas son la hipótesis concreta para el agente con LLM.
Si no las resuelve, el LLM no aporta sobre la heurística.

## 2026-10-29 — Prueba mínima de datos (la que faltaba)

**Qué probamos:** obtener de verdad, sin credenciales y desde código, los datos que el
sistema necesita. Criterios fijados antes de mirar: `data/prueba_datos/CRITERIOS.md`.
**Qué esperábamos:** habíamos diseñado el harness asumiendo que los datos se conseguían.
**Qué pasó:** el precio exterior se consigue (Tiendamia, Amazon). La oferta local en
Mercado Libre, que es la verificación central, no: 403 en todos los intentos. Los "más
vendidos" de Mercado Libre responden la mitad de las veces. El ranking de Tiendamia
necesita navegador. Además, Mercado Libre ya vende por Compra Internacional los
repuestos que suponíamos faltantes. Detalle en `data/prueba_datos/RESULTADOS.md`.
**Qué decidimos:** no-go para el diseño actual hasta repetir la prueba con un token de
Mercado Libre. Error de proceso que reconocemos: construimos el harness antes de probar
los datos.

## 2026-10-29 — Scraping desde el navegador: los datos se consiguen, la hipótesis no

**Qué probamos:** los 10 productos de la prueba en el listado de Mercado Libre, desde el
navegador real con sesión iniciada.
**Qué pasó:** 10 de 10 respondieron. Y los 10 tienen oferta local, incluidos los que
usábamos como ejemplos de ausencia (máquina de leche vegetal: 434 publicaciones).
**Qué decidimos:** el acceso a datos tiene salida (navegador, escala chica, declarado).
La hipótesis de "productos que faltan" pierde sustento con los ejemplos obvios: hay que
definir de dónde salen candidatos donde la ausencia sea plausible antes de seguir.

## 2026-10-29 — La señal no es "falta", es "solo llega por cross-border"

**Qué probamos:** 6 búsquedas en Mercado Libre de productos del ranking de más vendidos
de Amazon (Home & Kitchen). Datos en `data/prueba_datos/amazon_vs_ml_2026-10-29.json`.
**Qué pasó:** ninguno falta, pero en los que la búsqueda encuentra el producto correcto,
la oferta es casi toda Compra Internacional: Owala FreeSip 43 de 48 publicaciones, cortina
Barossa 40 de 52. Llegan hoy o mañana solo 4. Y en 3 de 6 búsquedas Mercado Libre devuelve
otra cosa ("zevo" trae cámaras Instax Evo; "upsimples", billeteras).
**Qué decidimos:** proponer al grupo reformular: medir qué parte de la demanda se atiende
solo por cross-border (con sus límites de 5 envíos al año y 3 unidades), y usar el LLM para
saber si dos publicaciones son el mismo producto, que es donde la búsqueda falla.

## 2026-10-29 — El voto con los pies desmiente la lectura anterior

**Qué probamos:** separar las ventas ("+N vendidos" visibles en el listado) entre
publicaciones de Compra Internacional y publicaciones locales, en 6 productos. Datos en
`data/prueba_datos/votos_pies_ml_2026-10-29.json`. Tiendamia ya no publica ranking.
**Qué pasó:** la oferta es mayormente internacional (27 a 43 publicaciones por página),
pero casi no vende: 0 a 4 publicaciones internacionales con ventas, contra 2 a 11 locales.
En los 6 productos, las ventas visibles se concentran en un puñado de publicaciones locales.
**Qué decidimos:** la lectura de la entrada anterior ("solo llega por cross-border") miraba
la oferta, no los votos. Los compradores eligen stock local y no esperan. La señal candidata
pasa a ser: demanda probada (ventas) concentrada en pocos vendedores locales.

## 2026-10-29 — Primera corrida del MVP sobre datos reales

**Qué probamos:** top 30 de Amazon en Cocina → 23 con marca → búsqueda en Mercado Libre →
emparejamiento → clasificación. El paso LLM lo hizo Claude en el chat (sin API key).
Datos en `data/mvp/`.
**Qué pasó:** 17 de 23 no se venden en Mercado Libre con stock local, y la demanda de la
búsqueda la toman sustitutos locales; 4 ya se venden; 1 dudoso; 1 sin demanda visible. El
baseline "menciona la marca" acertó 4 de 15 publicaciones con ventas (6 si se cuentan
probable y dudoso) y habría dado por atendidos 4 productos que no lo están.
**Qué decidimos:** el método produce una salida con sentido y el LLM tiene un trabajo medible
(emparejar). Falta: una medida de competencia mejor que el volumen (las balanzas dominan el
ranking por ser masivas), un segundo anotador, y validar con alguien del rubro si la marca
pesa en la decisión de compra.

## 2026-10-29 — Cuatro chequeos para "¿por qué no se vende?" y corrección del MVP

**Qué probamos:** el MVP anterior suponía que "no se vende acá pero venden parecidos"
significaba demanda insatisfecha. Lo desafiamos con cuatro explicaciones que compiten:
precio, espera, preferencia por otras opciones y falta de demanda. Las sumamos al harness
como skills (`chequear_*`) con una política de diagnóstico, y las corrimos sobre una foto
nueva de las 23 búsquedas (1.372 publicaciones, todos los precios). Datos y resultados en
`data/diagnostico/`.
**Qué pasó:** 16 de 23 no compiten en precio (cuestan 2,3 a 8 veces lo que se vende);
4 ya se venden acá; 1 sin demanda; 2 candidatos a probar. De 387 publicaciones
internacionales de estos productos, ninguna tiene ventas visibles (verificamos que el
contador sí aparece en otras internacionales). En los 4 productos que están en los dos
canales, la gente compra el local aunque el internacional cueste igual o menos: la espera
pesa. Primera versión de la política tenía un error de orden: daba como "oportunidad" a
productos que ya se venden; lo corregimos.
**Qué decidimos:** la conclusión del MVP anterior era incorrecta y la reemplazamos. El
único candidato sólido es el mixer Turelar (más barato que los Oster que se venden, y no
vende): separar espera de marca requiere otro dato. Pendientes: elegir mejor los
sustitutos (hoy entra ruido como la cinta Gorilla Tape) y comparar contra gama parecida.

## 2026-11-05 — API de Mercado Libre y segunda foto

**Qué probamos:** (1) la API de Mercado Libre sin token desde una conexión hogareña, no desde
la nube; (2) repetir la captura de las 23 búsquedas una semana después, ahora con un script
reutilizable (`scripts/captura_ml.js`) que guarda los títulos, y emparejar con reglas
(`scripts/emparejar.py`).
**Qué esperábamos:** que el 403 de la búsqueda fuera por la IP de la nube; que la foto nueva
pudiera cambiar las conclusiones.
**Qué pasó:** desde la conexión hogareña la API responde igual: búsqueda 403 `forbidden`,
más vendidos 401, `/products/search` y `/trends` 403; solo responden categorías. La foto
nueva (1.336 publicaciones) da las **mismas 23 conclusiones** que la del 29/10, y 0
publicaciones internacionales del producto con ventas. Encontramos un error del criterio:
para Gorilla Grip y KitchenAid exige "abrelata" en el título y se pierde "Abridor de latas",
así que subcuenta el producto (Gorilla Grip: 6 marcados, unos 20 reales). No lo corregimos
para que las dos fotos sean comparables; no cambia la conclusión (Gorilla Grip sigue costando 4 veces lo que
se vende; KitchenAid sigue "ya se vende acá"). En la foto nueva el rango de precio de los
16 que no compiten es 1,9 a 6,3 veces (antes 2,3 a 8,1).
**Qué decidimos:** la fuente de datos es la captura desde el navegador, declarada como
limitación. La API queda para quien tenga una app con token (`make prueba-api`). Siguiente
paso: emparejamiento con LLM contra estas reglas, empezando por los errores conocidos.

## 2026-11-05 — API de Mercado Libre con token: cerrada igual

**Qué probamos:** sacar un token válido con la app tp-iaa (authorization_code) y repetir las
llamadas. El usuario cargó el código y la Secret Key en su navegador; guardamos solo códigos
de respuesta en `data/prueba_datos/api_con_token_2026-11-05.json`.
**Qué esperábamos:** que con token la búsqueda respondiera.
**Qué pasó:** el token es válido (`/users/me` responde 200), pero búsqueda por texto, por
categoría, más vendidos, catálogo y tendencias dan 403 "At least one policy returned
UNAUTHORIZED". Están cerradas por política para una app no certificada, con o sin token.
**Qué decidimos:** la API de búsqueda queda descartada como fuente. La fuente es la captura
desde el navegador (`scripts/captura_ml.js`), declarada como limitación.

## 2026-11-05 — Reencuadre: leer los votos, no contarlos (piloto divergente)

**Qué probamos:** el MVP hacía solo la mitad convergente: partía de un producto de Amazon y
preguntaba por qué no se vende. El voto con los pies lo usaba como contador. Reencuadre
(fundamento Cyberseren: automatizar la función empresarial): leer **qué eligió la gente y
qué dejó pasar** en cada búsqueda, abducir hipótesis de necesidad, y recién ahí refutar.
Fijamos una partición dev/test de las 23 búsquedas (semilla 20261105; la tostadora quedó en
test pero la habíamos usado de ejemplo: marcada como contaminada). Sobre 6 búsquedas de dev,
Claude leyó la vista de votos (paso LLM a mano, sin API key) y escribió 6 hipótesis con
citas; el guardrail en código (`harness/votos.py`) verifica cada cita. Baseline sin LLM:
log-odds de términos del título en lo que vende contra lo que no.
**Qué esperábamos:** que salieran explicaciones que el chequeo de precio no ve.
**Qué pasó:** salieron seis (voltaje, lenguaje del título, lonchera que calienta, sustitución
por multifunción, silicona reutilizable, formato chico para regalar). Las 6 pasan el
guardrail. Intentamos refutar dos con datos de dev (`scripts/convergencia_piloto.py`):
- H2 (lenguaje) **refutada en el mixer**: entre publicaciones locales, "licuadora/batidora
  de inmersión" vende 5 de 8 y "minipimer" 9 de 15. En el organizador no se puede separar
  del precio (las locales con "fregadero" son 2 y cuestan 6 veces más).
- H1 (voltaje) **sigue abierta**: las que declaran 220 V o 50 Hz venden 7 de 9 contra 48 de
  166 las que no lo mencionan, pero son pocas y se confunde con marca. Los títulos no
  alcanzan; hace falta la ficha técnica.
El baseline de términos ya muestra parte de lo mismo (en tostadoras pierden "delgada",
"larga"), pero no arma la necesidad ni las rivales.
**Qué decidimos:** la etapa divergente produce hipótesis que el MVP anterior no podía ver.
Siguiente: (1) refutar H3 con una captura de "lonchera eléctrica"; (2) que el grupo juzgue
las hipótesis (sostenida, no obvia, accionable) para tener los primeros juicios humanos;
(3) correr la misma skill con la API y comparar contra el baseline en test.

## 2026-11-05 — H3 refutada como oportunidad; divergente con API y planilla de juicios

**Qué probamos:** capturamos "lonchera eléctrica", "vianda eléctrica" y "lunchera eléctrica
calienta comida" (`data/divergente/h3_lonchera_electrica_2026-11-05.json`).
**Qué pasó:** la necesidad existe (unas 4.500 ventas visibles; 34 de 53 locales venden),
pero está repartida entre muchos vendedores locales a ~$48k (ninguna publicación pasa +500)
y lo internacional cuesta 1,4 a 2,3 veces más y casi no vende. Necesidad confirmada,
oportunidad de importación refutada: `ya_atendido`.
**Qué decidimos:** sumamos `harness/divergente.py` (LLM propone, el guardrail valida, un
reintento con los errores; costo y latencia en la traza) y una planilla ciega para que el
grupo juzgue LLM contra baseline (`data/evaluacion/`). Limitación conocida: los textos del
LLM y del baseline se distinguen por el estilo, así que la ceguera es parcial.
Idea anotada para después (de una conversación previa sobre serendipia computacional):
explorar a propósito la cola de búsquedas poco vendidas, no solo el top de Amazon.

## 2026-11-05 — Cambio de fuente: lo que se compra por Compra Internacional

**Qué probamos:** dejamos de partir del top de Amazon (encontraba productos ya atendidos o
caros) y partimos del voto con más fricción: lo que la gente compra por Compra
Internacional, pagando y esperando. Capturamos el listado filtrado por envío internacional
en Cocina, Hogar, Bazar y Organización (74 productos con +100 vendidos), y para 15 buscamos
equivalentes con stock local.
**Qué esperábamos:** encontrar demanda probada que hoy solo se atiende desde afuera.
**Qué pasó:** con un baseline de palabras salían 10 "oportunidades"; con la regla escrita por
el LLM, 8; con el LLM juzgando equivalencia publicación por publicación, 3. Revisando a mano,
las reglas confundían tamaños y gamas (tabla 25x15 contra 60x30; set básico de bowls contra
ensaladeras premium; mini aspiradora USB contra aspiradoras de 120 W). Quedan: afilador
rodante (2,3x más caro local), set de herméticos de acero (3,4x) y contenedor con colador
(locales al mismo precio que no venden: abierto).
**Qué decidimos:** esta es la hipótesis medible principal del TP: el juicio de equivalencia del
LLM contra reglas y baseline, con precisión/recall/F1 sobre etiquetas humanas. Fijamos 15
productos de test sin mirar. Pendiente: etiquetas del grupo y corrida con la API.

## 2026-11-05 — Residuos e información situada (opiniones de compradores)

**Qué probamos:** buscar lo que precio, espera, preferencia y demanda NO explican (residuos:
publicaciones caras que venden mucho), y leer para qué dicen usarlas los compradores
(`scripts/voces_ml.js`, conteos y citas en `data/voces/`).
**Qué esperábamos:** prácticas locales escondidas (asado, carlitos, negocios chicos).
**Qué pasó:** de tres hipótesis situadas, dos cayeron con las opiniones: la sopladora no se
compra para el asado (1 de 175; 25 de 175 hablan del auto) y el afilador tampoco (0 de 111).
La tercera ("el pan de acá no entra en ranura, por eso no vende la tostadora de Amazon") la
sostenían las opiniones del carlitero, pero cayó con datos de ventas: las de ranura baratas
venden +10.000. Quedó en pie un segundo mercado: el carlitero de calor superior, premium,
con 2-3 fabricantes locales, comprado para panes que no entran en ranura y por negocios chicos.
**Qué decidimos:** consolidar todo en `HALLAZGOS.md` como fichas de decisión. Lección de
proceso: las hipótesis situadas son baratas de generar y fáciles de creer; sin refutación
habríamos presentado dos falsas.

## 2026-11-05 — Costo puesto: de "hueco" a "cuánto deja"

**Qué probamos:** calcular cuánto cuesta traer cada candidata y cuánto deja vendida en
Mercado Libre (`harness/costo_puesto.py`), con precios de Alibaba, aranceles de ARCA,
logística consolidada y comisión de Mercado Libre; tres escenarios y lote de prueba.
**Qué esperábamos:** que las tres candidatas tuvieran margen.
**Qué pasó:** los herméticos son la más robusta (73% sobre costo a $25.000; aguanta hasta
con el proveedor caro si se vende al precio local). El afilador funciona si el FOB es de
USD 6 o menos y el arancel 18% (44% a $35.000); con FOB USD 12 y arancel 35% pierde. El
tostador abierto, que parecía el hallazgo más interesante, no: puesto acá cuesta ~$450.000
contra $242.000 del fabricante local. Ninguna conviene vendida al precio de Compra
Internacional: el que vende por ese canal usa la franquicia courier y un FOB más bajo.
**Qué decidimos:** las fichas de `HALLAZGOS.md` ahora dicen cuánto deja cada una y con qué
riesgo. Falta pedir cotización real a un proveedor y a un despachante.

## 2026-11-05 — Serendipia: pies + manos, LLM que abduce, embudo que mata

**Qué probamos.** Volver a la idea original (Cyberseren): descubrir desfasajes que solo
aparecen en información dispersa. Para 21 productos que venden mucho (2 por búsqueda,
partición dev/test fijada antes de leer) juntamos 2.647 opiniones y ~330 preguntas de
indecisos. El LLM lee (filtro de textos informativos de Timoshenko y Hauser, 2019) y propone
señales y oportunidades citando textos; el programa las pasa por un embudo: guardrail de
citas, C1 (las palabras aparecen en 3+ textos), C2 (puntaje de oportunidad de Ulwick), C3
(el ancla vende +500), C4 (en la búsqueda de lo propuesto no hay más de 2 equivalentes que
vendan +100) y C5 (30% sobre costo puesto al precio de lo que se vendió). Dos baselines sin
LLM pasan por el mismo embudo: la queja más frecuente (B1) y una regla de pedidos de
repuesto (B2, escrita después de leer dev: test la juzga).

**Qué esperábamos.** Que los repuestos (discos de afilador, adhesivos de estantes, picador
de minipimer) salieran como oportunidades claras.

**Qué pasó en dev.** Todas las propuestas pasaron C1-C3; C4 mató cuatro (espumador,
repuestos de minipimer, organizador con estructura, herméticos de calidad: ya los venden
varios). C5 mató los adhesivos: lo que se vende cuesta ~$6.000 y el costo fijo de envío de
Mercado Libre (~$2.500) se come todo. Los discos quedaron **condicionales**: 27% de margen,
sobreviven si el proveedor cotiza ≤ USD 3,21 (catálogo 2,60-3,30). B2 encontró lo mismo; B1,
nada. Tres correcciones en dev, antes de test: (1) el precio de referencia era la mediana de
*todas* las equivalentes y una importada sin ventas a $164.000 inflaba el margen de los
adhesivos a 699%: ahora es la mediana de las que vendieron; (2) los criterios de
equivalencia contaban afiladores completos y discos de motosierra como "discos de repuesto":
ahora miran el comienzo del título; (3) la unidad del disco no coincidía con la del
mercado. Lo aprendido se escribió en el skill y se congeló.

**Qué pasó en test (una sola corrida).** Sobrevivió una: **tabla de picar doble faz**. Dos
tablas de acero venden +1.000; 21 textos dicen que rayan y desafilan los cuchillos; de 18
equivalentes en Mercado Libre solo una vendió +100; margen base 79%. B1 y B2: cero. El
guardrail atajó una cita repetida (lonchera 24 V). Una muerte fue falsa: el criterio de
equivalencia contó cepillos a vapor para mascotas como repuestos de limpiadora.

**Qué decidimos.** Serendipia pasa a ser la vía principal (`make serendipia`,
`OPORTUNIDADES.md`). Pendientes: equivalencia de C4 con el LLM (como en cross-border) en
vez de palabras; correr `make serendipia-api` desde el workflow para tener el paso
divergente con el modelo real y su costo medido; pedir cotizaciones de la tabla doble faz y
de los discos.

**Declaraciones.** (1) El paso divergente de dev y test lo hizo Claude en el chat siguiendo
el skill: no había clave de API en el entorno. (2) Durante la recolección se imprimieron
algunas preguntas de test; el skill, los umbrales y el código no se tocaron después de
correr test. (3) El commit `4f59338` quedó con un mensaje generado por Copilot ("Update
print statement from 'Hello' to 'Goodbye'") cuando en realidad sube
`data/voces/opiniones_2026-11-05.json`; no se reescribe la historia para corregirlo.
(4) El archivo unido de voces se llama `data/voces/corpus_2026-11-05.json` para no pisar
`voces_2026-11-05.json`, que sigue siendo la evidencia de las fichas de `HALLAZGOS.md`.

## 2026-11-05 — Un solo programa, legible

**Qué pasó.** Serendipia se había armado al lado de los enfoques anteriores en vez de
iterarlos: el repo tenía varios programas con piezas duplicadas (proponer → validar →
reintentar, costo del LLM, chequeo de citas, equivalencias), documentos que se contradecían
y funciones cuyo propósito había que adivinar. **Qué decidimos.** Queda un solo programa,
un archivo por etapa: `voces` → `divergente` (LLM) → `baselines` → `embudo` (la lista de
chequeos, cada uno con su pregunta) → `chequeos` → `correr`, con los umbrales juntos en
`umbrales.py`. Se borró el código superado (agente ReAct, diagnóstico, lectura de títulos,
cross-border, sus skills, scripts y tests): está en el historial de git hasta el commit
`cad44ca`, y sus datos siguen en `data/`. `HALLAZGOS.md` se eliminó: sus fichas están en
las entradas anteriores. Los tests de piezas que siguen vivas (costo puesto, costo del LLM,
cita falsa persistente) se pasaron a `tests/test_embudo.py`. La reorganización no cambió
ningún resultado: las 44 propuestas de dev y test terminan igual. AGENTS suma la regla de
no duplicar programas ni parchear documentos. Se precisó el lenguaje: el voto con los pies
no es "lo que se compra" sino qué se elige frente a las alternativas y qué se deja pasar.
Eso dejó a la vista una brecha, ahora en las limitaciones del README: el LLM ve el producto
elegido y sus voces, pero no las alternativas descartadas de la búsqueda (entran en C4). El
skill decía que las veía; se corrigió esa línea, sin cambiar el procedimiento.
