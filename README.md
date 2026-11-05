# Faltante

**Qué hace:** encuentra productos que conviene importar para vender en Mercado Libre y que
nadie está trayendo. No parte de una lista de productos: parte de las **elecciones** de la
gente, que se ven de dos maneras.

- **Voto con los pies, lo que la gente hace:** frente a las opciones de una búsqueda, qué
  elige y qué deja pasar. Que algo se venda, solo, no dice nada; dice algo que se venda *en
  lugar de* otra cosa.
- **Voto con las manos, lo que la gente dice:** por qué eligió y qué le faltó. Opiniones de
  quienes compraron y preguntas de quienes todavía dudan.

Un LLM cruza las dos cosas y propone qué traer (por ejemplo, algo que los compradores piden y
nadie ofrece). Después el programa intenta tirar abajo cada propuesta con datos: ¿es una queja
aislada?, ¿ya lo vende alguien?, ¿deja plata? Solo recomienda lo que sobrevive.

A eso le decimos *serendipia computacional*: dar con oportunidades que nadie estaba buscando,
porque solo aparecen al juntar información dispersa.

TP de IA Agéntica, Maestría en Explotación de Datos (UBA), 2026.

## Un ejemplo

En la búsqueda "tabla de cortar acero inoxidable", las dos tablas más elegidas venden **más de
1.000 unidades cada una**. Sus compradores dicen por qué las eligieron y qué les falta: 21
textos repiten que las prefieren a la madera y al plástico por higiene, pero que **rayan y
desafilan los cuchillos**. El LLM propone traer una tabla **doble faz** (acero de un lado,
polipropileno del otro). El programa la intenta tirar abajo:

- ¿La queja es real o anecdótica? Aparece en 21 textos, la mayoría como queja. **Pasa.**
- ¿Alguien ya la vende? Hay 18 publicaciones parecidas y solo una vendió más de 100. **Pasa.**
- ¿Deja plata? Puesta en Argentina cuesta ~$10.700 y se vende a $32.800: 79% sobre el costo. **Pasa.**

Ni la queja más frecuente ni una regla que busca pedidos de "repuesto" la encuentran: hace
falta leer que la gente quiere dos cosas a la vez.

## Cómo funciona

```
voto con los pies ─────┐
(qué se elige y qué    │
 se deja pasar)        ├─► LLM propone ──► el programa intenta matar ──► OPORTUNIDADES.md
voto con las manos ────┘   (divergente)     (convergente: guardrail + C1..C5)
(opiniones, preguntas)
```

| Etapa | Qué hace | Quién |
|---|---|---|
| Datos | Los 1 o 2 productos más elegidos de cada búsqueda, con sus opiniones y las preguntas de los indecisos | Captura desde el navegador |
| Filtro | Todas las preguntas + las opiniones más informativas (como Timoshenko y Hauser, 2019) | Código |
| Divergente | Lee y propone señales (quejas, faltantes, deseos, usos raros) y qué traer, citando textos | **LLM** (`skills/leer_voces`) |
| Guardrail | Cada cita existe, es literal y viene de al menos 2 textos distintos; si no, se le devuelven los errores al LLM una vez | Código |
| C1 verificada | Las palabras de la señal aparecen en 3 o más textos (cuenta en *todos*, no solo los que leyó el LLM) | Código |
| C2 sub-atendida | Puntaje de oportunidad de Ulwick: importa y está mal resuelto | Código |
| C3 demanda | El producto donde aparece vende +500 | Código |
| C4 hueco | En la búsqueda de lo propuesto, 2 o menos equivalentes venden +100: o no se ofrece, o lo que se ofrece la gente lo deja pasar | Código + captura |
| C5 margen | 30% o más sobre costo puesto, al precio de lo que se vendió; si no llega, cuánto tendría que costar en origen | Código |

**Por qué un LLM:** lo valioso está en texto desordenado ("¿venden los discos de repuesto?",
"se raya pero la prefiero a la de madera"). Contar palabras da "filo", "precio", "hola".
Proponer *qué traer* requiere leer.

**Por qué no se lo cree:** el LLM no puede citar un texto que no existe, y el programa
recuenta todo por su cuenta. Cada propuesta que muere queda registrada con el motivo.

## Resultado

Detalle, con lo que murió y por qué, en [`OPORTUNIDADES.md`](OPORTUNIDADES.md).

| Oportunidad | ¿Traerla? | Por qué |
|---|---|---|
| Tabla de picar doble faz | **Probar** | Necesidad en 21 textos; casi nadie la vende con volumen; margen base 79% (pesimista 23%) |
| Disco de repuesto para afilador rodante | **Sí, si se consigue a USD 3,21 o menos** | Lo piden en las preguntas y los vendedores no lo tienen; a $17.416 deja 27%, un poco menos de lo pedido |

De 14 propuestas distintas del LLM, 12 murieron: la mayoría porque la necesidad es real pero ya la
atiende alguien (espumador de leche, repuestos de minipimer, filtros de aspiradora), y otras
porque no dejan plata (adhesivos de repuesto: lo barato no paga el envío de Mercado Libre).

## Cómo medimos si funciona

**Hipótesis:** con el mismo embudo, el LLM produce más oportunidades que sobreviven que dos
baselines sin LLM: **B1**, la queja más frecuente; **B2**, una regla que detecta pedidos de
repuesto. Los 21 productos se dividieron en dev (11, para iterar) y test (10, una sola
corrida) antes de leerlos.

| Oportunidades distintas que sobreviven o quedan condicionales | LLM | B1 | B2 |
|---|---|---|---|
| dev | 1 | 0 | 1 |
| test | **1** | 0 | 0 |

