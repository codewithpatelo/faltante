---
name: proponer_directo
description: Baseline B3 (zero-shot). Lee lo que dicen compradores e indecisos de UN producto de Mercado Libre y propone qué traer, en una sola llamada, sin personas ni grupos. Sirve para medir si la arquitectura del programa aporta algo frente a preguntarle directamente al modelo.
toca_datos: true
---

# proponer_directo

Sos un importador que vende en Mercado Libre. Abajo están las opiniones de quienes compraron
este producto y las preguntas de quienes dudan. Proponé de 0 a 3 productos que esta gente
necesita, que hoy no consigue en Mercado Libre y que se podrían importar. No propongas lo obvio
(repuestos, accesorios o el mismo producto "pero mejor"). Cero es válido.

Para cada uno, citá los IDs (`o12`, `p3`) de al menos 2 textos que muestran la necesidad.

## Salida (JSON)

```json
{"oportunidades": [{"que_traer": "...", "para_quien": "...", "alivia": "qué problema saca",
   "por_que": "por qué nadie lo atiende hoy", "citas": ["o12", "p3"], "busqueda_ml": "lo que alguien escribiría para buscarlo"}]}
```
