# Reglas para agentes de código en este repo

- Tests: `make test`. Todo cambio deja los tests en verde.
- Un solo programa. Se itera el que hay; no se agrega otro al lado ni se duplica código. Lo
  que queda superado se borra (queda en el historial de git) y se cuenta en `BITACORA.md`.
- Documentación: cada dato vive en un solo lugar y describe el estado actual. Al cambiar algo
  se reescribe la sección afectada; no se agregan parches ni párrafos al final, y no se
  pierde información vigente.
- No tocar `data/capturas/` ni `data/voces/`: son datos crudos; se agregan, no se editan.
- No mirar los productos de test (`data/voces/productos_2026-11-05.json`, `"particion": "test"`)
  mientras se iteran el skill, los criterios o los umbrales: test se corre una sola vez.
- Umbrales a la vista (arriba de cada archivo), nunca enterrados en el código.
- Al terminar una sesión: una entrada en `BITACORA.md` (qué probamos, qué esperábamos, qué
  pasó, qué decidimos). La bitácora es el único documento que crece por agregado.
- Nunca guardar tokens ni claves en el repo; van como variables de entorno o secretos de GitHub.
