---
name: testing-streamlit-real-cases
description: Exercise the investigation Streamlit adapter against demo and genuine persisted EVTX cases.
---

# Streamlit investigation testing

## Devin Secrets Needed

None for localhost Streamlit, SQLite and Ollama. Remote private endpoints may need separately approved access.

## Setup

- Run `uv sync` from the repository root.
- Use `docs/tracer.md` for the genuine import-and-investigate command. Verify the fixture manifest, Hayabusa executable plus adjacent rules/config, and the configured Ollama model before testing.
- Start demo UI with `env -u INVESTIGACION_DATOS uv run streamlit run src/investigacion/ui/app.py --server.port 8501 --server.headless true`.
- Start persisted UI separately with `INVESTIGACION_DATOS=datos uv run streamlit run src/investigacion/ui/app.py --server.port 8502 --server.headless true`.
- Relative data paths resolve against the server working directory. Merely opening the UI does not perform inference.

## High-signal browser coverage

- The demo should show four events; real fixture counts should be checked against the actual CLI output, not assumed across fixtures.
- Click reference buttons within Hallazgos, not merely chronology buttons. Detail opens as a modal dialog regardless of the active tab; scroll position does not matter.
- The modal blocks interaction until dismissed: use Cerrar, the X, outside click, or Esc before returning to findings.
- Capture original locator, source SHA and Hayabusa versions alongside the selected UID.
- Download both formats through the browser and inspect actual files in `~/Downloads`, checking case IDs, counts and cited UID membership.
- To test case-switch reset adversarially, import the same fixture again through the real CLI. Both cases share event UIDs; an open event must still disappear on selection change. Never fabricate model findings to make the UI look validated.
- Model prose and candidate techniques can vary. Structural validation is not proof that the hypothesis is semantically correct; retain pendiente review state.
- Inspect long raw evidence for Markdown/math interpretation: PowerShell dollar signs may render differently from literal source content.
