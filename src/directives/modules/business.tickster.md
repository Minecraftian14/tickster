# `business.tickster`

## Purpose and Tools

The package contains the prospective Python server and shared workflow support.
The server is incomplete; its current implementation does not establish a complete service architecture.

## Placement and Boundaries

Keep server entry points, API support, versioning, models, and workflow support in the `tickster` package.
API version discovery expects version-named packages under `tickster/api/` with a `routes` module that exports `router`.
Preserve the current version discovery and route fallback behavior when changing API routing.
Keep shared workflow state and helpers under `tickster/workflow/`; inspect their consumers before changing the contract.

## Ownership and Acceptance

Treat this family as human-reviewed or hybrid.
API changes preserve version discovery and route behavior or document an approved compatibility change.
Workflow changes preserve consumers or coordinate their updates.
