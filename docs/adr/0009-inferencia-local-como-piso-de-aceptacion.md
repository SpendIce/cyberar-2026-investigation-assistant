---
status: superseded by ADR-0011
---

# Exigir inferencia funcional en la notebook de la demo

El MVP deberá completar su inferencia en la notebook de presentación, actualmente un equipo CPU-only con 15 GiB de RAM. Un Ollama operado por el equipo en una máquina remota podrá usarse para desarrollo, comparación o aceleración mediante un túnel cifrado, pero no será dependencia de la demostración ni justificará afirmar funcionamiento desconectado.

## Consequences

El endpoint de Ollama será configurable sin introducir un segundo runtime. La selección del modelo priorizará cumplimiento del esquema, citas y abstención antes que tamaño; si la inferencia no está disponible, la cronología y evidencia permanecerán utilizables.
