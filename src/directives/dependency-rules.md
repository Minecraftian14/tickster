# Dependency Rules

Use the component boundaries in [architecture.md](architecture.md) and the package contracts in the applicable module specs.
Within `src/business/`, import packages by their top-level name from the configured module root.

Before changing a shared contract, inspect its consumers and preserve compatibility unless the change is approved.
The current package boundaries are provisional and may evolve with the POC.
