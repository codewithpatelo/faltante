---
name: agrupar_personas
description: Paso S de la divergencia. Agrupa a las personas de muchos productos distintos en segmentos según su situación y lo que quieren lograr, no según el producto que compraron. Primero define los segmentos; después asigna a cada persona.
toca_datos: true
---

# agrupar_personas

**Pregunta:** ¿qué grupos de gente hay detrás de compras que no tienen nada que ver entre sí?

Una persona que compró un bebedero para gatos y otra que compró una aspiradora de auto pueden
estar en la misma situación ("vive en un departamento con mascotas y pelos por todos lados").
Ese grupo, y no el producto, es el que tiene una necesidad que alguien puede atender.

## Tarea "definir"

Recibís líneas `[id] situación | quiere lograr | dolor` de personas de muchos productos.

1. Buscá situaciones de vida compartidas: dónde vive, con quién, qué hace, qué restricción
   tiene (espacio, tiempo, plata, salud, mascotas, chicos, trabajo, clima).
2. Definí entre 15 y 40 segmentos. Cada uno, una situación compartida que pueda incluir gente
   de productos y búsquedas distintas. No definas un segmento por categoría de producto
   ("compradores de termos") ni por un rasgo de todos ("quiere calidad").
3. Para cada segmento escribí `quien` (la situación) y `criterio` (cómo decidir si una persona
   entra). Que no se superpongan: una persona entra en un solo segmento.

Salida:

```json
{"segmentos": [{"id": "G1", "nombre": "...", "quien": "...", "criterio": "..."}]}
```

## Tarea "asignar"

Recibís los segmentos y una tanda de personas. Asigná cada persona al segmento cuyo criterio
cumple, o `"-"` si no cumple ninguno o el texto no alcanza para saberlo. Ante la duda, `"-"`.

Salida:

```json
{"asignaciones": [["E012.o34", "G3"], ["E012.p2", "-"]]}
```
