# Cómo juzgar las hipótesis (10 minutos por persona)

1. Copiá `planilla_juicios.csv` a `juicios_<tu_nombre>.csv` (o abrila en Google Sheets y exportá a CSV con ese nombre).
2. No abras `clave_fuentes.json`: la mitad de los ítems los escribió el LLM y la otra mitad el baseline sin LLM. Se juzga a ciegas.
3. Para entender cada ítem podés mirar la búsqueda: `python scripts/vista_votos.py data/capturas/captura_ml_2026-11-05.json "<búsqueda>"`.
4. Poné un puntaje de 1 a 3 en cada columna y tu nombre en `juez`:
   - **sostenida**: ¿los datos de la búsqueda la respaldan? (1 no, 2 en parte, 3 sí)
   - **no_obvia**: ¿dice algo que no sabías mirando solo el precio? (1 obvia, 3 sorprendente)
   - **accionable**: ¿un importador o vendedor podría hacer algo con esto? (1 no, 3 sí)
5. `make juicios` calcula promedios por fuente (LLM vs baseline) y el acuerdo entre jueces (kappa de Cohen).

Con los juicios humanos después se calibra un LLM juez (clase de IR: kappa contra expertos).

# Etiquetar equivalencias (15 minutos por persona)

1. Copiá `planilla_equivalencia.csv` a `equivalencia_<tu_nombre>.csv`.
2. Para cada fila: ¿la publicación local es **el mismo producto o un reemplazo directo** del
   internacional (mismo tipo, tamaño y gama parecidos)? Escribí `si` o `no` y tu nombre.
3. No abras `clave_equivalencia.json`.
4. `make equivalencia` calcula precisión, recall y F1 del baseline, de la regla y del juicio del LLM
   contra la mayoría de las etiquetas humanas.
