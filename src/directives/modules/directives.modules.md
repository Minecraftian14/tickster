# Module Specification Convention

## Purpose and Tools

Use one concise specification per module family when its structure, ownership, tools, or contracts need guidance beyond the repository map.
Every module specification uses these three sections:

- **Purpose and Tools** states the module's role and the relevant language, framework, or configured tools.
- **Placement and Boundaries** states where files belong, required structure or naming, and important module limits.
- **Ownership and Acceptance** states the ownership class when established and the minimum evidence that a change satisfies its contract.

Keep each fact in the section that best fits it.
Include exact filenames, symbols, or loader behavior when another component depends on them.

## Placement and Boundaries

Keep module specs focused on expected contents, placement, conventions, and contracts.
Do not repeat the architecture narrative or rules already owned by `AGENTS.md`, `repository.md`, or another directive; link to the source of truth.
State only module-specific constraints and distinguish observed layout from required structure.

The examples below are illustrative proposals moved from `ownership.md`.
They show the level of detail a module spec can use and do not assign permanent ownership.

### Example: `src/devtools/`

#### Purpose and Tools

Kotlin development utilities using the configured Gradle and Compose structure.

#### Placement and Boundaries

Keep its source and tests in the configured roots.

#### Ownership and Acceptance

Proposed class: human-reviewed or hybrid.
Accept bounded utility or UI changes after relevant Gradle checks and review of developer-facing behavior.

### Example: `src/business/utilities/`

#### Purpose and Tools

Shared Python utility package; detailed responsibilities remain to be specified.

#### Placement and Boundaries

Keep package source within this package and follow its approved public interface.

#### Ownership and Acceptance

Proposed class: AI-assisted, contract-bound once its purpose and interfaces are documented.
Accept internal helper changes against package-level checks while preserving shared semantics and dependencies.

## Ownership and Acceptance

Keep specifications concise and decision-useful.
Prefer precise short statements, one requirement per line, and links over duplicated context.
Do not add an ownership fallback here; the policy in `ownership.md` applies when a module's class is unspecified.
