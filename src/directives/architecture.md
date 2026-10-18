# Architecture

## System Shape

Tickster is a polyglot research application organized as one repository with several related sub-projects under `src/`.
The root project configuration supplies shared dependency, build, and command entry points.

The product goal is an experimental investment-intelligence laboratory, as defined in [product.md](product.md).
The system should preserve traceability from collected evidence through analysis and recommendations to outcomes, while keeping real-world actions under human judgment and risk oversight.

## Components and Responsibilities

- **Business (`src/business/`)** contains Python packages for research data, workflows, integrations, and the evolving application server.
- **Frontend (`src/frontend/`)** contains the React user interface, built with Mantine and Vite.
- **Devtools (`src/devtools/`)** contains Kotlin development utilities built with Compose Multiplatform and Composables UI.
- **Scripts (`src/scripts/`)** contains XONSH project-management and quality-of-life commands.
- **Directives (`src/directives/`)** contains authoritative product, architecture, ownership, module, and development specifications.

Within the business area, the observed data path is divided among collection, foundation, enrichment, and representation packages.
Experiments consume research data and express agent or graph logic; Nodezator workflows and node packs provide a visual workflow representation and executable node definitions.
The current divisions are a POC-era layout and may change as requirements become clearer.

The `tickster` package contains the prospective server and shared workflow utilities.
Its versioning code discovers API version packages and can chain version routers for fallback behavior when an endpoint is unavailable in a requested version.
The server is currently incomplete; do not infer a complete service architecture from its presence.

## Boundaries and Data Flow

Keep collection, canonical data management, enrichment, presentation, orchestration, and UI concerns in their appropriate packages.
Use existing package contracts to pass data between stages; avoid coupling a collector or UI directly to unrelated internal implementation details.

Agent workflows and Nodezator workflows are related representations, not interchangeable execution systems.
LangGraph-style experiment functions may have Nodezator node definitions that call them, but graph functions do not automatically satisfy Nodezator's discovery contract.

External market, language-model, and tunnel providers are integration edges.
Keep provider-specific behavior at those edges where practical, and do not allow an experiment to trigger autonomous trading or bypass human oversight.

## Evolution

Treat these component relationships as a map of the current repository and intended direction, not a frozen design.
For cross-module changes, consult [dependency-rules.md](dependency-rules.md), the affected [module specifications](modules/), and the applicable ownership policy.
Record major durable architectural choices under `decisions/`.
