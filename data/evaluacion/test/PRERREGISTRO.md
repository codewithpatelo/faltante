# Prerregistro de la corrida de test (escrito el 16/11/2026, antes de correrla)

**Hipótesis.** Con el mismo embudo convergente (guardrail, C1 dolor, C3 demanda, C4 hueco, C5 la
eligen, C6 margen) y los mismos jueces, el LLM deja **más oportunidades distintas no descartadas**
(que sobreviven o quedan condicionales con un experimento siguiente) que dos baselines sin LLM:
B1, mejorar el producto por su queja más frecuente (lo que hacen las herramientas comerciales);
B2, una regla que detecta pedidos de repuesto.

**Datos.** escala_test: 136 productos de 71 búsquedas, apartados por hash de la búsqueda antes de
leerlos (`scripts/unir_escala.py`). Nadie miró sus voces mientras se iteraba.

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
