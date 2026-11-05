# Decisiones

Qué elegimos, contra qué, por qué. Para que cualquiera del grupo pueda defenderlas.

**El LLM propone, el código decide.**
El LLM abre (abduce oportunidades desde texto desordenado); siete supuestos críticos probados
en código cierran (guardrail y C1 a C6). La divergencia trae hipótesis; la convergencia mata
el humo.
Un LLM que también se juzga a sí mismo confirma lo que propuso.

**Guardrails en código, no en el prompt.**
"Citá textos reales" en el prompt es una sugerencia. En `errores_de_citas` (`harness/chequeos.py`)
es una regla: la cita tiene que existir, ser literal y venir de dos textos distintos; si no,
el error vuelve al modelo una vez y lo que sigue mal se descarta en el embudo.

**El programa recuenta por su cuenta.**
El LLM lee una muestra filtrada; C1 y C2 cuentan sus palabras clave en todos los textos. Así
una señal no pasa por estar bien redactada.

**Preguntas de indecisos antes que opiniones.**
Las opiniones dicen qué le pasó a quien ya compró; las preguntas muestran por qué alguien
duda o no encuentra algo ("¿venden el filtro solo?"). Van todas; de las opiniones, las más
informativas (Timoshenko y Hauser).

**Lo que se deja pasar también es un voto (C5).**
"Nadie lo vende con volumen" no prueba que haya un hueco: si la alternativa se ofrece con
stock local y a precio comparable, y la gente igual elige el producto de origen, la necesidad
no alcanza para que la compren. Es humo. Lo importado (con espera) y lo caro no cuentan como
alternativa, porque explican por sí solos que no se elija.

**Una oportunidad que nadie atiende tiene que dejar plata al precio que la gente paga.**
C4 mira si ya se vende; C6 calcula el margen con el precio de lo que efectivamente se vendió
(una publicación sin ventas puede pedir cualquier cosa). Si no llega, calcula el FOB máximo:
la oportunidad queda condicional y el experimento siguiente es pedir cotización.

**Confianza calculada, no opinada.**
Sobrevivir dice que nada refutó la oportunidad; no dice cuán sólida es la evidencia. La
confianza (alta, media, baja) sale de cinco factores de sí o no que calcula el programa.

**Baselines sin LLM por el mismo embudo.**
B1 (queja más frecuente) es lo que haría un análisis de palabras; B2 (pedidos de repuesto)
es una regla fuerte escrita después de leer dev. Si el LLM no les gana en test, el LLM sobra.

**Partición por producto, decidida antes de leer.**
Dev para iterar skill, criterios y umbrales; test una sola vez, con todo congelado.

**Captura desde el navegador.**
La API de búsqueda de Mercado Libre devuelve 403 aun con token válido. Leer la página con
la sesión del usuario es lo único que funciona; se guarda solo el texto visible.

**Código escrito a mano, sin frameworks de agentes.**
El embudo es una lista de siete supuestos críticos con nombre (`harness/embudo.py`). La defensa es
individual y cada uno tiene que poder explicarlo por dentro; un framework deja una caja negra.

**DeepSeek Flash.**
Leer ~45 textos cortos y citar es una tarea chica y estructurada, y lo que falta es escala: a
~USD 0,003 por producto, 1.000 productos cuestan ~USD 3. Se compara con un modelo más grande
(DeepSeek V4 Pro) solo si el juicio humano muestra que no alcanza.
