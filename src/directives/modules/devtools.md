# Development Tools

## Purpose and Tools

`src/devtools/` contains developer-sided utilities, including interactive tools and previews.
The root Gradle configuration uses Kotlin with Compose Multiplatform and Composables UI.

## Placement and Boundaries

Keep Kotlin development-tool source under `src/devtools/`.
Use this area for interactive utilities; use `src/scripts/` for XONSH command-line helpers.
Do not add application business logic here solely for convenience.

## Ownership and Acceptance

This file does not assign final ownership; see the provisional example in [ownership.md](../ownership.md).
Changes should preserve the configured Gradle source and test roots and pass applicable validation.
