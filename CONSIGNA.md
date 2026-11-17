# Cumplimiento de la consigna

Cada requisito de la consigna oficial (TP integrador, IA Agéntica 2026), dónde se verifica en el
repo y qué falta. ✅ cumplido · 🟡 parcial · ❌ falta.

| Requisito | Dónde se ve | Estado |
|---|---|---|
| **Utilidad real**: usuario identificable | Importadores y vendedores chicos de Mercado Libre que deciden qué traer (README, "Qué hace") | 🟡 falta mostrárselo a 1 o 2 importadores |
| **IA generativa en el núcleo** | Cuatro pasos con LLM: leer personas, armar segmentos, proponer, y dos jueces (dolor y equivalencias) | ✅ |
| **Hipótesis medible contra baseline, partición fija** | `data/evaluacion/test/PRERREGISTRO.md`; resultado en el README, "¿Sirve?" | ✅ contra reglas sin LLM: 16, 4, 0 en test (p = 0,002). 🟡 contra el modelo solo de una (B4): los datos refutan 9 de sus 10 recomendaciones, falta el juicio humano a ciegas. 🟡 generar: la versión por situación perdía con proponer directo (B3); rehecha por trabajo, en dev empata (30 contra 31) |
| **Datos verificados** | README, "Datos": fuente, volumen, fecha, cómo se eligieron | ✅ |
| **Economía**: costo por tarea, latencia, elección de modelo | README, "Costo y modelo"; cada corrida guarda tokens, USD y segundos por llamada (`traza`) | ✅ |
| **Git con trabajo distribuido** | `git log` | 🟡 Darío: requisitos del README, su planilla a ciegas y el LEEME; faltan Nilo y Victoria (su planilla en `data/evaluacion/humano/`) |
| **Antecedentes** (mercado y literatura) | Abajo | ✅ |
| **≥ 2 áreas en profundidad** | Abajo | ✅ |
| **Repo replicable** con README, Makefile, skills y reglas | `make todo` desde un clon limpio (o `docker build` + `docker run`); `skills/`, `AGENTS.md` | ✅ |
| **Relato del desarrollo** (bloqueos, qué no funcionó, qué cambió el rumbo) | `BITACORA.md`; evidencia de cada decisión en `DECISIONES.md` y `data/evaluacion/` | ✅ |
| **Presentación** (15 min, 10-11/12) | — | ❌ después de la entrega |

## Áreas en profundidad

1. **Orquestación con verificación y reintento.** Un flujo fijo (no un agente libre: cada paso
   tiene una sola salida posible y se puede auditar): personas → segmentos → propuestas → seis
   supuestos críticos. Cada salida del LLM pasa por un guardrail en código (las citas existen, el
   fragmento está en el texto, la propuesta cruza productos); si falla, el error vuelve al modelo
   una vez y lo que sigue mal se descarta. `harness/personas.py`, `harness/divergente.py`,
   `harness/embudo.py`, `harness/modelo.py`.
2. **Evaluación.** Benchmark propio con partición fija por búsqueda, dos baselines sin LLM y dos con el mismo modelo (B3, la generación sola; B4,
   todo de una) por el mismo embudo, prerregistro de cada comparación, 3 corridas por versión en dev y una sola en
   test. Los dos jueces LLM se validan aparte: el de dolor con un control al azar y un placebo
   (0 falsos positivos), el de equivalencias con 40 desacuerdos etiquetados a ciegas (32 aciertos
   contra 8 del criterio viejo), y los dos contra juicio humano (`data/evaluacion/humano/`).
3. **Observabilidad y guardrails.** Cada llamada queda en la traza con paso, intento, tokens,
   segundos, errores del guardrail y si se cortó; el costo de cada corrida sale de ahí. Ningún
   umbral está a ojo: cada uno con su fuente o su prueba estadística (`harness/umbrales.py`).

También: **skills** (`skills/`, uno por paso del LLM, con entrada, procedimiento y salida) y
**optimización de prompts** (25 variantes del paso que proponía, tomadas de la literatura,
comparadas 3 veces cada una, y la mejor optimizada al estilo GEPA; resultados en
`data/serendipia/espacio_*.json` y `optimizacion_escala_dev.json`, conclusiones en DECISIONES).

## Antecedentes

**Mercado.** Las herramientas para vendedores miden *cuánto* se vende y *cuánta* competencia
hay: Nubimetrics (Mercado Libre) rankea categorías por crecimiento y saturación; Jungle Scout,
Helium 10 y el Product Opportunity Explorer de Amazon dan un puntaje de oportunidad con demanda,
competencia y quejas de los listados, y su sugerencia típica es mejorar el producto por su queja
(nuestro baseline B1). Minea o PiPiADS rastrean productos virales en redes, y los importadores
argentinos completan el circuito a mano: ven el producto, lo buscan en Alibaba o 1688 y cotizan
con un agente (BorderBox, Chilat). Ninguna dice *qué necesidad queda sin atender ni para quién*,
ni intenta refutar la idea antes de recomendarla. Faltante es complementario: parte de la gente,
no del producto, y cada recomendación llega con el dato que no la pudo matar.

**Literatura.** *Necesidades desde reseñas:* Timoshenko y Hauser (2019, *Marketing Science*)
filtran el contenido informativo antes de extraer necesidades; con LLM (2025) igualan a analistas
profesionales (medida: qué proporción de las necesidades de los analistas encuentran). *Ideas
con LLM:* Si, Yang y Hashimoto (2024) encuentran ideas más novedosas que las de expertos, pero el
ranking automático coincide poco con humanos; Terwiesch et al. (2026) miden más intención de
compra en ideas de GPT-4 que en las de personas, pero menos diversidad (1 − similitud coseno
media); Maiden et al. (2025) generan oportunidades más novedosas con reglas de necesidades y
pivotes, juzgadas por otro LLM; Cristofaro et al. (2025) advierten que la IA tiende a lo conocido
al reconocer oportunidades. *Jueces LLM:* Zheng et al. (2023) muestran acuerdo de nivel humano,
con sesgos (posición, autopromoción): hay que calibrarlos contra personas. *Economía:* Kirzner y
Huerta de Soto (el empresario descubre desajustes), preferencia revelada, Bresnahan y Reiss
(1991: con 3 a 5 competidores un mercado ya compite). **Qué aporta Faltante:** separa quien
propone de quien mide, mide la necesidad contra un control con una prueba estadística, y la
contrasta con lo que la gente elige y deja pasar en el mercado real, no con un juez de "novedad".

## Correr el LLM sin compartir claves

`DEEPSEEK_API_KEY` es un secreto del repo. Pestaña Actions → workflow **llm** → *Run workflow*,
con la tarea `serendipia` (partición `escala_dev` o `escala_test`) o `equivalencias`. Los
resultados quedan completos en el registro de la corrida (líneas `RESULTADO <archivo> <json>`).
