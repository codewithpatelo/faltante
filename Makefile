PY ?= python3

.PHONY: setup test demo agente vivo reporte limpiar

setup:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q tests

demo:
	$(PY) run.py --politica fija
	$(PY) run.py --politica heuristica
	$(PY) reporte.py

agente:
	$(PY) run.py --politica react_llm
	$(PY) reporte.py

vivo:
	$(PY) run.py --politica heuristica --fuente ml --salida out_ml

reporte:
	$(PY) reporte.py

limpiar:
	rm -rf out out_ml .pytest_cache
