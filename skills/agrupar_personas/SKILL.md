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

Recibís líneas `[id] (búsqueda) situación | quiere lograr | dolor` de personas de muchas búsquedas.

1. Buscá situaciones de vida que se repiten **en búsquedas distintas**: dónde vive, con quién,
   qué hace, qué restricción tiene (espacio, tiempo, plata, salud, cuerpo, mascotas, chicos,
   trabajo, auto, clima). Que la misma situación aparezca en compradores de cosas que no tienen
   nada que ver es justo lo que buscamos.
2. Definí entre 15 y 40 segmentos. Cada uno tiene que poder juntar gente de **al menos 3
   búsquedas distintas**. Si una situación solo aparece en una búsqueda ("usa el celular en
   el auto" sale solo de los soportes de celular), no es un segmento: es la descripción del
   producto. Tampoco valen un motivo de compra ("es para regalo", "para revender", "por la
   garantía") ni un rasgo de todos ("quiere calidad").
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
