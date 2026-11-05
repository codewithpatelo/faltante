---
name: cruzar_senales
description: Paso B de la divergencia. Recibe las señales verificadas de muchos productos y categorías y propone oportunidades de importación que conectan señales de al menos 2 productos distintos. De ahí salen las hipótesis no obvias.
toca_datos: true
---

# cruzar_senales

**Pregunta:** ¿qué producto, que hoy nadie trae, resolvería necesidades que aparecen
dispersas en productos distintos?

Mirar un producto solo da ideas obvias (su repuesto, su versión mejorada). Lo no obvio aparece
al cruzar: la misma necesidad en categorías que no tienen nada que ver, un uso no previsto de
un producto que revela otro producto, una concesión que se repite, una preferencia que
contradice lo que se ofrece.

## Entrada

Una lista de señales ya verificadas por el programa, cada una con su ID (`P12.S2` = señal 2
del producto 12), el producto y la búsqueda donde apareció, cuántos textos la mencionan, y una
cita.

## Procedimiento

1. Agrupá señales que expresan la misma necesidad de fondo aunque vengan de productos
   distintos (por ejemplo, "no entra en la mesada" en una pava y en una freidora).
2. Buscá tensiones: lo que la gente elige pese a un defecto, lo que deja pasar pese a una
   ventaja, usos que ningún producto contempla.
3. Para cada grupo, preguntate qué producto resolvería la necesidad de fondo. Descartá lo
   obvio: el repuesto del mismo producto o "el mismo producto pero mejor".
4. Escribí de 0 a 5 **oportunidades**. Cero es válido.

## Lo que ya aprendimos (lo chequea el programa después)

- Se va a probar si **ya lo vende alguien** (C4) y si, cuando se ofrece, **la gente lo elige
  o lo deja pasar** (C5). Proponé cosas que plausiblemente no estén ofrecidas con stock local.
- **Lo barato no paga el envío:** debajo de ~$10.000 el costo fijo de Mercado Libre se come
  el margen; un consumible barato tiene que ir en pack o junto a otro producto.
- **La unidad tiene que ser la que el mercado compra** (suelto, pack, kit).
- **El criterio de equivalencia mira el comienzo del título**, que en Mercado Libre es lo que
  se vende ("Disco …" es un disco; "Afilador … con discos" es un afilador). Usá `empieza_con`
  para el sustantivo y `todos` / `excluir` para el resto.

## Criterios (los chequea el programa)

- Cada oportunidad cita **al menos 2 señales de productos distintos**, con IDs que existan.
- `busqueda_ml` es lo que alguien escribiría en Mercado Libre para encontrarlo.

## Salida (JSON)

```json
{"oportunidades": [{"id": "O1", "que_traer": "...",
   "por_que": "qué necesidad de fondo conecta las señales y por qué nadie la atiende",
   "señales": ["P12.S2", "P47.S1"], "busqueda_ml": "...",
   "criterio_equivalencia": {"empieza_con": ["..."], "todos": [["...", "..."]], "excluir": ["..."]}}]}
```
