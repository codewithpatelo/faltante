# Reglas para agentes de código en este repo

- Tests: `make test`. Todo cambio deja los tests en verde.
- No tocar `data/capturas/` ni `data/diagnostico/foto_*`: son datos crudos; se agregan, no se editan.
- No mirar `data/divergente/particion.json["test"]` mientras se itera la skill o el prompt: test se usa una sola vez.
- No abrir `data/evaluacion/clave_fuentes.json` si vas a juzgar.
- Umbrales y rúbricas a la vista (arriba de cada archivo), nunca enterrados en el código.
- Al terminar una sesión: una entrada en `BITACORA.md` (qué probamos, qué esperábamos, qué pasó, qué decidimos).
- Nunca guardar tokens ni claves en el repo; las claves van como variables de entorno o secretos de GitHub.
