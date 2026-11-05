# Decisiones

Qué elegimos, contra qué, por qué. Para que cualquiera del grupo pueda defenderlas.

**El LLM propone, el código decide.**
El LLM abre (abduce oportunidades desde texto desordenado); seis chequeos en código cierran
(guardrail y C1 a C5).
Un LLM que también se juzga a sí mismo confirma lo que propuso.

**Guardrails en código, no en el prompt.**
"Citá textos reales" en el prompt es una sugerencia. En `errores_de_citas` (`harness/chequeos.py`)
es una regla: la cita tiene que existir, ser literal y venir de dos textos distintos; si no,
el error vuelve al modelo una vez y lo que sigue mal muere en el embudo.

**El programa recuenta por su cuenta.**
El LLM lee una muestra filtrada; C1 y C2 cuentan sus palabras clave en todos los textos. Así
una señal no pasa por estar bien redactada.

**Preguntas de indecisos antes que opiniones.**
Las opiniones dicen qué le pasó a quien ya compró; las preguntas muestran por qué alguien
duda o no encuentra algo ("¿venden el filtro solo?"). Van todas; de las opiniones, las más
informativas (Timoshenko y Hauser).

**Una oportunidad que nadie atiende tiene que dejar plata al precio que la gente paga.**
C4 mira si ya se vende; C5 calcula el margen con el precio de lo que efectivamente se vendió
(una publicación sin ventas puede pedir cualquier cosa). Si no llega, calcula el FOB máximo:
la oportunidad queda condicional y el experimento siguiente es pedir cotización.

**Baselines sin LLM por el mismo embudo.**
B1 (queja más frecuente) es lo que haría un análisis de palabras; B2 (pedidos de repuesto)
es una regla fuerte escrita después de leer dev. Si el LLM no les gana en test, el LLM sobra.

**Partición por producto, decidida antes de leer.**
Dev para iterar skill, criterios y umbrales; test una sola vez, con todo congelado.

**Captura desde el navegador.**
La API de búsqueda de Mercado Libre devuelve 403 aun con token válido. Leer la página con
la sesión del usuario es lo único que funciona; se guarda solo el texto visible.

**Código escrito a mano, sin frameworks de agentes.**
El embudo es una lista de seis chequeos con nombre (`harness/embudo.py`). La defensa es
individual y cada uno tiene que poder explicarlo por dentro; un framework deja una caja negra.

**Haiku 4.5.**
Leer ~45 textos cortos y citar es una tarea chica y estructurada. Se compara con un modelo
más grande solo si el juicio humano muestra que no alcanza.
