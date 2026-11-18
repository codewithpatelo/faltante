---
name: formular_trabajos
description: Paso J de la divergencia. De cada persona ya leída (mapa de empatía chico), formula el trabajo que intenta hacer un nivel por encima del producto y lo que le sale mal, sin nombrar el producto. Es la etapa de resumen orientado al uso de TnT-LLM, con el formato de trabajo y resultado de Ulwick (Jobs-to-be-Done).
toca_datos: true
---

# formular_trabajos

**Pregunta:** ¿qué está tratando de lograr esta persona en su vida, para lo cual compró (o duda
en comprar) este producto, y qué le sale mal?

La gente no quiere el producto: quiere hacer un trabajo. El que compra una cortadora de pelo
quiere "cortarle el pelo a su hijo en casa"; el que compra un bebedero quiere "que el gato tome
agua aunque no esté en casa". Dos personas que compraron cosas distintas pueden estar haciendo el
mismo trabajo, y ahí aparece lo que el mercado no les resuelve.

## Qué escribir de cada persona

- `trabajo`: el trabajo **un nivel por encima del producto**, con el formato verbo + objeto +
  contexto, **sin nombrar el producto ni su categoría**. Bien: "mantener el auto limpio viajando
  con chicos", "cortarle el pelo a un hijo en casa", "entrenar fuerza en un departamento chico".
  Mal: "usar la aspiradora", "afeitarse con la afeitadora", "tener una buena almohada".
  Subí un nivel preguntando "¿para qué lo quiere?" una vez, no más: "dormir sin dolor de cuello"
  sí; "ser feliz" no.
- `le_sale_mal`: lo que le impide hacer bien ese trabajo hoy, también sin nombrar el producto
  ("se le cansa el brazo antes de terminar", "le da miedo lastimarlo", "no sabe si va a entrar en
  el espacio"). Vacío (`""`) si a esta persona no le sale mal nada.

Si la tarjeta no alcanza para saber el trabajo, no la incluyas. No inventes.

## Entrada

Líneas `[id] producto | situación | quiere lograr | dolor | teme | compara con`.

## Salida (JSON)

```json
{"trabajos": [{"id": "E012.o34", "trabajo": "...", "le_sale_mal": "..."}]}
```
