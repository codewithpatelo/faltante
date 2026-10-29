---
name: voto_manos
description: Busca menciones textuales del producto (reseñas, preguntas, foros). Cruza el voto con los pies con el voto con las manos.
toca_datos: true
---

# voto_manos

**Qué pregunta responde:** ¿la gente además lo *dice*?

**Cuándo usarla:** para ubicar la hipótesis en el cuadrante pies × manos.
No es obligatoria: un hueco con pies y sin manos es **demanda silenciosa**, el caso más valioso.

**Entrada:** `{"producto": str}`

**Salida:** `{"menciones": int, "ejemplos": [{"texto": str, "fuente": str}], "fuente": str}`

**Cómo interpretarla:**
- `menciones == 0` con pies fuertes → demanda silenciosa. Apoya, no refuta.
- `menciones > 0` → citar al menos un ejemplo literal en el expediente.
- Muchas menciones y pies débiles → queja sin disposición a pagar. **Trampa**: no confirmar
  solo con esto.
