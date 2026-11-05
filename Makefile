PY ?= python3

.PHONY: setup test demo agente diagnostico divergente juicios cross-border equivalencia foto reporte todo prueba-api vivo limpiar

setup:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q tests

# Políticas fija y heurística sobre datos sintéticos (prueban el mecanismo, no son hallazgos).
demo:
	$(PY) run.py --politica fija
	$(PY) run.py --politica heuristica
	$(PY) reporte.py

# Agente ReAct con LLM sobre los mismos datos sintéticos. Requiere ANTHROPIC_API_KEY.
agente:
	$(PY) run.py --politica react_llm
	$(PY) reporte.py

# Diagnóstico sobre datos reales de Mercado Libre. Sin FOTO usa la más reciente.
diagnostico:
	$(PY) diagnostico_run.py $(FOTO)

# Etapa divergente (piloto): vista de votos de las búsquedas de desarrollo, guardrail sobre
# las hipótesis y chequeos convergentes de H1 y H2.
CAPTURA_DIV ?= data/capturas/captura_ml_2026-11-05.json
divergente:
	@mkdir -p out
	$(PY) scripts/vista_votos.py $(CAPTURA_DIV) --dev > out/vista_dev.txt
	$(PY) scripts/validar_hipotesis.py data/divergente/hipotesis_piloto.json
	$(PY) scripts/convergencia_piloto.py > /dev/null && echo "convergencia -> data/divergente/convergencia_piloto.json"

# Compra Internacional que vende: ¿hay equivalente con stock local? (baseline, regla y juicio LLM)
cross-border:
	$(PY) scripts/cross_border_run.py data/capturas/captura_ml_locales_cross_border_2026-11-05.json

# Precisión/recall/F1 del emparejamiento contra etiquetas humanas.
equivalencia:
	$(PY) scripts/calcular_equivalencia.py

# Resultados de la evaluación humana (ver data/evaluacion/COMO_JUZGAR.md).
juicios:
	$(PY) scripts/calcular_juicios.py

# Etapa divergente con LLM sobre test (requiere ANTHROPIC_API_KEY).
divergente-llm:
	$(PY) -m harness.divergente $(CAPTURA_DIV) --test

# Convierte una captura hecha con scripts/captura_ml.js en una foto para el diagnóstico.
#   make foto CAPTURA=~/Downloads/captura_ml_2026-11-05.json
foto:
	@test -n "$(CAPTURA)" || (echo "Uso: make foto CAPTURA=ruta/a/captura_ml_<fecha>.json  (ver scripts/captura_ml.js)"; exit 1)
	$(PY) scripts/emparejar.py $(CAPTURA)

reporte:
	$(PY) reporte.py

# Todo lo que corre sin red ni claves.
todo: test demo diagnostico divergente cross-border

# Prueba la API de Mercado Libre con tu propia app (pide Client ID y Secret, no los guarda).
prueba-api:
	$(PY) scripts/prueba_ml.py

# Harness contra la API de Mercado Libre. Requiere ML_ACCESS_TOKEN (ver make prueba-api).
vivo:
	$(PY) run.py --politica heuristica --fuente ml --salida out_ml

limpiar:
	rm -rf out out_ml .pytest_cache
