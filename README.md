# Faltante

**Qué hace:** le dice a un importador chico qué conviene traer para vender en Mercado Libre,
y por qué. Mira lo que la gente **ya compra** (no lo que dice que compraría), busca dónde
esa demanda no está bien atendida acá, y calcula cuánto deja traerlo.

Tiene dos vías: **cross-border** (lo que ya se compra desde afuera y no tiene equivalente
local) y **serendipia** (lo que dicen compradores e indecisos de productos que venden mucho,
leído por un LLM y filtrado por un embudo de cinco chequeos). Resultado de la segunda:
[`OPORTUNIDADES.md`](OPORTUNIDADES.md).

TP de IA Agéntica, Maestría en Explotación de Datos (UBA), 2026.

## La idea en un ejemplo

Un afilador de cuchillos rodante se vendió **más de 1.000 veces por Compra Internacional** a
$21.800. Esa gente pagó y esperó semanas para recibirlo: la demanda está probada. Acá, los
afiladores equivalentes con stock local cuestan entre $43.000 y $135.000. Traído en cantidad,
el afilador queda puesto en unos $11.400; vendido a $35.000 con stock local, deja 44% sobre
el costo. Eso es una oportunidad concreta, con números.

## Cómo funciona, paso a paso

| Paso | Qué hace | Quién lo hace |
|---|---|---|
| 1. Encontrar demanda probada | Junta productos que se venden mucho por Compra Internacional (+100 vendidos) | Código (captura desde el navegador) |
| 2. Buscar el equivalente local | Para cada uno, busca si alguien ya lo vende con stock en Argentina | **LLM**: decide si dos publicaciones son el mismo producto (tamaño, gama, tipo) |
| 3. Descartar lo que ya está atendido | Si hay equivalente local barato que vende, no hay hueco | Código, con reglas a la vista |
| 4. Entender el porqué | En los casos raros, lee para qué dicen usarlo los compradores | **LLM** + código que verifica las citas |
| 5. Calcular si conviene | Costo puesto (origen + flete + impuestos) contra precio de venta y comisión | Código |

**Por qué hace falta un LLM:** Mercado Libre mezcla en una misma búsqueda el producto,
sustitutos, accesorios y cosas que no tienen nada que ver. Decidir que una tabla de 25x15 cm
no es lo mismo que una de 60x30 cm requiere leer. Con reglas de palabras salen 10
"oportunidades" de 15; con el LLM leyendo publicación por publicación, 3. Las otras 7 eran
falsas.

**Por qué no se lo cree todo:** cada cosa que afirma el LLM tiene que citar una publicación
real con un fragmento literal de su título, y el código lo verifica. Y cada hipótesis se
intenta tirar abajo con datos antes de recomendarla.

## Serendipia: de lo que dice la gente a qué traer

Cruza el **voto con los pies** (qué se compra: ventas, precio, origen) con el **voto con las
manos** (opiniones de compradores y, sobre todo, preguntas de indecisos). El LLM diverge:
abduce necesidades no resueltas. El programa converge: intenta matar cada una.

| Etapa | Qué chequea | Quién |
|---|---|---|
| Filtro | Todas las preguntas + las opiniones más informativas (Timoshenko y Hauser, 2019) | Código |
| Divergente | Señales (quejas, faltantes, deseos, usos) y oportunidades, citando textos | **LLM** (`skills/leer_voces`) |
| Guardrail | Cada cita existe, es literal y hay al menos 2 textos distintos | Código |
| C1 verificada | Las palabras clave aparecen en 3+ textos (cuenta en *todos*, no solo los que leyó el LLM) | Código |
| C2 sub-atendida | Puntaje de oportunidad de Ulwick: importancia alta y satisfacción baja | Código |
| C3 demanda | El producto donde aparece vende +500 | Código |
| C4 hueco | En la búsqueda de lo propuesto, 2 o menos equivalentes venden +100 | Código + captura |
| C5 margen | 30% o más sobre costo puesto, al precio de lo que se vendió; si no, el FOB máximo | Código |

