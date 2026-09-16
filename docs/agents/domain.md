# Domain docs

This repository uses a single domain context.

## Before exploring or changing the project

- Read `CONTEXT.md` for the canonical domain language.
- Read every ADR under `docs/adr/` that affects the area being changed.
- If a referenced document does not exist, proceed silently instead of creating speculative documentation.

## Layout

```text
/
├── CONTEXT.md
└── docs/
    └── adr/
```

## Vocabulary

Use the terms defined in `CONTEXT.md` in issue titles, tests, interfaces and documentation. Do not replace them with synonyms that the glossary explicitly avoids.

If a required concept is absent, reconsider whether it belongs to the project. When it represents a real domain gap, resolve it through domain modeling before introducing competing terminology.

## ADR conflicts

Surface any conflict with an accepted ADR explicitly. Do not silently override a recorded decision. Superseded ADRs remain historical context; follow the ADR that supersedes them.
