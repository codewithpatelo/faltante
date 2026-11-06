---
name: medir_dolor
description: Clasificador del paso D. Dado un dolor (trabajo, obstáculo y qué hace mal la solución actual) y una tanda de textos de personas, dice quién lo cuenta como algo vivido y quién lo tiene resuelto. No sabe quién propuso el dolor ni de qué segmento es cada persona.
toca_datos: true
---

# medir_dolor

Para cada texto de la lista, decidí si la persona que lo escribió **cuenta este dolor como algo que
le pasó o que hace**. Tiene que estar en el texto: no lo deduzcas del producto que compró. Un deseo
("estaría bueno que…") o una pregunta genérica no cuentan; una pregunta que muestra el problema
("¿se cae con el calor? el mío anterior se caía") sí.

De las que lo tienen, marcá cuáles dicen que **ya lo resolvieron** (con este producto u otra cosa).

Ante la duda, no lo marques.

## Salida (JSON)

```json
{"tienen": ["E012.o34", "E047.p3"], "resuelto": ["E047.p3"]}
```
