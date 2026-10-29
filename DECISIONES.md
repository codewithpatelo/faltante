# Decisiones

Qué elegimos, contra qué, por qué. Para que cualquiera del grupo pueda defenderlas.

**Loop ReAct escrito a mano, no LangGraph ni similares.**
El loop son ~150 líneas. La defensa es individual y cada uno tiene que poder explicar la
arquitectura por debajo; un framework ahorra dos días y deja una caja negra.

**Guardrails en código, no en el prompt.**
"No confirmes sin evidencia" escrito en el prompt es una sugerencia. En `motor.veredicto`
es una regla: el veredicto sin evidencia válida se rechaza y vuelve al modelo como error.

**Políticas intercambiables sobre el mismo motor.**
Fija, heurística y LLM llaman a las mismas cuatro operaciones. Así la comparación es justa
y los controles viven en un solo lugar.

**Baseline principal: el mismo set de skills sin loop (política fija).**
Si el agente no le gana a correr todo sobre todo, el loop es decoración. Lo que el loop
puede ganar es eficiencia (menos llamadas) y resolución semántica (nombres, inferencia).

**Adaptadores desacoplados de las skills.**
El riesgo del proyecto está en el acceso a datos. Cambiar de fuente no toca el harness.

**`insuficiente` es un veredicto de primera clase.**
Cuando la fuente falla, el sistema lo dice. Preferimos no recomendar a recomendar sin datos.

**Haiku 4.5 para el agente.**
El trabajo es clasificar, resolver nombres y elegir la próxima verificación: tareas cortas
y estructuradas. Modelos más grandes se prueban solo si Haiku falla en P1/P6.
