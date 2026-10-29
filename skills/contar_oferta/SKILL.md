---
name: contar_oferta
description: Cuenta cuánta oferta local hay de un producto (publicaciones y vendedores). Falsea hipótesis de AUSENCIA.
toca_datos: true
---

# contar_oferta

**Qué pregunta responde:** ¿este producto ya se vende en Argentina?

**Cuándo usarla:** primero, ante cualquier hipótesis de tipo `ausencia` o `complemento`.
Es la verificación más barata y la que más hipótesis mata.

**Entrada:** `{"producto": str}`

**Salida:** `{"publicaciones": int, "vendedores": int, "fuente": str}`

**Cómo interpretarla:**
- `vendedores >= 15` → hay oferta. Una hipótesis de ausencia queda **refutada**.
- `vendedores` entre 3 y 14 → oferta fina. No refuta; pedir `ratio_precio`.
- `vendedores <= 2` → casi ausente. Apoya la hipótesis, pero sola **no alcanza**: puede ser
  un producto que nadie quiere. Combinar con `persistencia` o `voto_manos`.
