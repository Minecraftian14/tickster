# Ownership Policy

## Ownership Classes

- **Human-owned:** AI may inspect and propose changes, but requires explicit maintainer authorization to change the implementation or its public contract.
- **AI-assisted, contract-bound:** AI may implement within the documented contract; contract changes require review.
- **AI-regenerable:** AI may replace the designated implementation from its authoritative specification while preserving its contracts and acceptance criteria.
- **Human-reviewed or hybrid:** AI may make permitted changes, with human review before integration.

## Unspecified Ownership

The applicable module specification should state ownership when it is established.
If it is unspecified, treat ownership as unresolved and do not make potentially destructive changes until the maintainer clarifies it.
An explicit protected path or human-owned contract takes precedence over a broader classification.

Use [change-policy.md](change-policy.md) for approval requirements.
