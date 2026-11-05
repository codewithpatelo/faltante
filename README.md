# Faltante

**Qué hace:** le dice a un importador chico qué conviene traer para vender en Mercado Libre,
y por qué. Lee lo que la gente **compra** (voto con los pies) y lo que **dice** antes y
después de comprar (voto con las manos), propone oportunidades con un LLM y después intenta
matarlas con datos. Solo recomienda lo que sobrevive.

TP de IA Agéntica, Maestría en Explotación de Datos (UBA), 2026.

## La idea en un ejemplo

Dos tablas de picar de acero venden **más de 1.000 unidades cada una**. En sus opiniones, 21
textos repiten lo mismo: las eligen por higiene, pero **rayan y desafilan los cuchillos**.
El LLM propone una tabla **doble faz** (acero de un lado, polipropileno del otro). El
programa la intenta tirar abajo:

- ¿La queja es real o anecdótica? Aparece en 21 textos, la mayoría como queja. **Pasa.**
- ¿Alguien ya la vende? Hay 18 publicaciones parecidas y solo una vendió más de 100. **Pasa.**
- ¿Deja plata? Puesta en Argentina cuesta ~$10.700 y se vende a $32.800: 79% sobre el costo. **Pasa.**

Ni la queja más frecuente ni una regla que busca pedidos de "repuesto" la encuentran: hace
falta leer que la gente quiere dos cosas a la vez.

## Cómo funciona

```
pies + manos ──► LLM propone (divergente) ──► el programa intenta matar (convergente) ──► OPORTUNIDADES.md
```

| Etapa | Qué hace | Quién |
|---|---|---|
| Datos | Productos que venden mucho, con sus opiniones y las preguntas de los indecisos | Captura desde el navegador |
| Filtro | Todas las preguntas + las opiniones más informativas (como Timoshenko y Hauser, 2019) | Código |
| Divergente | Lee y propone señales (quejas, faltantes, deseos, usos raros) y qué traer, citando textos | **LLM** (`skills/leer_voces`) |
| Guardrail | Cada cita existe, es literal y viene de al menos 2 textos distintos | Código |
| C1 verificada | Las palabras de la señal aparecen en 3 o más textos (cuenta en *todos*, no solo los que leyó el LLM) | Código |
| C2 sub-atendida | Puntaje de oportunidad de Ulwick: importa y está mal resuelto | Código |
| C3 demanda | El producto donde aparece vende +500 | Código |
| C4 hueco | En la búsqueda de lo propuesto, 2 o menos equivalentes venden +100 | Código + captura |
| C5 margen | 30% o más sobre costo puesto, al precio de lo que se vendió; si no llega, cuánto tendría que costar en origen | Código |

**Por qué un LLM:** lo valioso está en texto desordenado ("¿venden los discos de repuesto?",
"se raya pero la prefiero a la de madera"). Contar palabras da "filo", "precio", "hola".
Proponer *qué traer* requiere leer.

**Por qué no se lo cree:** el LLM no puede citar un texto que no existe, y el programa
recuenta todo por su cuenta. Cada propuesta que muere queda registrada con el motivo.

## Qué encontramos

Detalle en [`OPORTUNIDADES.md`](OPORTUNIDADES.md).

| Oportunidad | ¿Traerla? | Por qué |
|---|---|---|
| Tabla de picar doble faz | **Probar** | Necesidad en 21 textos; casi nadie la vende con volumen; margen base 79% (pesimista 23%) |
| Disco de repuesto para afilador rodante | **Sí, si se consigue a USD 3,21 o menos** | Lo piden en las preguntas y los vendedores no lo tienen; a $17.416 deja 27%, un poco menos de lo pedido |
| Espumador de leche, repuestos de minipimer, filtros de aspiradora | No | La necesidad es real pero ya la venden varios (murieron en C4) |
| Adhesivos de repuesto para estantes de ducha | No | Se venden a ~$6.000 y el costo fijo de envío de Mercado Libre se come el margen (C5) |

**Lo que aprendimos:**
1. Las preguntas de los indecisos valen más que las opiniones: ahí aparece lo que falta
   ("¿venden el filtro solo?").
2. Que una necesidad sea real no alcanza: la mayoría muere porque ya la atiende alguien.
3. En Mercado Libre lo barato no paga el envío: un consumible de menos de ~$10.000 tiene que
   ir en pack o junto al producto.
4. Las explicaciones fáciles hay que contarlas: "la sopladora se compra para el asado" lo
   decía 1 de 175 opiniones.

### La otra vía: cross-border

Antes de serendipia probamos partir de lo que se compra por **Compra Internacional** (la
gente paga y espera semanas: demanda probada) y buscar si tiene equivalente con stock local.
Encontró dos candidatas (set de herméticos de acero y afilador rodante), dejó una abierta y
descartó cinco. Fichas en [`HALLAZGOS.md`](HALLAZGOS.md); se corre con `make cross-border` y `make costos`.

## Cómo medimos si funciona

**Hipótesis:** con el mismo embudo, el LLM produce más oportunidades que sobreviven que dos
baselines sin LLM: **B1**, la queja más frecuente; **B2**, una regla que detecta pedidos de
repuesto. Los 21 productos se dividieron en dev (11, para iterar) y test (10, una sola
corrida) antes de leerlos.

