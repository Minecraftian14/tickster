# Project Scripts

## Purpose and Tools

`src/scripts/` contains project-management and quality-of-life command-line utilities.
The preferred scripting language is XONSH; `run.xsh` reads command definitions from the root `run.json`.

## Placement and Boundaries

Place new project utility scripts in this directory and follow [the XONSH standards](../standards/scripts.md).
Use `src/devtools/` for interactive tools with a UI.
Do not operate on `.env` or the protected paths listed in the repository-wide instructions.

## Acceptance

Document new command behavior in its existing command configuration where appropriate.
Exercise the affected command safely and report validation evidence.
