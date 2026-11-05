---
name: leer_voces
description: Paso A de la divergencia. Lee un producto muy elegido, lo que la gente dejó pasar en su búsqueda, y lo que dicen sus compradores e indecisos; devuelve señales (quejas, faltantes, deseos, usos no previstos) citando textos reales. No propone qué traer: eso se hace después, cruzando señales de muchos productos (skills/cruzar_senales).
toca_datos: true
---

# leer_voces

**Pregunta:** ¿qué le falta a la gente que eligió este producto, y qué dice eso de sus
preferencias?

## Entrada

- **Elección (voto con los pies):** el producto ancla, uno de los más elegidos de su búsqueda
  (título, precio, "+N vendidos"), y las alternativas de esa búsqueda: las que también se
  eligen y las que la gente **dejó pasar** (se ofrecen y casi no se venden).
- **Compradores (voto con las manos):** opiniones, numeradas `[o12]`.
- **Indecisos:** preguntas al vendedor con su respuesta, numeradas `[p3]`. Muestran por qué
  alguien duda o qué no encuentra.

## Procedimiento

1. Mirá la elección: ¿qué tiene el ancla que no tienen las que se dejaron pasar (precio,
   formato, tamaño, marca, origen)? Eso es una preferencia revelada.
2. Leé las preguntas: lo que piden y el vendedor **no tiene**, repuestos y consumibles,
   compatibilidades (voltaje, medidas), para qué lo quieren usar.
3. Leé las opiniones: **quejas** repetidas sobre un atributo, **usos no previstos** ("lo uso
   para…"), **deseos** ("ojalá", "le faltaría", "debería venir con"), **concesiones** ("no es
   lo ideal pero…": aceptan un defecto porque no hay algo mejor).
4. Escribí de 0 a 6 **señales**. Cero es válido. Una señal es lo que la gente necesita o
   prefiere, dicho en términos generales ("quiere higiene sin perder el filo"), no un producto.

## Criterios (los chequea el programa)

- Cada señal cita al menos **2 textos distintos** con un fragmento **literal** (≥ 4 caracteres).
- Cada señal trae `palabras_clave`: el programa las cuenta en todas las opiniones y preguntas.
  Si aparecen en menos de 3 textos, la señal es anecdótica y se descarta.
- No inventar ventas, precios ni opiniones. No confundir una queja de envío o del vendedor con
  una necesidad del producto.

## Salida (JSON)

```json
{"señales": [{"id": "S1", "tipo": "faltante|queja|deseo|uso_no_previsto|duda|concesion|preferencia",
   "descripcion": "la necesidad, en términos generales", "palabras_clave": ["repuesto", "disco"],
   "citas": [{"texto": "p3", "fragmento": "..."}, {"texto": "o12", "fragmento": "..."}]}]}
```
