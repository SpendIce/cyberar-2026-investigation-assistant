# Issue tracker: GitHub

Issues and specs for this repository live in GitHub Issues at `SpendIce/cyberar-2026-investigation-assistant`. Use the `gh` CLI for tracker operations.

## Conventions

- Create an issue with `gh issue create --title "..." --body-file <path>`.
- Read an issue and its discussion with `gh issue view <number> --comments`.
- List issues with `gh issue list`, requesting JSON fields when filtering programmatically.
- Comment with `gh issue comment <number> --body "..."`.
- Apply or remove labels with `gh issue edit`.
- Close completed work with `gh issue close <number> --comment "..."`.
- Infer the repository from the `origin` remote when running inside this checkout.

## Pull requests as a triage surface

**PRs as a request surface: no.**

Pull requests created by implementation work are not treated as incoming feature requests by the triage flow.

## Publishing from skills

- When a skill says "publish to the issue tracker", create a GitHub issue.
- When a skill says "fetch the relevant ticket", read the complete issue body, comments and labels.
- Apply `ready-for-agent` to specs and tickets that are complete enough to implement without further discovery.

## Blocking relationships

Use GitHub native issue dependencies when available. Create blocking edges through the GitHub API using the blocker's numeric database ID, not its issue number or node ID. If native dependencies are unavailable, add a `Blocked by: #<number>` line to the dependent issue.

A ticket is ready to start only when all its blockers are closed.

## Wayfinding

For `/wayfinder`, use one map issue labelled `wayfinder:map` and child issues for decisions. Prefer native sub-issues and dependencies; fall back to task lists and explicit `Part of`/`Blocked by` references when those features are unavailable.
