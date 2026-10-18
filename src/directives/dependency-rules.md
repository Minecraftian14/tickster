# Dependency Rules

## Direction

The current business data layout suggests a staged flow: collection produces observations, foundation provides shared canonical records and persistence/query behavior, enrichment derives research features, and representation renders or serializes results.
Treat this as a useful current boundary, not a finalized architecture; a change that crosses these packages should document the reason and keep the dependency narrow.

Within `src/business/`, import packages by their top-level module name from the configured `src/business` source root.
Prefer a package's documented public interface over imports from unrelated internal modules.
Local relative imports within a package are acceptable where they match established package conventions.

Frontend code may call application-facing interfaces, but business packages should not depend on frontend implementation details.
Development tools and scripts may orchestrate project commands, but application code should not depend on developer-only tools.
Directives describe contracts; implementation modules should not require runtime imports from the directives tree.

## Shared Contracts

Treat shared models, workflow state, serialization behavior, and provider boundaries as contracts when multiple packages depend on them.
Before changing one, inspect consumers and preserve compatibility unless an explicitly reviewed change requires otherwise.
Prefer adapting the downstream consumer over changing a human-owned shared contract.

Provider-specific integrations should remain at their integration boundary where practical.
Avoid adding a new dependency or reversing an existing dependency direction without recording the need in the affected module specification or review.

## POC Status

The repository is in a POC stage, and its package boundaries may evolve.
These rules favor clear dependencies and compatibility without freezing the current structure; document and review justified boundary changes rather than treating observed imports as permanent policy.
