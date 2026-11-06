---
name: hipotesis_de_dolor
description: Paso D de la divergencia. Lee el mapa de empatía de un segmento y formula hipótesis de dolor - qué trabajo intenta hacer esa gente, qué se lo impide, con qué lo resuelve hoy y qué hace mal esa solución. No propone productos.
toca_datos: true
---

# hipotesis_de_dolor

**Pregunta:** ¿qué le duele a este grupo de gente, y qué hace mal lo que usa hoy para resolverlo?

El error número uno de los emprendedores es saltar a la solución antes de entender el problema.
Acá no se propone nada para traer: solo se formula el problema, para que el programa lo pueda
medir y refutar antes de seguir.

## Entrada

El mapa de empatía del segmento: quiénes son, qué eligieron y qué dejaron pasar, qué ven en sus
búsquedas, y una línea por persona con su ID (`E012.o34`): situación, qué quiere lograr, dolor,
ganancia, miedo, con qué compara.

## Qué escribir (de 1 a 4 dolores)

- `trabajo`: lo que intentan lograr, en términos de su vida y no del producto ("tener el celular a
  la vista mientras manejan", no "un soporte mejor").
- `obstaculo`: lo que se los impide.
- `solucion_actual`: con qué lo resuelven hoy (el producto que eligieron, una improvisación, nada).
- `que_hace_mal`: qué falla de esa solución (lo que se quejan, lo que aguantan a regañadientes, lo
  que abandonan). Si la solución actual funciona bien, el dolor no es un agujero: no lo escribas.
- `personas`: IDs de personas que lo cuentan **como algo que les pasó o que hacen** ("se me cae",
  "tuve que", "lo uso para"). Un deseo ("estaría bueno", "ojalá") no cuenta como evidencia.

## Criterios (los chequea el programa)

Otro modelo, que no ve lo que escribiste salvo el dolor, lee los textos originales de toda la gente
del segmento y de un grupo de control al azar, y cuenta quién lo tiene. El dolor sobrevive si lo
tienen bastantes personas, en más de un producto, bastante más que en el control, y la mayoría no
lo tiene resuelto. Escribí el dolor de forma que alguien que lee un texto pueda decir si esa persona
lo tiene o no.

## Salida (JSON)

```json
{"dolores": [{"id": "D1", "trabajo": "...", "obstaculo": "...", "solucion_actual": "...",
   "que_hace_mal": "...", "personas": ["E012.o34", "E047.p3"]}]}
```
