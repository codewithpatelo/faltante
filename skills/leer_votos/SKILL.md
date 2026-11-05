---
name: leer_votos
description: Etapa divergente. Lee una búsqueda de Mercado Libre separada en lo que vende y lo que no, y abduce hipótesis de necesidad u oportunidad citando publicaciones concretas.
toca_datos: true
---

# leer_votos

**Pregunta:** ¿qué eligió la gente en esta búsqueda y qué dejó pasar, y qué necesidad
explica esa elección mejor que "es más barato"?

## Procedimiento

1. Mirá la vista de la búsqueda (`scripts/vista_votos.py`): GANAN (con "+N vendidos") y
   PIERDEN, cada una con su índice `[i]`, precio y si es internacional.
2. Compará ganadoras contra perdedoras en estos ejes, uno por uno: formato (tamaño,
   tipo de aparato), marca, rango de precio, origen (local o internacional), palabras del
   título, función que promete, compatibilidad (voltaje, repuestos).
3. Buscá el patrón que el precio **no** explica: algo caro que vende, algo barato que no,
   una función que aparece solo en lo que vende.
4. Escribí entre 0 y 3 hipótesis. Cero es una respuesta válida si lo único que se ve es precio.
5. Para cada una, listá las explicaciones rivales y cómo se refutaría con datos.

## Criterios (los chequea `validar_hipotesis` en código)

- Cita al menos una publicación que gana y una que pierde.
- Cada cita lleva un fragmento **literal** del título.
- Si dice que algo gana, tiene que tener ventas visibles; si dice que pierde, no.

## Salida

JSON con `id`, `busquedas`, `tipo` (formato, marca, lenguaje, barrera_situada,
necesidad_latente, sustitucion_funcional), `necesidad`, `oportunidad`, `evidencia`
(`busqueda`, `i`, `vota`, `fragmento`), `rivales` y `como_refutarla`. Ejemplo real en
`data/divergente/hipotesis_piloto.json`.

## Qué no hacer

- No inventar datos que no están en la vista (ventas, opiniones, voltajes).
- No confundir "no vende porque es internacional" con una necesidad: eso ya lo mide
  `chequear_espera`.
