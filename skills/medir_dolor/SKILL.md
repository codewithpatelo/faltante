---
name: medir_dolor
description: Clasificador de C1. Dado un problema (trabajo, obstáculo y qué hace mal la solución actual) y una tanda de textos de personas, dice quién cuenta tener ESE problema y quién ya lo resolvió. Primero anota qué le pasa a cada persona según su texto y después decide, sin respuesta por defecto. No sabe quién propuso el problema ni de qué grupo es cada persona.
toca_datos: true
---

# medir_dolor

Medís cuánta gente tiene un problema. Si marcás de más, se aprueba una idea para un problema que
nadie tiene; si marcás de menos, se descarta uno real. Los dos errores cuestan igual: **no hay
respuesta por defecto**.

## Cómo decidir, texto por texto

1. Anotá en pocas palabras **qué le pasa a esta persona según su texto** (no según el producto
   que compró). Si no cuenta nada de sí ("excelente, llegó rápido"), anotá "nada".
2. **Tiene el problema** si lo que le pasa es **este** problema: el mismo trabajo y el mismo
   obstáculo, o uno que es lo mismo dicho de otra forma. No alcanza con quejarse: una queja de
   otra cosa (el envío, el color, el tamaño, la calidad en general, otro defecto) no es este
   problema. Una pregunta cuenta si muestra que le pasa ("¿esto aguanta una semana? se me
   secaron todas la última vez"); una duda genérica antes de comprar ("¿de qué material es?") no.
3. **Lo resolvió** si el texto dice que ya no le pasa: el producto u otra cosa se lo solucionó
   ("ahora sí puedo…", "con esto se terminó…"). Si solo elogia el producto sin hablar del
   problema, no hay nada que decidir: no lo tiene.

## Ejemplos (problema: "regar las plantas cuando se va de viaje / se le secan si falta varios días")

- "Me fui 10 días y las encontré secas, el riego por goteo no anduvo" → tiene, no resuelto.
- "Con este kit me fui dos semanas y volví y estaban perfectas" → tiene, resuelto.
- "Llegó roto el envase" → no tiene: es otra queja.
- "Hermoso, lo recomiendo" → no tiene: no cuenta nada.

## Salida (JSON)

```json
{"textos": [{"id": "E012.o34", "le_pasa": "...", "tiene": true, "resuelto": false}]}
```

Una entrada por texto de la lista.
