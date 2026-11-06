---
name: leer_personas
description: Paso A de la divergencia. Lee las opiniones y preguntas de un producto y, de cada persona que cuenta algo de sí, arma un mapa de empatía chico (situación, qué quiere lograr, dolor, ganancia, qué teme, con qué compara), citando su texto. No propone qué traer.
toca_datos: true
---

# leer_personas

**Pregunta:** ¿quién es cada persona que escribió, y qué revela de su vida su elección?

Cada opinión es de alguien que **eligió** este producto; cada pregunta, de alguien que
**duda** antes de elegirlo. Detrás de cada texto hay una persona con una situación, algo que
quiere lograr, algo que le duele y algo que teme. Eso es lo que buscamos, no la ficha del producto.

## Entrada

El producto (título y búsqueda donde se eligió) y sus textos numerados: opiniones `[o12]` y
preguntas al vendedor con su respuesta `[p3]`.

## Qué anotar de cada persona (mapa de empatía)

- `situacion`: quién es o en qué circunstancia está, en términos generales y sin nombrar el
  producto: "vive en un departamento chico con dos gatos", "entrena en casa sin espacio",
  "cocina para uno", "trabaja muchas horas sentado". Solo si el texto lo dice o lo deja claro.
- `quiere_lograr`: el trabajo que le encarga al producto, en sus palabras ("que el agua no se
  corte si se va la luz", "llevar el almuerzo al trabajo").
- `dolor`: lo que le molesta, le falla o tolera a regañadientes.
- `ganancia`: lo que valora o lo que lo haría feliz.
- `teme`: la duda o el miedo que lo frena (en las preguntas suele ser lo principal).
- `compara_con`: otra cosa que tuvo, vio o usa en lugar de esto.
- `fragmento`: un pedazo **literal** de su texto (4 caracteres o más) que sostenga lo anotado.

Un campo que el texto no dice queda vacío (`""`). No inventes situaciones.

## Criterios (los chequea el programa)

- Solo personas que cuentan algo: "Excelente, llegó rápido" no se anota.
- `texto` es uno de los IDs de la entrada y `fragmento` está tal cual en ese texto.
- Las quejas del envío o del vendedor no son dolores del producto: no se anotan.

## Salida (JSON)

```json
{"personas": [{"texto": "o12", "situacion": "...", "quiere_lograr": "...", "dolor": "...",
   "ganancia": "...", "teme": "...", "compara_con": "...", "fragmento": "..."}]}
```
