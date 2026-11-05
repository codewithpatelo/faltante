# Cumplimiento de la consigna (auditoría al 05/11/2026)

Cada requisito de la consigna oficial, dónde se verifica en el repo y qué falta.
✅ cumplido · 🟡 parcial · ❌ falta.

## El caso en una línea

**Usuario:** importadores y vendedores chicos de Mercado Libre que deciden qué traer.
**Tarea:** leer en Mercado Libre cómo "vota con los pies" la gente (qué compra y qué deja
pasar en cada búsqueda), proponer hipótesis de necesidad u oportunidad, y tratar de
refutarlas con datos antes de recomendar.

**Hipótesis medible de serendipia (la vía principal desde el 05/11):** sobre productos que
venden mucho, cruzar pies (ventas, precio) y manos (opiniones y preguntas) con un LLM que
abduce oportunidades, y pasarlas por el mismo embudo convergente en código (guardrail de
citas, C1 verificada, C2 Ulwick, C3 demanda, C4 hueco local, C5 margen), produce **más
oportunidades distintas que sobreviven** que dos baselines sin LLM: B1 queja más frecuente y
B2 regla de pedidos de repuesto. Partición fija por producto (`data/voces/productos_2026-11-05.json`:
11 dev, 10 test). Resultado (`make serendipia`, `OPORTUNIDADES.md`):

| | LLM | B1 | B2 |
|---|---|---|---|
| dev: sobreviven + condicionales distintas | 1 | 0 | 1 |
| test: sobreviven + condicionales distintas | **1** | 0 | 0 |

Con 21 productos no hay potencia estadística; lo que se muestra es el mecanismo y el tipo de
hallazgo que solo aparece leyendo (una combinación de dos deseos, no un repuesto). Límites:
el paso divergente de dev/test lo hizo Claude en el chat con el skill congelado (sin clave de
API en el entorno; `make serendipia-api` lo repite con Haiku); algunas preguntas de test se
vieron durante la recolección.

**Hipótesis medible de emparejamiento (vía cross-border):** para decidir si una publicación local es
equivalente a un producto que se vende por Compra Internacional, el juicio del LLM
publicación por publicación tiene mayor F1 que (a) una regla de palabras escrita por el LLM
y (b) un baseline sin LLM (dos palabras del título), medido contra etiquetas humanas
(`data/evaluacion/planilla_equivalencia.csv`, `make equivalencia`). En dev ya cambia el
resultado: 10 oportunidades con el baseline, 8 con la regla, 3 con el juicio del LLM.
Test: 15 productos fijados sin mirar (`data/cross_border/particion.json`).

**Hipótesis medible secundaria (etapa divergente):** sobre las 11 búsquedas de **test**, las hipótesis que
produce el LLM con la skill `leer_votos` obtienen mayor puntaje humano (promedio de
*sostenida*, *no obvia* y *accionable*, escala 1 a 3) que el **baseline** sin LLM
(log-odds de términos del título en lo que vende contra lo que no), sin perder
verificabilidad: 100% de las hipótesis aceptadas pasan el guardrail de citas.
Métrica secundaria: proporción de hipótesis que sobreviven a la refutación.

## Requisitos

| Requisito | Dónde se ve | Estado |
|---|---|---|
| Utilidad real | Este archivo (usuario y tarea); `README.md` | 🟡 falta validar con 1 o 2 importadores reales |
| LLM en el núcleo | `harness/serendipia.py`, `skills/leer_voces/`, `harness/divergente.py`, `skills/leer_votos/` | 🟡 código y tests listos; la corrida con modelo es la del workflow `llm` (ver abajo) |
| Hipótesis vs baseline, partición fija dev/test | Arriba; `data/cross_border/particion.json`, `data/divergente/particion.json`; baselines en `scripts/cross_border_run.py` y `harness/votos.py` | 🟡 definidas y congeladas; faltan las etiquetas humanas y la corrida en test |
| Datos verificados | Sección "Datos" abajo; `data/capturas/` | ✅ |
| Economía (costo, latencia, modelo) | Sección "Costos" abajo; `harness/divergente.py::costo`; economía del usuario: `harness/costo_puesto.py` | 🟡 costo del sistema estimado (latencia real en el workflow); costo puesto y margen de cada oportunidad calculados con supuestos y fuentes |
| Git con trabajo distribuido | `git log` | ❌ hoy todos los commits son de Patricio: ver "Reparto" |
| Antecedentes (mercado y literatura) | Sección "Antecedentes" abajo | 🟡 versión breve |
| ≥ 2 áreas en profundidad | Sección "Áreas" abajo | 🟡 dos fuertes, una a completar |
| Repo con README, Makefile, skills y reglas | `README.md`, `Makefile`, `skills/`, `AGENTS.md`, `Dockerfile` | ✅ `make todo` corre desde un clon limpio |
| Relato del desarrollo | `BITACORA.md` | ✅ incluye lo que no funcionó y las decisiones de rumbo |

## Cómo correr las partes con LLM sin compartir claves

1. En GitHub: Settings → Secrets and variables → Actions → *New repository secret*:
   `ANTHROPIC_API_KEY`.
