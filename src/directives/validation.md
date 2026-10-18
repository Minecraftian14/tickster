# Validation

This is a starter checklist; module specifications may add required checks.
No CI expectation is established here until repository CI configuration defines one.

For a change, run the applicable command already defined by the root configuration:

- Frontend: `npm run lint` and, when build behavior is affected, `npm run build`.
- Python: `uv run pytest` for relevant tests under `tests/business/`.
- Kotlin devtools: use the configured Gradle build or test task when that area changes.
- XONSH scripts: exercise the affected command with safe, representative arguments.

For Nodezator node-pack changes, verify the required node definition layout and `main_callable` contract in [the node-pack specification](modules/business.nodes_pack.md).

Report commands that were not run and why.
