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

# Igual, pero las propuestas las hace DeepSeek por la API (requiere DEEPSEEK_API_KEY): lee a cada
# persona (mapa de empatía), agrupa a la gente en segmentos y propone qué traer a cada segmento.
# PARTICION: escala_dev o escala_test. Las búsquedas nuevas que proponga el modelo hay que
# capturarlas con scripts/captura_ml.js para C4 y C5, y volver a correr harness.correr.
PARTICION ?= escala_dev
serendipia-api:
	$(PY) -m harness.divergente $(PARTICION)
	$(PY) -m harness.correr $(PARTICION)_api

# Todo lo que corre sin red ni claves.
todo: test serendipia

limpiar:
	rm -rf .pytest_cache __pycache__ */__pycache__
