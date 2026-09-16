# Agent instructions

## Commands

```bash
uv sync          # instala dependencias y el paquete local
uv run investigacion   # ejecuta la aplicación mínima
uv run pytest    # ejecuta la suite de pruebas
uv run mypy src  # verifica los tipos
```

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

The tracker uses the canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context project. Read `CONTEXT.md` and relevant ADRs under `docs/adr/`. See `docs/agents/domain.md`.
