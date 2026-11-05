PY ?= python3

.PHONY: setup test serendipia serendipia-api todo limpiar

setup:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q tests

# Pasa por el embudo las propuestas del LLM y de los baselines, en dev y en test.
# Escribe data/serendipia/embudo_<particion>.json; el resumen para leer está en OPORTUNIDADES.md.
serendipia:
	$(PY) -m harness.correr dev
	$(PY) -m harness.correr test

# Igual, pero las propuestas del LLM las hace la API sobre test (requiere ANTHROPIC_API_KEY).
# Si el modelo propone búsquedas nuevas, hay que capturarlas con scripts/captura_ml.js para C4.
serendipia-api:
	$(PY) -m harness.divergente test
	$(PY) -m harness.correr test_api

# Todo lo que corre sin red ni claves.
todo: test serendipia

limpiar:
	rm -rf .pytest_cache __pycache__ */__pycache__
