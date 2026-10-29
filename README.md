# Faltante — MVP del harness

Agente que parte de **votos con los pies** (gente que compra afuera, que paga usado a
precio de nuevo, que fabrica adaptadores) y decide qué conviene importar, tratando de
**refutar** cada hipótesis contra datos antes de confirmarla.

> **Estado:** el harness corre y está testeado. Los resultados de `make demo` usan
> **datos sintéticos** (`data/*_sintetico.json`): prueban el mecanismo, no son hallazgos.

## Correrlo

```bash
make setup      # instala dependencias
make test       # tests del harness, sin red ni API key
make demo       # políticas fija y heurística sobre datos sintéticos
make agente     # agente con LLM (requiere ANTHROPIC_API_KEY)
make vivo       # contra la API de Mercado Libre (requiere ML_ACCESS_TOKEN)
```

Con Docker: `docker build -t faltante . && docker run --rm -e ANTHROPIC_API_KEY faltante make agente`

## Cómo está armado

```
pistas (votos con los pies)
   │
   ▼
POLÍTICA ─── decide qué hacer ──►  MOTOR ─── guardrails, caché, traza
(fija | heurística | LLM)            │
                                      ▼
                               SKILLS ──► ADAPTADORES (fixtures | Mercado Libre | …)
```

- **`harness/motor.py`** — ejecuta lo que el agente pide y controla las reglas; no decide.
  Cuatro operaciones: `proponer_hipotesis`, `verificar`, `dar_veredicto`, `leer_skill`.
- **`harness/agente.py`** — el loop ReAct sobre la API de Anthropic, sin framework.
- **`harness/politicas.py`** — los baselines: fija (todas las skills sobre todo) y
  heurística (corta apenas refuta).
- **`skills/*/SKILL.md`** — una por verificación: qué pregunta responde, cuándo usarla,
  cómo interpretar el resultado. El agente las lee con `leer_skill`.
- **`adapters/`** — de dónde salen los datos. Cambiar de fuente no toca el harness.

## Fases

1. **Divergente:** de cada pista, el agente infiere qué producto se demanda y de qué tipo
   es la oportunidad (`ausencia`, `precio`, `complemento`).
2. **Convergente:** corre skills para refutarla, de la más barata a la más cara, y corta
   cuando queda refutada.
3. **Decisión:** `confirmar`, `descartar` o `insuficiente`.

## Guardrails (en código)

- No se puede confirmar ni descartar sin al menos una evidencia **propia, exitosa y que
  haya tocado datos**. Si no se pudo verificar, el veredicto es `insuficiente`.
- Tope de skills por hipótesis y de pasos totales.
- No se puede terminar con pistas sin veredicto.
- Todo rechazo vuelve al agente como error y queda en la traza.

## Salidas (`out/`)

- `<politica>.resumen.json` — accuracy, skills por pista, llamadas a la fuente, costo.
- `<politica>.traza.jsonl` — cada paso: qué se propuso, qué se corrió, qué se rechazó.
- `<politica>.estado.json` — hipótesis, evidencias y veredictos: el expediente.

## Datos: lo que sabemos (29/10/2026)

- La búsqueda de la API de Mercado Libre devuelve **403** sin access token.
- El listado web muestra muro de login a tráfico no autenticado.
- Hace falta registrar una app en developers.mercadolibre.com.ar.

Ver `BITACORA.md` y `DECISIONES.md`.
