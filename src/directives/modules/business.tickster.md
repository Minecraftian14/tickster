# `business.tickster`

## Purpose and Ownership

`src/business/tickster/` is the prospective Python server and contains shared workflow support used by parts of the current business implementation.
The server is incomplete and this specification describes its observed role, not a commitment to immediate production use.
Treat this family as human-reviewed or hybrid until maintainers assign a more specific ownership class.

## Structure and Contracts

- Keep server entry points, API support, versioning, models, and workflow support within the `tickster` package.
- API versions are represented by version-named packages under `tickster/api/`; version discovery expects a `routes` module that exports `router`.
- Preserve the existing version discovery and fallback behavior when changing API routing.
- Keep shared workflow state and helpers in `tickster/workflow/`; consumers depend on these interfaces, so inspect them before changing their shape or semantics.

## Permitted Freedom and Boundaries

Implementation details within a documented contract may evolve.
Do not silently redefine a shared workflow contract or change API compatibility behavior to accommodate a downstream caller.
Do not add autonomous trading behavior; recommendations and real-world actions remain subject to human judgment and risk oversight.

## Acceptance

API changes preserve version discovery and route behavior or document an approved compatibility change.
Workflow changes preserve consumers or coordinate their updates.
Run applicable Python tests and report any checks not run.
