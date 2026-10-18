# Business Source Root

## Purpose and Tools

`src/business/` is the configured Python module root for application and research packages.
Imports use package names such as `import tickster`, not `import business.tickster`.

## Placement and Boundaries

Do not place Python files directly in `src/business/`.
Place Python source within package directories under this root.
Do not place loose documentation, scripts, or configuration in the root.

See the family specs for `tickster`, experiments, Nodezator workflows, and node packs.

## Ownership and Acceptance

Package changes follow their documented contracts and the shared [Python standards](../standards/python.md).
Place relevant tests under `tests/business/` using the corresponding package path.
