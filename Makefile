PY ?= python3

.PHONY: setup test demo agente diagnostico foto reporte todo prueba-api vivo limpiar

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

# Convierte una captura hecha con scripts/captura_ml.js en una foto para el diagnóstico.
#   make foto CAPTURA=~/Downloads/captura_ml_2026-11-05.json
foto:
	@test -n "$(CAPTURA)" || (echo "Uso: make foto CAPTURA=ruta/a/captura_ml_<fecha>.json  (ver scripts/captura_ml.js)"; exit 1)
	$(PY) scripts/emparejar.py $(CAPTURA)

reporte:
	$(PY) reporte.py

# Todo lo que corre sin red ni claves.
todo: test demo diagnostico

# Prueba la API de Mercado Libre con tu propia app (pide Client ID y Secret, no los guarda).
prueba-api:
	$(PY) scripts/prueba_ml.py

# Harness contra la API de Mercado Libre. Requiere ML_ACCESS_TOKEN (ver make prueba-api).
vivo:
	$(PY) run.py --politica heuristica --fuente ml --salida out_ml

limpiar:
	rm -rf out out_ml .pytest_cache
