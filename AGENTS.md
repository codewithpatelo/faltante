# Reglas para agentes de código en este repo

- Tests: `make test`. Todo cambio deja los tests en verde.
- Un solo programa. Se itera el que hay; no se agrega otro al lado ni se duplica código. Lo
  que queda superado se borra (queda en el historial de git) y se cuenta en `BITACORA.md`.
- Documentación: cada dato vive en un solo lugar y describe el estado actual. Al cambiar algo
  se reescribe la sección afectada; no se agregan parches ni párrafos al final, y no se
  pierde información vigente.
- No tocar `data/capturas/` ni `data/voces/`: son datos crudos; se agregan, no se editan.
- No mirar los productos de test (`"particion": "escala_test"` en `data/escala/corpus_*.json`)
  mientras se iteran los skills, los criterios o los umbrales: test se corre una sola vez, con un
  prerregistro escrito antes (`data/evaluacion/test/`).
- Ninguna prueba trivial. Toda verificación tiene que poder fallar y se compara con la regla tonta
  (responder siempre lo mismo, o el azar): si no le gana, no prueba nada y se dice. Una muestra
  para juzgar (humana o de un LLM) se arma con casos dudosos y las dos respuestas posibles, no al
  azar sobre lo que ya decidió el juez.
- Umbrales a la vista (arriba de cada archivo), nunca enterrados en el código.
- Al terminar una sesión: una entrada en `BITACORA.md` (qué probamos, qué esperábamos, qué
  pasó, qué decidimos). La bitácora es el único documento que crece por agregado.
- Nunca guardar tokens ni claves en el repo; van como variables de entorno o secretos de GitHub.