2. Pestaña Actions → workflow **llm** → *Run workflow*.
3. Corre los tests, la etapa divergente sobre test y el LLM juez, y deja los resultados en
   la rama `resultados-llm` (hipótesis validadas, costo, latencia y traza de reintentos).

Alternativa local: `ANTHROPIC_API_KEY=... make divergente-llm && python scripts/juez_llm.py`.

## Datos

| Fuente | Volumen | Actualización | Licencia / términos |
|---|---|---|---|
| Listado público de Mercado Libre (primera página por búsqueda), capturado con `scripts/captura_ml.js` desde un navegador con sesión | 23 búsquedas, 1.372 publicaciones (29/10) y 1.336 (05/11); +3 búsquedas para H3 | a demanda; dos fotos con una semana de diferencia dan las mismas 23 conclusiones | datos visibles públicamente; uso académico, escala chica y manual; no se guardan datos de usuarios ni de vendedores |
| Amazon Best Sellers, Cocina | 30 productos (23 con marca) | 29/10/2026 | público; solo título y marca |
| API de Mercado Libre | no usable: búsqueda 403 con y sin token (`data/prueba_datos/`) | — | — |

## Costos (estimados, Haiku 4.5: USD 1 / 5 por millón de tokens de entrada / salida)

- Entrada por búsqueda: ~1.800 tokens (skill + vista de ~60 publicaciones). Salida: ~900.
- **≈ USD 0,006 por búsqueda**; las 11 de test, ≈ USD 0,07 (≈ USD 0,14 si todas reintentan).
- Con Sonnet 4.5 (USD 3 / 15): ≈ USD 0,02 por búsqueda. Se elige Haiku porque la tarea es
  leer ~60 títulos y citar; si los juicios muestran que no alcanza, se compara con Sonnet.
- Captura: gratis, ~25 s por búsqueda en el navegador.
- **Serendipia** (`harness/serendipia.py::costo`): por producto, ~4.000 tokens de entrada
  (skill + ~45 textos filtrados) y ~1.200 de salida ≈ **USD 0,01 por producto** con Haiku;
  los 10 de test ≈ USD 0,10 (el doble si todos reintentan). El costo real queda en
  `divergente_test_api.json` cuando corre el workflow. Recolección de voces: ~1 min por
  producto en el navegador.

## Áreas en profundidad

1. **Orquestación y guardrails:** etapa divergente (LLM) → *gate* en código que verifica
   cada cita → reintento con los errores → etapa convergente con chequeos en código y
   motor con topes y traza (`harness/motor.py`, `harness/votos.py`, `harness/divergente.py`,
   `harness/serendipia.py`: embudo C1-C5 con el motivo de cada muerte).
2. **Evaluación:** partición fija, baseline sin LLM, juicios humanos a ciegas con rúbrica,
   acuerdo entre jueces (kappa ponderado) y LLM juez calibrado contra humanos
   (`data/evaluacion/`, `scripts/calcular_juicios.py`, `scripts/juez_llm.py`).
3. **Skills** (complementaria): skills curadas por el equipo (`skills/`); en clase vimos que
   las curadas suman y las autogeneradas restan.

## Antecedentes (versión breve)

**Mercado.** *Nubimetrics* (Argentina) clasifica categorías de Mercado Libre por crecimiento
de ventas y saturación de competencia, y rankea búsquedas en alza. *Jungle Scout* (Amazon)
da un Opportunity Score con demanda (unidades vendidas), competencia y calidad de los
listados. Las dos miden **cuánto** se vende y **cuánta** competencia hay. Lo nuestro lee
**qué** se elige frente a qué (formato, marca, función, origen) y propone **por qué**,
con citas verificables y explicaciones rivales: es complementario, no un reemplazo.

**Literatura.** Zhou et al. (2024), *Hypothesis Generation with Large Language Models*
(arXiv 2404.04326): un LLM genera hipótesis desde pocos ejemplos y las refina; miden por
cuánto mejoran la predicción frente a few-shot (+3 a +32 puntos). Usamos la misma idea
(hipótesis desde datos, refinadas contra evidencia) con otra métrica: juicio humano y
supervivencia a la refutación. Para el LLM juez seguimos la práctica de calibrarlo contra
humanos con kappa (encuesta de Gu et al., 2024, *A Survey on LLM-as-a-Judge*, arXiv 2411.15594).
Base conceptual: preferencia revelada (lo que se compra, no lo que se declara).

## Reparto propuesto (para que el git refleje a todos)

| Quién | Qué | Entregable verificable |
|---|---|---|
| Dario | Evaluación: juicios, kappa, calibración del juez | `data/evaluacion/juicios_*.csv`, resultados en README |
| Nilo | Datos: capturas nuevas (Compra Internacional que sí vende, otras categorías) | `data/capturas/`, entrada en BITACORA |
| Victoria | Antecedentes completos y presentación | sección ampliada acá, slides |
| Patricio | Harness, orquestación y corrida con LLM | `harness/`, workflow `llm`, resultados en test |
