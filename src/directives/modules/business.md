# Business Source Root

## Purpose and Tools

`src/business/` is the Python source root for application and research packages.
The root `pyproject.toml` configures it as the module root; imports use package names such as `import tickster` rather than `import business.tickster`.

## Placement and Boundaries

Place each Python package in its own directory under `src/business/`.
Do not place loose Python modules, documentation, scripts, or configuration directly in the source root.
Put project command scripts in `src/scripts/` and interactive development utilities in `src/devtools/`.

Consult the relevant family specification before changing `tickster`, experiments, Nodezator workflows, or node packs.
Other business packages should follow the applicable package contracts and the shared [Python standards](../standards/python.md).

## Acceptance

New code belongs to an appropriately named package, uses the configured import root, and respects documented dependency direction.
Relevant tests belong under `tests/business/` in a corresponding package path.
