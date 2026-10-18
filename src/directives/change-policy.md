# Change Policy

## Routine Changes

Changes within a documented AI-assisted or AI-regenerable area may proceed when they satisfy the current specification and acceptance checks.
Keep changes focused and record the actual validation performed.
Human-reviewed areas require maintainer review before integration, as stated by their module specification.

## Protected Contracts

Obtain explicit maintainer authorization before changing a human-owned implementation or its public contract.
For shared contracts, identify downstream dependents, describe compatibility effects, and coordinate any required updates before implementation.
Do not adapt a downstream module by silently weakening or redefining a protected upstream contract.

## Authoritative Directives

Directive edits are welcome as part of normal project development.
Changes that alter requirements, ownership, module contracts, dependency direction, or validation expectations should explain the reason and affected areas in the change description and receive maintainer review before integration.
Editorial fixes that do not change meaning may follow the ordinary review process without special authorization.

Never change a directive merely to make existing code appear compliant.
When requirements are missing or contradictory, document the gap and request a maintainer decision before encoding a lasting rule.

## Review Record

For a protected-contract or directive change, include the affected contract, compatibility considerations, and validation evidence in the review description.
Record durable architectural choices in `decisions/` where their rationale will matter to future work.
