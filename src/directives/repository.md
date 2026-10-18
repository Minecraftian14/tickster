# Repository Layout

## Repository Model

This repository hosts related sub-projects that share root-level configuration.
The `src/` directory is the source tree; each first-level directory is a distinct responsibility area, not an independent repository.

## Source Areas

- `src/business/` — Python source root. Place Python packages here, not loose modules directly in this directory. Imports use package names such as `import tickster...`, with `src/business` supplied as the package root.
- `src/frontend/` — React JavaScript application using Mantine, Vite, and the root npm configuration.
- `src/devtools/` — Kotlin development tools using Compose Multiplatform and Composables UI. Gradle maps this source directory explicitly.
- `src/scripts/` — XONSH project utilities invoked through the root command setup.
- `src/directives/` — authoritative Markdown specifications and development context.

Tests live under `tests/`. Python tests are organized under `tests/business/` by package; Kotlin test sources are configured under `tests/devtools/`.

## Artifact Placement

Keep source and tooling in their designated `src/` area.
Keep build and package configuration at the repository root where the existing toolchains expect it.
Place authoritative specifications in `src/directives/`, tests in `tests/`, and concise task reports in `temp/` as required by `AGENTS.md`.

Do not place loose documentation, scripts, or configuration directly in `src/business/`.
Use `src/devtools/` for interactive development utilities and `src/scripts/` for XONSH command-line utilities.

The repository also has a `docs/` area, but its contents are outside the scope of this directive.
Protected paths and prohibited operations are defined by the root `AGENTS.md` and must be respected without exception.

## Shared Configuration and Commands

The root `pyproject.toml` configures Python packaging with `src/business` as the module root and pytest discovery under `tests/business`.
The root `package.json` defines frontend development, build, lint, and preview commands.
The Gradle build maps Kotlin sources to `src/devtools` and tests to `tests/devtools`.
The root `run.json` and `src/scripts/run.xsh` provide project-level command aliases.

Treat this map as descriptive of the current configuration.
Before adding a new artifact location or source root, update the appropriate directive and build configuration through the normal review process.
