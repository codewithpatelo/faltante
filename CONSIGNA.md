# Cumplimiento de la consigna (05/11/2026)

Cada requisito de la consigna oficial, dónde se verifica en el repo y qué falta.
✅ cumplido · 🟡 parcial · ❌ falta.

## El caso

**Usuario:** importadores y vendedores chicos de Mercado Libre que deciden qué traer.
**Tarea:** cruzar lo que la gente hace (voto con los pies: entre las opciones de una búsqueda,
qué elige y qué deja pasar) con lo que dice (voto con las manos: opiniones de compradores y
preguntas de indecisos), proponer qué traer, y tratar de refutarlo con datos antes de
recomendarlo.

**Hipótesis:** con el mismo embudo convergente en código (guardrail de citas, C1
el dolor existe, C3 demanda, C4 hueco local, C5 la eligen si se ofrece, C6 margen), el
LLM produce **más oportunidades distintas que sobreviven** que dos baselines sin LLM: B1, la queja más
frecuente; B2, una regla que detecta pedidos de repuesto. Partición fija por producto,
decidida antes de leer las voces (`data/voces/productos_2026-11-05.json`: 11 dev, 10 test).

| Oportunidades distintas que sobreviven o quedan condicionales | LLM | B1 | B2 |
|---|---|---|---|
| dev | 1 | 0 | 1 |
| test | 0 | 0 | 0 |

**Veredicto hoy: no se puede evaluar.** Con 21 productos nada sobrevive en test, ni con LLM ni
sin él; hacen falta cientos o miles. Además, las hipótesis del LLM fueron triviales
(repuestos, accesorios), porque leyó cada producto por separado. Test se corrió dos veces: la
segunda, después de agregar C5. Límites declarados: el paso del LLM en dev y test lo hizo Claude en el chat con el skill congelado
(sin clave de API en el entorno); algunas preguntas de test se vieron durante la
recolección; B2 se escribió después de leer dev.

## Requisitos

| Requisito | Dónde se ve | Estado |
|---|---|---|
| Utilidad real | Este archivo; `OPORTUNIDADES.md` (cada oportunidad con el experimento siguiente) | 🟡 falta mostrárselo a 1 o 2 importadores |
| LLM en el núcleo | `harness/divergente.py`, `skills/leer_voces/` | 🟡 corrido en el chat; la corrida con la API es el workflow `llm` |
| Hipótesis vs baseline, partición fija dev/test | Arriba; `harness/baselines.py`, `harness/correr.py`; `data/serendipia/embudo_*.json` | ✅ corrida en test; 🟡 falta el juicio humano de las propuestas |
| Datos verificados | Sección "Datos" | ✅ |
| Economía (costo, latencia, modelo) | Sección "Costos"; `harness/divergente.py::costo`; economía del usuario: C5 y `harness/costo_puesto.py` | 🟡 costo del sistema estimado; el real sale del workflow |
| Git con trabajo distribuido | `git log` | ❌ hoy todos los commits son de Patricio: ver "Reparto" |
| Antecedentes (mercado y literatura) | Sección "Antecedentes" | 🟡 versión breve |
| ≥ 2 áreas en profundidad | Sección "Áreas" | 🟡 dos fuertes |
| Repo con README, Makefile, skills y reglas | `README.md`, `Makefile`, `skills/`, `AGENTS.md`, `Dockerfile` | ✅ `make todo` corre desde un clon limpio |
| Relato del desarrollo | `BITACORA.md` | ✅ incluye los enfoques descartados y por qué |

## Cómo correr el LLM sin compartir claves

1. En GitHub: Settings → Secrets and variables → Actions → *New repository secret*:
   `DEEPSEEK_API_KEY` (ya está cargada).
2. Pestaña Actions → workflow **llm** → *Run workflow*.
3. Según la tarea: `serendipia` (los dos pasos del LLM con DeepSeek Flash, guardrail con
   reintento y embudo), `explorar` (compara las 25 variantes del prompt) u `optimizar`. Deja
   propuestas, costo, latencia y traza como archivo de la corrida (`gh run download <id>`).

Alternativa local: `DEEPSEEK_API_KEY=... make serendipia-api`.

## Datos

| Fuente | Volumen | Actualización | Licencia / términos |
|---|---|---|---|
| Opiniones y preguntas de 21 publicaciones de Mercado Libre, leídas desde un navegador con sesión | 2.647 opiniones, 334 preguntas con respuesta | 05/11/2026, a demanda | visibles públicamente; uso académico, escala chica; no se guardan nombres de usuarios |
| Listado público de Mercado Libre (primera página por búsqueda), `scripts/captura_ml.js` | 30 búsquedas para C4 | 05/11/2026, a demanda | ídem |
| Precios de origen (catálogo Alibaba) | 9 productos, con ID de publicación | 05/11/2026 | públicos; referencia, no cotización |
| API de Mercado Libre | no usable: búsqueda 403 con y sin token | — | — |

