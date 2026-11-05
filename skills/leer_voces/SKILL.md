---
name: leer_voces
description: Etapa divergente. Cruza el voto con los pies (qué se elige entre las opciones de una búsqueda y qué se deja pasar) con el voto con las manos (opiniones de compradores y preguntas de indecisos) de un producto que vende, y propone oportunidades de importación citando textos reales.
toca_datos: true
---

# leer_voces

**Pregunta:** ¿qué necesidad no resuelta aparece cuando se cruza lo que la gente elige con
lo que dice antes y después de comprar?

## Entrada

- **Pies:** el producto ancla, uno de los 1 o 2 más elegidos de su búsqueda (título, precio,
  "+N vendidos").
- **Manos, compradores:** opiniones, numeradas `[o12]`.
- **Manos, indecisos:** preguntas al vendedor con su respuesta, numeradas `[p3]`. Son las más
  valiosas: muestran por qué alguien duda o no compra.

## Procedimiento

1. Leé las preguntas primero. Buscá lo que piden y el vendedor **no tiene** ("no lo tenemos",
   "no viene", "no trabajamos"), repuestos y consumibles, compatibilidades (voltaje, medidas).
2. Leé las opiniones. Buscá: **quejas** repetidas sobre un atributo, **usos no previstos**
   ("lo uso para…"), **deseos** ("ojalá", "le faltaría", "debería venir con").
3. Cruzá con los pies: una queja en un producto que vende mucho vale más (la gente lo compra
   igual porque no hay algo mejor); una duda en uno que vende poco explica por qué no vende.
4. Escribí **señales** (0 a 6) y **oportunidades** (0 a 3). Cero es válido.
5. Para cada oportunidad: qué habría que traer, qué búsqueda en Mercado Libre la verificaría
   y con qué palabras se reconoce un equivalente.

## Lo que aprendimos en dev (antes de congelar para test)

- **La unidad tiene que ser la que el mercado compra.** Si en Mercado Libre el repuesto se
  vende suelto, proponé el suelto; si proponés un kit, el precio de referencia no corresponde.
- **Lo barato no paga el envío.** Debajo de ~$10.000 el costo fijo por unidad de Mercado Libre
  (~$2.500) se come el margen: un consumible barato tiene que ir en pack o junto al producto.
- **El criterio de equivalencia mira el comienzo del título**, que en Mercado Libre es lo que
  se vende ("Disco …" es un disco; "Afilador … con discos" es un afilador). Usá `empieza_con`
  para el sustantivo y `todos` / `excluir` para el resto.

## Criterios (los chequea el programa)

- Cada señal cita al menos **2 textos distintos** con un fragmento **literal** (≥ 4 caracteres).
- Cada señal trae `palabras_clave`: el programa las cuenta en todas las opiniones y preguntas.
  Si aparecen en menos de 3 textos, la señal es anecdótica y la oportunidad muere.
- No inventar ventas, precios ni opiniones.

## Salida (JSON)

```json
{"señales": [{"id": "S1", "tipo": "faltante|queja|deseo|uso_no_previsto|duda",
   "descripcion": "...", "palabras_clave": ["repuesto", "disco"],
   "citas": [{"texto": "p3", "fragmento": "..."}, {"texto": "o12", "fragmento": "..."}]}],
 "oportunidades": [{"id": "O1", "que_traer": "...", "por_que": "qué contradicción pies-manos la sostiene",
   "señales": ["S1"], "busqueda_ml": "...",
   "criterio_equivalencia": {"empieza_con": ["disco", "repuesto"], "todos": [["rodante", "rodillo"]], "excluir": ["motosierra"]}}]}
```

## Qué no hacer

- No proponer el mismo producto ancla: ya se vende.
- No confundir una queja de envío o del vendedor con una necesidad del producto.
