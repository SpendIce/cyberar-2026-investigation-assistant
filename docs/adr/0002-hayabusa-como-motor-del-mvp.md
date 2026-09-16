---
status: accepted
---

# Usar Hayabusa como motor defensivo del MVP

El MVP analizará evidencia Windows exportada mediante Hayabusa, en coherencia con su usuario primario: un investigador de incidentes. Wazuh queda como futura integración con operaciones continuas y Atomic Red Team como futura fuente de emulación controlada para validar cobertura; ninguna de esas extensiones forma parte obligatoria del producto de 48 horas.

## Consequences

El producto debe diferenciar los mapeos ATT&CK heredados de reglas Hayabusa de las hipótesis nuevas del modelo. La aplicación conservará el EVTX original y referencias inequívocas a sus eventos en lugar de tratar la cronología derivada como evidencia suficiente.
