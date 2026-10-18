# Repository Layout

## Source Roots

The sub-project responsibilities and tools are defined in [architecture.md](architecture.md) and the applicable [module specifications](modules/).
This file records source roots and artifact locations.

| Path              | Layout and configuration                                                                                                             |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `src/business/`   | Python module root configured by `pyproject.toml`; packages are imported by their package name. See [business](modules/business.md). |
| `src/frontend/`   | Frontend source directory configured by the root npm/Vite setup. See [frontend](modules/frontend.md).                                |
| `src/devtools/`   | Kotlin source directory configured by Gradle. See [devtools](modules/devtools.md).                                                   |
| `src/scripts/`    | Project script directory. See [scripts](modules/scripts.md).                                                                         |
| `src/directives/` | Authoritative specifications. See [directives](modules/directives.md).                                                               |

## Artifact Locations

Keep source in its designated `src/` area and shared build/package configuration at the repository root.
Place tests under `tests/`; Python tests follow package paths under `tests/business/`, and Gradle maps Kotlin tests to `tests/devtools/`.
Place task reports under `temp/` as required by `AGENTS.md`.

The root project configuration owns the build and command mappings.
Update it when an approved change introduces or relocates a source root.
Protected paths and prohibited operations are defined in `AGENTS.md`.