| | LLM | B1 queja más frecuente | B2 regla de repuestos |
|---|---|---|---|
| dev: oportunidades distintas que sobreviven o quedan condicionales | 1 | 0 | 1 |
| test: ídem | **1** | 0 | 0 |

Con 21 productos esto muestra el mecanismo, no una diferencia estadística.

**Costo:** ~USD 0,01 por producto con Claude Haiku 4.5 (estimado; detalle en `CONSIGNA.md`).
La recolección en el navegador lleva ~1 minuto por producto.

## Correrlo

```bash
git clone https://github.com/codewithpatelo/faltante && cd faltante
python3 -m venv .venv && source .venv/bin/activate
make setup     # instala dependencias
make todo      # 38 tests + todo el análisis sobre los datos guardados (no necesita internet ni claves)
```

| Comando | Qué hace |
|---|---|
| `make serendipia` | El embudo en dev y test, LLM contra los dos baselines |
| `make serendipia-api` | Lo mismo con el paso divergente hecho por la API (necesita `ANTHROPIC_API_KEY`) |
| `make cross-border` / `make costos` | La vía cross-border y el costo puesto de sus candidatas |
| `make equivalencia` | Precisión del LLM contra reglas para decidir si dos publicaciones son lo mismo |
| `make diagnostico` / `make divergente` | Primeros enfoques (top de Amazon, lectura de títulos) |

Las partes con LLM también corren desde GitHub sin compartir claves: workflow **llm** en la
pestaña Actions (ver `CONSIGNA.md`).

## De dónde salen los datos

| Qué | Volumen | Cómo |
|---|---|---|
| Productos ancla (los 1 o 2 que más venden en cada búsqueda) | 21, en 12 búsquedas de Cocina, Hogar y Bazar | `data/voces/productos_2026-11-05.json` |
| Opiniones de compradores | 2.647 | Panel "Mostrar todas las opiniones" de cada publicación, leído desde el navegador |
| Preguntas de indecisos con su respuesta | 334 | Página de preguntas de cada publicación, desde el navegador |
| Búsquedas para C4 | 30 | `scripts/captura_ml.js` → `data/capturas/captura_ml_serendipia_*.json` |
| Precios de origen | 9 productos | Catálogo de Alibaba, con el ID de cada publicación: `data/serendipia/fob_2026-11-05.json` |
| Aranceles, flete, comisiones y envío de Mercado Libre | — | Con fuente en `harness/costo_puesto.py` y `harness/serendipia.py` |

Todo junto en `data/voces/corpus_2026-11-05.json`. La API de búsqueda de Mercado Libre está
cerrada aun con token válido (probado: `data/prueba_datos/`), por eso se lee desde un
navegador con sesión iniciada.

## Mapa del repo

| Carpeta / archivo | Qué hay |
|---|---|
| `OPORTUNIDADES.md` | El resultado: qué sobrevivió, qué murió y por qué, LLM contra baselines |
| `HALLAZGOS.md` | Resultado de la vía cross-border |
| `BITACORA.md` | Qué probamos en cada sesión, qué salió mal y qué decidimos |
| `CONSIGNA.md` | Cada requisito del TP, dónde se cumple y qué falta |
| `harness/serendipia.py` | Filtro, guardrail, chequeos C1 a C5 y el paso divergente con la API |
| `scripts/serendipia_run.py` | Corre el embudo para el LLM y los baselines |
| `skills/` | Instrucciones que sigue el LLM (`leer_voces` para serendipia) |
| `data/serendipia/` | Lo que propuso el LLM, el recorrido de cada propuesta por el embudo, precios de origen |
| `tests/` | 38 tests: guardrails, citas, reintentos, chequeos, costos, embudo |

## Glosario

- **Voto con los pies / con las manos:** lo que la gente compra / lo que dice (opiniones y preguntas).
- **Divergente / convergente:** primero abrir hipótesis (LLM), después intentar refutarlas (programa).
- **Abducción:** proponer lo que haría que lo observado tenga sentido.
- **Puntaje de oportunidad (Ulwick):** importancia + (importancia − satisfacción); alto = importa y está mal resuelto.
- **Equivalente:** una publicación que es el mismo producto o un reemplazo directo.
- **Costo puesto:** precio en origen + flete + aranceles, con el producto en Argentina.
- **FOB:** precio del proveedor en el puerto de origen.
- **Guardrail:** regla en código que el LLM no puede saltear.

## Limitaciones

- El paso divergente de dev y test lo hizo Claude en el chat siguiendo el skill, porque no
  había clave de API en el entorno; `make serendipia-api` lo repite con el modelo.
- Algunas preguntas de test se vieron durante la recolección. Después de correr test no se
  cambió nada.
- C4 decide equivalencias por palabras del título y se equivoca: en test contó cepillos a
  vapor *para mascotas* como repuestos de limpiadora y mató una propuesta que no debía.
  Pendiente: que lo decida el LLM, como en cross-border.
- Los costos usan precios de catálogo y tarifas publicadas, no cotizaciones reales.
- "+N vendidos" es un piso del contador de Mercado Libre, no las ventas exactas.
- El código que recolectó opiniones y preguntas se corrió en la consola del navegador y
  todavía no está guardado en `scripts/`.
