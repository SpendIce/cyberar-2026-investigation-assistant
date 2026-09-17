---
name: testing-persisted-investigation-exports
description: Exercise the investigation CLI and Streamlit downloads against isolated persisted cases without requiring live inference.
---

# Persisted export runtime testing

## Devin Secrets Needed
None for local controlled-adapter cases. Live inference and ingestion are separate coverage.

## Setup
- Run `uv sync` at the repository root.
- Use an isolated temporary directory, not the user's evidence store.
- Construct and investigate cases with `EvidenciaControlada`, `InferenciaControlada`, `ModuloDeInvestigacion`, and `RepositorioSQLite(<directory>/casos.sqlite)`. See `investigacion.sembrado` for valid event/proposal constructors.
- Include a valid proposal and a proposal referencing a nonexistent event to exercise warnings without losing validated findings.
- Start `INVESTIGACION_DATOS=<directory> uv run streamlit run src/investigacion/ui/app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false`.
- Without INVESTIGACION_DATOS, the UI uses an in-memory seeded case instead of the persisted database. Explicitly label controlled data in testing evidence; do not infer real ingestion merely from the persisted-mode UI banner.

## Runtime checks
- Export through `uv run python -m investigacion.informe --datos <directory> --caso <id> --formato markdown|json --salida <file>`.
- Compare repeated exports byte-for-byte; compare stdout without --salida to file output.
- Check nonexistent IDs and ambiguous multi-case repositories yield exit 1 and actionable stderr.
- In Streamlit use the persisted-case selector, then scroll to Exportación (browser Find can navigate there).
- Click each download button; inspect actual browser-downloaded files and compare them with CLI exports, not only the displayed preview.
- Capture the Markdown preview with each finding's link reason and warning heading visible. The JSON represents warnings through the `errores` key, not a Markdown heading.
- Record only the browser flow, keeping CLI evidence as command logs.
