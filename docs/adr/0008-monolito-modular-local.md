---
status: accepted
---

# Entregar un monolito modular local

El MVP se implementará con Python, Streamlit y SQLite, usando Hayabusa para el análisis EVTX y un único runtime Ollama local para inferencia estructurada. Se evita React para reducir procesos, contratos y pasos de despliegue; Streamlit conservará conexiones y recursos entre reruns y el trabajo costoso quedará fuera de la capa de presentación.

## Consequences

Ollama deberá ejecutarse en modo sin cloud y con el modelo precargado antes de la demo. La selección de evidencia limitará el contexto, las inferencias serán seriales y el modelo exacto se elegirá por benchmark en el hardware de presentación, no por reputación general.