Ejemplo de lo que sale: dos tablas de acero venden +1.000 cada una; los compradores dicen que
las eligen por higiene pero que **rayan y desafilan los cuchillos**. El LLM propone una tabla
**doble faz** (acero de un lado, polipropileno del otro). En Mercado Libre hay 18 parecidas y
solo una vendió +100; puesta en Argentina cuesta ~$10.700 y se vende a $32.800. Una regla que
busca "repuesto" o la queja más frecuente no la encuentran.

## Qué encontramos

Detalle en [`HALLAZGOS.md`](HALLAZGOS.md) (cross-border, una ficha por producto) y
[`OPORTUNIDADES.md`](OPORTUNIDADES.md) (serendipia: lo que sobrevivió y lo que murió, con motivo).

| Producto | ¿Traerlo? | Por qué |
|---|---|---|
| Tabla de picar doble faz (serendipia) | **Probar** | Necesidad leída en 21 textos; casi nadie la vende con volumen; margen base 79% |
| Disco de repuesto para afilador rodante (serendipia) | **Sí, si se consigue a USD 3,21 o menos** | Lo piden en las preguntas y nadie lo tiene; a $17.416 el margen base es 27% |

| Set de 5 herméticos de acero | **Sí** | +5.000 por Compra Internacional; puesto en ~$5.700, a $25.000 deja 73% |
| Afilador rodante | **Sí, si se consigue a USD 6 o menos** | +1.000 por Compra Internacional; a $35.000 deja 44% |
| Tostador abierto (carlitero) | No | Parece un hueco, pero importado queda en ~$450.000 contra $242.000 del fabricante local |
| Olla de cocción lenta (Crock-Pot) | No | La gente compra esa función dentro de ollas multifunción |
| Lonchera eléctrica | No | La necesidad existe pero ya la atienden muchos vendedores locales |

**Tres cosas que aprendimos:**
1. Partir del top de Amazon no sirve: casi todo es más caro o ya se vende acá. Partir de lo
   que se compra por Compra Internacional sí.
2. Lo que viene de afuera **sin stock local casi no se compra**: en 387 publicaciones
   internacionales del top de Amazon, ninguna mostraba ventas. La espera pesa. Por eso la
   oportunidad es traer con stock local, no competir por Compra Internacional.
3. Las explicaciones "culturales" son fáciles de inventar: "la sopladora se compra para el
   asado" (1 de 175 opiniones lo dice) y "el afilador es para el asado" (0 de 111) eran falsas.

## Correrlo

```bash
git clone https://github.com/codewithpatelo/faltante && cd faltante
python3 -m venv .venv && source .venv/bin/activate
make setup     # instala dependencias
make todo      # 38 tests + todo el análisis sobre los datos guardados (no necesita internet ni claves)
```

Pasos sueltos:

| Comando | Qué hace |
|---|---|
| `make serendipia` | Embudo de serendipia en dev y test, LLM contra dos baselines |
| `make serendipia-api` | Lo mismo con el paso divergente hecho por la API (necesita `ANTHROPIC_API_KEY`) |
| `make cross-border` | Pasos 1 a 3: productos internacionales que venden contra equivalentes locales |
| `make costos` | Paso 5: costo puesto y margen de cada candidata |
| `make diagnostico` | Por qué no se venden acá los productos del top de Amazon (primer enfoque) |
| `make divergente` | Hipótesis leídas de los votos, con sus citas verificadas |
| `make equivalencia` | Precisión del LLM contra reglas, con las etiquetas del grupo |
| `make divergente-llm` | La lectura con el modelo de verdad (necesita `ANTHROPIC_API_KEY`) |

## Cómo medimos si funciona

**Hipótesis:** para decidir si una publicación local es equivalente a un producto
importado, el LLM acierta más que una regla de palabras. Se mide con precisión, recall y F1
contra etiquetas humanas (`data/evaluacion/planilla_equivalencia.csv`). Hay 15 productos de
prueba separados que no se miraron mientras se armaba el sistema.

