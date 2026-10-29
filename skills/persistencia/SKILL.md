---
name: persistencia
description: Revisa si la señal se sostiene en el tiempo o es un pico. Separa ausencia estructural de faltante puntual.
toca_datos: true
---

# persistencia

**Qué pregunta responde:** ¿la demanda viene sosteniéndose o fue una moda de una semana?

**Cuándo usarla:** antes de confirmar cualquier hipótesis. Es la defensa contra el error
más caro del sistema: confundir un faltante puntual con una ausencia estructural.

**Entrada:** `{"producto": str}`

**Salida:** `{"meses_con_senal": int, "de_meses": int, "tendencia": "sube"|"estable"|"baja", "fuente": str}`

**Cómo interpretarla:**
- `meses_con_senal / de_meses < 0.5` → pico. **Refuta** la hipótesis.
- `tendencia == "baja"` → la oportunidad se está cerrando. Bajar prioridad.
- `>= 0.75` y `estable` o `sube` → persistente. Apoya.
