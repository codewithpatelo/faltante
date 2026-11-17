# Prerregistro de la corrida de test (escrito el 16/11/2026, antes de correrla)

**Hipótesis.** Con el mismo embudo convergente (guardrail, C1 dolor, C3 demanda, C4 hueco, C5 la
eligen, C6 margen) y los mismos jueces, el LLM deja **más oportunidades distintas no descartadas**
(que sobreviven o quedan condicionales con un experimento siguiente) que dos baselines sin LLM:
B1, mejorar el producto por su queja más frecuente (lo que hacen las herramientas comerciales);
B2, una regla que detecta pedidos de repuesto.

**Datos.** escala_test: 136 productos de 71 búsquedas, apartados por hash de la búsqueda antes de
leerlos (`scripts/unir_escala.py`). Nadie miró sus voces mientras se iteraba.

**Declaración.** 46 de esos 136 productos (los del corpus del 05/11) ya pasaron una vez por test
el 06/11, con una versión vieja (señales por producto): 6 propuestas, ninguna sobrevivió
(commit `77b8094`). Ese resultado se vio; las voces no. Por eso además del total se informa,
por separado, el resultado sobre los **90 productos nuevos** (corpus del 06/11, prefijo `F`), que
ninguna versión leyó nunca: es el test limpio.

**Sistema congelado.** El commit en el que se lanza la corrida. Mismo modelo (DeepSeek Flash),
mismos skills y umbrales que la última corrida de dev. Se corre **una sola vez**. Las búsquedas
que proponga se capturan con el mismo script y las equivalencias las juzga el mismo juez.

**Medidas, en este orden.**
1. Oportunidades distintas no descartadas (por búsqueda propuesta): LLM contra B1 y contra B2.
2. Proporción de no descartadas sobre las que pasan el guardrail (cuánto humo mata el embudo).
3. Dónde muere cada una (C1 a C6) y con qué motivo: análisis de fallas.
4. Costo (USD), tokens y latencia de la corrida.

**Regla.** La hipótesis se sostiene si el LLM deja más oportunidades distintas no descartadas
que B1 y que B2. Como es una sola corrida, se informa junto a la variabilidad entre corridas
medida en dev (3 corridas de la misma versión), y si el LLM deja más pero dentro de esa
variabilidad, se dice así. Si queda en 0 o por debajo de un baseline, se informa igual.

**Lo que no mide.** Si las oportunidades son obvias o si alguien las traería: eso lo da el
juicio humano a ciegas (`data/evaluacion/humano/`) y, en definitiva, una cotización y una
preventa.

## Agregado del 16/11, antes de correrlo: baseline B3 (zero-shot)

B1 y B2 resultaron débiles (las de B1 no son productos; B2 casi nunca dispara), así que ganarles
prueba poco. Se agrega el baseline que la consigna nombra primero: **el mismo modelo con un
prompt zero-shot** que lee cada producto y propone qué traer en una sola llamada, sin personas ni
grupos (`harness/directo.py`, `skills/proponer_directo/`). Pasa por el mismo embudo y los mismos
jueces. Se prueba primero en dev (sin tocar el prompt después de ver el resultado) y se corre una
sola vez en test. El programa no cambia. **Regla:** la arquitectura aporta si el programa deja
más oportunidades distintas no descartadas que B3 en test. Si B3 deja tantas o más, se informa
que alcanza con preguntarle al modelo, y que lo que aporta el programa es el embudo.

## Agregado del 16/11, antes de correrlo: baseline B4 (one-shot de punta a punta)

B3 no es el rival justo de todo el programa: solo reemplaza la generación de ideas y después usa
nuestro embudo. El rival justo es **lo que haría alguien que le pregunta al modelo qué importar**:
una sola llamada por producto que lee las opiniones y lo que hoy se ofrece en su búsqueda (la
misma captura que usa el programa), aplica ella misma los cinco criterios del embudo (dolor,
nadie lo vende, lo comprarían, deja plata, no es obvio) y devuelve la **recomendación final**
(`skills/recomendar_de_una/`, `harness/directo.py`). El prompt queda congelado en el commit que
agrega este texto; se corre en dev y en test a la vez, una sola vez cada una, y no se toca.

**Qué se compara: las recomendaciones finales de cada uno.** Del programa, las que el embudo no
descarta; de B4, todo lo que recomienda.

1. **Juicio humano a ciegas (la medida principal, porque no depende de nuestro embudo).** Las
   recomendaciones finales de B4 se suman a las planillas de oportunidades, mezcladas y sin decir
   de qué método salen; si son más de 20 por partición, se sortean 20 con semilla fija. Medida:
   proporción que la mayoría de los jueces marca concreta, no obvia y que cotizaría.
   **Regla:** el programa aporta frente a preguntarle al modelo si esa proporción es mayor en las
   suyas que en las de B4 (Fisher unilateral, p < 0,05). Si no, se informa que no.
2. **Auditoría con datos del mercado (descriptiva).** Las recomendaciones de B4 pasan por el
   embudo como cualquier propuesta: qué parte contradicen los datos y en qué chequeo. No es una
   prueba de la hipótesis (el embudo es nuestro, y las del programa lo pasan por construcción);
   dice cuánto de lo que recomienda el modelo solo lo refuta el mercado.
3. Cantidad de recomendaciones finales y costo de cada uno.

B3 queda como ablación de la generación: dice si leer personas y grupos genera mejores ideas que
pedírselas directo al modelo, con el mismo embudo.
