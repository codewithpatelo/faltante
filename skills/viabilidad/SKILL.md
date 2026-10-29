---
name: viabilidad
description: Chequea barreras para importar (ANMAT, SENASA, homologación, exclusividad de marca). Falsea hipótesis inviables.
toca_datos: true
---

# viabilidad

**Qué pregunta responde:** si el hueco es real, ¿se puede llenar?

**Cuándo usarla:** como último filtro, antes de confirmar. Un hueco que lleva años abierto
puede estar abierto por una razón.

**Entrada:** `{"producto": str}`

**Salida:** `{"barreras": [str], "bloqueante": bool, "fuente": str}`

**Cómo interpretarla:**
- `bloqueante == true` → **refutada** como oportunidad, aunque la demanda sea real.
- Barreras no bloqueantes → confirmar, pero listarlas en el expediente.
