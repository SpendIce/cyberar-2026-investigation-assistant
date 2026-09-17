# RESPALDO DE PRESENTACIÓN — corrida guardada

Este directorio contiene una **ejecución anterior guardada** del caso
sospechoso (fixture DeepBlueCLI PsExec/PowerShell). No es una ejecución en
vivo: se muestra únicamente como respaldo si la inferencia falla durante la
exposición (ADR-0017, issue #12).

- `datos/casos.sqlite` — caso `7afe62aa3c2b46d6848a1197eb2545eb`
  persistido: importación real por Hayabusa 4.1.0, inferencia real con
  `qwen2.5:7b-instruct` (modalidad `modelo_local`), validación y cadena de
  custodia de 2 escrituras.
- `informe.md` — exportación Markdown de ese caso, con la sección
  Integridad (sello de custodia de la cabeza).
- `informe.md.sha256` — sello del artefacto; verificable con
  `python -m investigacion.informe --verificar docs/demo/respaldo/informe.md`.
- `datos/evidencia/` — original EVTX conservado y salida cruda de Hayabusa.

Regeneración: ver `docs/demo/preparacion.md`, sección "Respaldo".
