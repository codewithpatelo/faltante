PY ?= python3

.PHONY: setup test serendipia serendipia-api todo limpiar

setup:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q tests

# El embudo en dev y test sobre los datos guardados: LLM contra los baselines B1 y B2.
# Escribe data/serendipia/embudo_<particion>.json; el resumen está en OPORTUNIDADES.md.
serendipia:
	$(PY) scripts/serendipia_run.py dev
	$(PY) scripts/serendipia_run.py test

# El paso del LLM hecho por la API sobre test (requiere ANTHROPIC_API_KEY). Las búsquedas
# nuevas que proponga el modelo hay que capturarlas con scripts/captura_ml.js para C4.
serendipia-api:
	$(PY) -m harness.serendipia test
	$(PY) scripts/serendipia_run.py test_api

# Todo lo que corre sin red ni claves.
todo: test serendipia

limpiar:
	rm -rf .pytest_cache __pycache__ */__pycache__
