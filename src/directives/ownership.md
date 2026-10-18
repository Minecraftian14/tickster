# Ownership Policy

## Ownership Classes

Ownership describes who may change an area and what review a change needs.
It is independent of whether AI tools assist with the work.

- **Human-owned:** Humans control the implementation and public contract. AI may inspect and propose changes, but must not edit, regenerate, or replace the area without explicit authorization from its maintainer.
- **AI-assisted, contract-bound:** AI may implement within an approved specification. Required paths, interfaces, behavior, and checks are fixed by the contract; changes to that contract require review.
- **AI-regenerable:** AI may replace the designated implementation from an authoritative purpose and contract specification. Durable requirements and acceptance checks remain separate where practical.
- **Human-reviewed or hybrid:** AI may make permitted changes, but a human reviews the result before integration. Human-owned portions within the area remain protected.

## Classification and Precedence

The applicable module specification should state the ownership class and any narrower boundaries.
An explicit protected path or human-owned contract takes precedence over a broader area classification.
If ownership is not documented, treat it as unresolved and do not make potentially destructive changes until the maintainer clarifies it.

Ownership classifications can be changed through the process in [change-policy.md](change-policy.md).
Do not infer that a module is AI-regenerable merely because it has tests or an existing implementation.

## Illustrative Examples

These examples demonstrate how to document ownership and are provisional proposals for maintainer revision.
They do not assign permanent ownership to either area.

### `src/devtools/` — Illustrative Human-Reviewed or Hybrid Example

- **Purpose:** Kotlin utilities used by project developers.
- **Proposed class:** Human-reviewed or hybrid.
- **Freedom:** AI may implement bounded UI or utility changes that preserve the configured Gradle and Compose structure.
- **Review boundary:** A maintainer reviews user-facing behavior, shared build configuration, and changes that affect developer workflows.
- **Acceptance evidence:** Relevant Gradle compilation or tests, plus human review of the resulting behavior.

### `src/business/utilities/` — Illustrative AI-Assisted, Contract-Bound Example

- **Purpose:** Shared Python utility package; its detailed responsibilities are not yet specified.
- **Proposed class:** AI-assisted, contract-bound after its public purpose and interfaces are documented.
- **Freedom:** AI may implement internal helpers within an approved package contract.
- **Review boundary:** Public interfaces, shared semantics, and dependencies used by multiple modules require maintainer review.
- **Acceptance evidence:** Package-level tests and checks required by the future module specification.

Revise these examples to match the team's actual ownership decisions before relying on them for implementation authorization.
