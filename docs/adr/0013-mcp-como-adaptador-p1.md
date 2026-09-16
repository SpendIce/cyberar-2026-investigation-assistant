---
status: accepted
---

# Incorporar MCP solo como adaptador P1

MCP no reemplazará la interfaz Streamlit ni formará parte del camino crítico, porque un servidor MCP todavía requiere un host y no ofrece por sí mismo la visualización necesaria para investigar evidencia. Después de verificar completamente el P0, podrá agregarse un adaptador MCP del módulo de investigación para exponer casos, eventos, hallazgos, análisis y exportación a asistentes institucionales autorizados.

## Consequences

La lógica de Hayabusa, inferencia, validación y persistencia permanecerá fuera del adaptador. La superficie MCP no aceptará rutas arbitrarias, shell, SQL ni acceso irrestricto a EVTX; un host externo tampoco deberá convertirse accidentalmente en destinatario de evidencia sensible.