**Hipótesis de serendipia:** con el mismo embudo, el LLM produce más oportunidades que
sobreviven que dos baselines sin LLM (la queja más frecuente; una regla que detecta pedidos
de repuesto). Resultado: en test, LLM 1 sobreviviente, baselines 0; en dev, LLM y regla
empatan con 1 condicional. Son 21 productos: muestra el mecanismo, no una diferencia
estadística. Tabla completa en `OPORTUNIDADES.md`.

**Costo del sistema:** ~USD 0,006 por producto analizado con Claude Haiku 4.5. Detalle en `CONSIGNA.md`.

## De dónde salen los datos

- **Mercado Libre**, leído desde el navegador con sesión iniciada (`scripts/captura_ml.js`):
  título, precio, "+N vendidos" y si es Compra Internacional. La API de búsqueda está cerrada,
  incluso con token válido (lo probamos: `data/prueba_datos/`).
- **Opiniones de compradores**, también desde el navegador (`scripts/voces_ml.js`).
- **Precios de origen** (Alibaba), **aranceles** (ARCA), **flete** y **comisiones**: fuentes en
  `harness/costo_puesto.py`.

Para refrescar los datos: abrí `https://listado.mercadolibre.com.ar/termo` con tu sesión,
pegá `scripts/captura_ml.js` en la consola (F12) y seguí las instrucciones del archivo.

## Mapa del repo

| Carpeta / archivo | Qué hay |
|---|---|
| `OPORTUNIDADES.md` | Resultado de serendipia: sobrevivientes, condicionales y muertes con motivo |
| `HALLAZGOS.md` | Resultado de cross-border: una ficha por producto |
| `BITACORA.md` | Qué probamos en cada sesión, qué salió mal y qué decidimos (para la exposición) |
| `CONSIGNA.md` | Cada requisito del TP, dónde se cumple y qué falta |
| `harness/` | El sistema: chequeos, emparejamiento, lectura de votos, costos, guardrails |
| `skills/` | Instrucciones que sigue el LLM en cada tarea (`SKILL.md`) |
| `scripts/` | Captura desde el navegador y scripts de evaluación |
| `data/` | Todo lo capturado y los resultados, con fecha |
| `tests/` | 38 tests: guardrails, chequeos, citas, reintentos, costos, embudo |

## Glosario

- **Voto con los pies:** lo que la gente compra de verdad, contra lo que dice que compraría.
- **Compra Internacional:** publicaciones de Mercado Libre que se envían desde afuera; el
  comprador espera semanas.
- **Equivalente:** una publicación local que es el mismo producto o un reemplazo directo
  (mismo tipo, tamaño y gama).
- **Costo puesto:** lo que cuesta tener el producto en un depósito en Argentina: precio en
  origen + flete + aranceles.
- **Abducción:** proponer la explicación (o el producto) que haría que lo observado tenga sentido.
- **Puntaje de oportunidad (Ulwick):** importancia + (importancia − satisfacción); alto = importa y está mal resuelto.
- **Guardrail:** regla en código que el LLM no puede saltear (por ejemplo, no puede citar una
  publicación que no existe).

## Limitaciones

- Miramos la primera página de cada búsqueda y unas pocas categorías (Cocina, Hogar, Bazar).
- "+N vendidos" es un piso del contador de Mercado Libre, no las ventas exactas.
- Los costos usan precios y tarifas publicados, no una cotización real de proveedor y despachante.
- Hasta que el grupo etiquete, el juicio del LLM no está validado por personas.
- En serendipia, el paso divergente de dev y test lo hizo Claude en el chat siguiendo el skill
  (no había clave de API en el entorno); `make serendipia-api` lo repite con la API.
- La equivalencia de C4 es por palabras del título y se equivoca: en test contó cepillos a
  vapor *para mascotas* como repuestos de limpiadora y mató una propuesta que no debía. El
  emparejamiento con LLM de cross-border es el arreglo pendiente.
- C4 necesita capturar cada búsqueda desde el navegador (la API de Mercado Libre está cerrada).