## Costos (DeepSeek Flash: USD 0,30 / 1,20 por millón de tokens de entrada / salida en hora pico; la mitad fuera de pico)

- Por producto: ~4.000 tokens de entrada (skill + ~45 textos filtrados) y ~1.200 de salida
  ≈ **USD 0,003**; 1.000 productos ≈ USD 3 (el doble si todos reintentan).
- Se elige DeepSeek Flash por costo: la escala que hace falta (cientos o miles de productos)
  cuesta centavos. Si el juicio humano muestra que no alcanza, se compara con DeepSeek V4 Pro
  (USD 1,32 / 3,96).
- Recolección: gratis, ~1 minuto por producto en el navegador. C4 y C5: ~20 s por búsqueda.
- El costo y la latencia reales quedan en `divergente_<particion>_api.json` al correr el workflow.

## Áreas en profundidad

1. **Orquestación y guardrails:** divergente (LLM) → guardrail en código que verifica cada
   cita → reintento con los errores → convergente: seis supuestos críticos, cada uno con el dato
   que lo refuta, y cada descarte con su motivo (`harness/embudo.py`: la lista de chequeos; `harness/chequeos.py`: qué hace cada uno).
2. **Evaluación:** partición fija por producto, dos baselines sin LLM por el mismo embudo,
   una sola corrida en test, umbrales a la vista; pendiente el juicio humano a ciegas de las
   propuestas (¿no obvia? ¿accionable?).
3. **Prompts y skills:** espacio de 25 variantes del prompt del paso B con decisiones tomadas de
   la literatura, comparadas sobre los mismos datos, y optimización de la mejor al estilo GEPA
   (`harness/espacio_de_prompts.py`, `harness/explorar_prompts.py`, `harness/optimizar_prompt.py`).

## Antecedentes (versión breve)

**Mercado.** *Nubimetrics* (Argentina) clasifica categorías de Mercado Libre por crecimiento
de ventas y saturación de competencia. *Jungle Scout* (Amazon) da un Opportunity Score con
demanda, competencia y calidad de los listados. Las dos miden **cuánto** se vende y
**cuánta** competencia hay. Faltante lee **qué** necesidad queda sin resolver y propone
**qué traer**, con citas verificables: es complementario.

**Literatura.** Generación de hipótesis: MOOSE-Chem (Yang et al., ICLR 2025: antecedente más
inspiraciones de fuentes no relacionadas, combinadas y refinadas); Si, Yang y Hashimoto (2024:
las ideas de LLM resultan más novedosas que las de expertos, pero ~5% de 4.000 no se repiten y
el ranking automático coincide poco con humanos); encuesta de abducción en LLM (2026: generar
hipótesis que compiten, después seleccionar). Optimización de prompts: GEPA (Agrawal et al.,
ICLR 2026: reflexión en lenguaje natural sobre los fallos; supera a MIPROv2 y a RL con muchas
menos corridas). Necesidades del usuario: Timoshenko y Hauser (2019, *Marketing Science*): filtrar el contenido
generado por usuarios informativo antes de extraer necesidades; su versión con LLM (2025)
encontró todas las necesidades que hallaron los analistas. Ulwick (*Outcome-Driven
Innovation*): puntaje de oportunidad = importancia + máx(importancia − satisfacción, 0).
Zhou et al. (2024, *Hypothesis Generation with Large Language Models*, arXiv 2404.04326): un
LLM genera hipótesis desde datos y las refina contra evidencia. Base conceptual: preferencia
revelada (lo que se elige frente a las alternativas, no lo que se declara).

## Reparto propuesto (para que el git refleje a todos)

| Quién | Qué | Entregable verificable |
|---|---|---|
| Dario | Evaluación: baseline humano (proponer con los mismos datos) y juicio a ciegas de todas las propuestas mezcladas; etiquetas de equivalencia para C4 | planilla en `data/evaluacion/`, resultado acá |
| Nilo | Datos: voces de más productos ancla (otras categorías) y guardar en `scripts/` el código de recolección | `data/voces/`, entrada en BITACORA |
| Victoria | Antecedentes completos y presentación | sección ampliada acá, slides |
| Patricio | Programa, corrida con la API y cotizaciones de las que pasaron | `harness/`, workflow `llm`, `OPORTUNIDADES.md` |
