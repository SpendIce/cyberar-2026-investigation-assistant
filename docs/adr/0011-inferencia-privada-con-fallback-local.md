---
status: accepted
---

# Preferir inferencia privada remota con fallback local

El despliegue preferirá un Ollama más capaz en un nodo privado administrado por el equipo o la institución, accedido mediante un túnel cifrado y sin exponer su API públicamente. La notebook conservará un modelo reducido capaz de producir inferencia real si falla la conexión; si ambos modelos no están disponibles, el sistema continuará en modo degradado con Hayabusa, cronología y evidencia, sin fingir nuevas conclusiones de IA.

## Consequences

La aplicación usará el mismo contrato de Ollama con un endpoint configurable y registrará modelo, modalidad, versión, latencia y hash del contexto. Solo enviará evidencia seleccionada al nodo remoto; la condición de infraestructura propia deberá confirmarse con la organización antes de presentarla como cumplimiento de las bases.
