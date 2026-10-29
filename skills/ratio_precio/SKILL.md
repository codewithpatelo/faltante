---
name: ratio_precio
description: Compara el precio local contra el del exterior. Falsea hipótesis de PRECIO y mide el sobreprecio que paga la gente.
toca_datos: true
---

# ratio_precio

**Qué pregunta responde:** ¿cuánto más paga la gente en Argentina que afuera?

**Cuándo usarla:** ante hipótesis de tipo `precio`, o cuando `contar_oferta` dio oferta fina.

**Entrada:** `{"producto": str}`

**Salida:** `{"precio_local_usd": float|null, "precio_exterior_usd": float, "ratio": float|null, "fuente": str}`

**Cómo interpretarla:**
- `ratio < 1.3` → no hay arbitraje que justifique importar. Hipótesis de precio **refutada**.
- `ratio >= 1.8` con oferta → voto de precio fuerte: la gente paga mucho más y compra igual.
- `ratio` nulo → no hay precio local: es ausencia, no arbitraje. Reclasificar.
