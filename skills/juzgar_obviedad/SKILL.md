---
name: juzgar_obviedad
description: Juez auxiliar para comparar prompts. Clasifica cada oportunidad propuesta como obvia o no obvia. No decide qué se recomienda (eso lo hace el embudo en código); solo mide si un prompt trae ideas que una persona mirando el mercado no vería enseguida.
---

# juzgar_obviedad

Para cada oportunidad decidí si es **obvia** o **no obvia**.

**Obvia** si cumple alguna:
- es un repuesto, consumible o accesorio de alguno de los productos ancla de sus señales;
- es el mismo producto ancla "pero mejor": más grande, más chico, de otro material, con más piezas, en pack;
- se le ocurre a cualquiera que mire la búsqueda del producto ancla en Mercado Libre.

**No obvia** si conecta necesidades de productos o búsquedas distintas en algo que no es
ninguno de los anclas, o si revela un uso o una preferencia que la búsqueda del ancla no muestra.

No juzgues si es buena, rentable o viable: solo si es obvia.

## Salida (JSON)

```json
{"juicios": [{"id": "O1", "obvia": true, "motivo": "es el repuesto del ancla"}]}
```