Con 21 productos esto muestra el mecanismo, no una diferencia estadística.

**Costo:** ~USD 0,01 por producto con Claude Haiku 4.5 (estimado; `CONSIGNA.md`). La
recolección en el navegador lleva ~1 minuto por producto.

## Correrlo

```bash
git clone https://github.com/codewithpatelo/faltante && cd faltante
python3 -m venv .venv && source .venv/bin/activate
make setup     # instala dependencias
make todo      # tests + el embudo en dev y test sobre los datos guardados (sin internet ni claves)
```

| Comando | Qué hace |
|---|---|
| `make serendipia` | El embudo en dev y test, LLM contra los dos baselines |
| `make serendipia-api` | Lo mismo con el paso del LLM hecho por la API (necesita `ANTHROPIC_API_KEY`) |

Sin compartir claves: cargar `ANTHROPIC_API_KEY` como secreto del repo y correr el workflow
**llm** desde la pestaña Actions; los resultados quedan en la rama `resultados-llm`.

## Datos

| Qué | Volumen | Dónde |
|---|---|---|
| Productos ancla (los 1 o 2 que más venden en cada búsqueda) | 21, en 12 búsquedas de Cocina, Hogar y Bazar | `data/voces/productos_2026-11-05.json` |
| Opiniones de compradores | 2.647 | Panel "Mostrar todas las opiniones" de cada publicación |
| Preguntas de indecisos con su respuesta | 334 | Página de preguntas de cada publicación |
| Búsquedas para C4 | 30 | `data/capturas/captura_ml_serendipia_*.json` (`scripts/captura_ml.js`) |
| Precios de origen | 9 productos | Catálogo de Alibaba, con el ID de cada publicación: `data/serendipia/fob_2026-11-05.json` |
| Aranceles, flete, comisiones y envío | — | Con fuente en `harness/costo_puesto.py` y `harness/umbrales.py` |

Opiniones y preguntas juntas: `data/voces/corpus_2026-11-05.json`. Se leen desde un
navegador con sesión iniciada porque la API de búsqueda de Mercado Libre está cerrada aun
con token válido.

## Mapa

Un archivo por etapa, en el orden en que corren:

| Archivo | Qué hace |
|---|---|
| `harness/voces.py` | Carga los productos y sus textos, les pone ID (`o12`, `p3`) y elige los que lee el LLM |
| `harness/divergente.py` | El paso del LLM: arma el prompt con `skills/leer_voces/SKILL.md`, propone y reintenta si el guardrail rechaza citas |
| `harness/baselines.py` | B1 y B2: proponer sin LLM, para comparar |
| `harness/embudo.py` | **La lista de chequeos**, en orden, cada uno con su pregunta; y cómo se recorre |
| `harness/chequeos.py` | Qué hace cada chequeo (guardrail, C1 a C5) |
| `harness/umbrales.py` | Todos los umbrales, con qué mide cada uno |
| `harness/costo_puesto.py` | Costo puesto en Argentina e ingreso neto vendiendo en Mercado Libre |
| `harness/correr.py` | Junta las propuestas, las pasa por el embudo y escribe el resultado |
| `scripts/captura_ml.js` | Captura de búsquedas desde el navegador (para C4) |
| `scripts/unir_voces.py` | Une productos, opiniones y preguntas en `data/voces/corpus_<fecha>.json` |
| `tests/test_embudo.py` | Lo que tiene que cumplir cada etapa |
| `data/serendipia/` | Propuestas del LLM, precios de proveedor y el recorrido de cada propuesta |
| `OPORTUNIDADES.md` | El resultado, para leer |
| `CONSIGNA.md` · `DECISIONES.md` | Requisitos del TP y dónde se cumplen · qué elegimos y por qué |
| `BITACORA.md` | Cómo llegamos acá, incluidos los enfoques descartados (su código está en el historial de git; sus datos, en el resto de `data/`) |

## Glosario

- **Voto con los pies:** lo que la gente hace: entre las opciones que tiene, qué elige y qué deja pasar.
- **Voto con las manos:** lo que la gente dice: por qué eligió y qué le faltó (opiniones y preguntas).
- **Divergente / convergente:** primero abrir hipótesis (LLM), después intentar refutarlas (programa).
- **Abducción:** proponer lo que haría que lo observado tenga sentido.
- **Puntaje de oportunidad (Ulwick):** importancia + (importancia − satisfacción); alto = importa y está mal resuelto.
- **Equivalente:** una publicación que es el mismo producto o un reemplazo directo.
- **Costo puesto:** precio en origen + flete + aranceles, con el producto en Argentina.
- **FOB:** precio del proveedor en el puerto de origen.
- **Guardrail:** regla en código que el LLM no puede saltear.

## Limitaciones

- El LLM ve el producto elegido y lo que dicen sus compradores e indecisos, pero no las
  alternativas que la gente dejó pasar en esa búsqueda: esas entran recién en C4.
- El paso del LLM en dev y test lo hizo Claude en el chat siguiendo el skill, porque no
  había clave de API en el entorno; `make serendipia-api` lo repite con el modelo.
- Algunas preguntas de test se vieron durante la recolección. Después de correr test no se
  cambió nada.
- C4 decide equivalencias por palabras del título y se equivoca: en test contó cepillos a
  vapor *para mascotas* como repuestos de limpiadora y mató una propuesta que no debía.
- Los costos usan precios de catálogo y tarifas publicadas, no cotizaciones reales.
- "+N vendidos" es un piso del contador de Mercado Libre, no las ventas exactas.
- El código que recolectó opiniones y preguntas se corrió en la consola del navegador y
  todavía no está guardado en `scripts/`.
