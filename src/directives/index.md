# Project Directives Index

The specifications are first-class, version-controlled project artifacts.
The root `AGENTS.md` defines repository-wide agent workflow and boundaries.
This index identifies which detailed directives to consult; it does not duplicate their requirements.

## How to Use This Index

For a substantive change:

1. Identify the affected areas and their ownership.
2. Consult the applicable directives listed below, including the relevant module contract and validation requirements.
3. If a necessary directive is missing, incomplete, or contradictory, report the gap rather than inventing a lasting rule.
4. Update a directive when the intended requirement changes, following the applicable approval process.

Read the full applicable directive, not just its title or this index.

## Directive Catalog

The paths below are the directive catalog.
An existing file is authoritative only for the scope it actually documents; report missing requirements rather than assuming an empty or incomplete file defines them.

| Directive               | Scope                                                                                                                         | Consult when                                                                    |
|-------------------------|-------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `product.md`            | Product purpose, users, goals, non-goals, and product-level principles                                                        | A change affects intended product behavior or scope                             |
| `architecture.md`       | System components, responsibilities, boundaries, and major data flows                                                         | Designing or changing component responsibilities or cross-module behavior       |
| `repository.md`         | Directory map, source roots, permitted artifact locations, and repository layout                                              | Creating, moving, or locating files and modules                                 |
| `ownership.md`          | Human-owned, AI-assisted/contract-bound, AI-regenerable, and human-reviewed areas                                             | Before editing, replacing, or regenerating implementation                       |
| `change-policy.md`      | Approval requirements and process for changes to protected contracts or authoritative directives                              | A change needs authorization or changes a governing requirement                 |
| `dependency-rules.md`   | Permitted dependency direction, import boundaries, and shared-contract rules                                                  | Adding dependencies or changing cross-module relationships                      |
| `standards/python.md`   | Python-specific conventions and tooling expectations                                                                          | Editing Python packages under `src/business/` or Python tooling elsewhere       |
| `standards/frontend.md` | React, JavaScript, and Mantine conventions                                                                                    | Editing `src/frontend/`                                                         |
| `standards/devtools.md` | Kotlin and Composables UI conventions for development tools                                                                   | Editing `src/devtools/`                                                         |
| `standards/scripts.md`  | XONSH conventions for project-management and quality-of-life scripts                                                          | Editing `src/scripts/`                                                          |
| `standards/testing.md`  | Testing strategy, test placement, and expectations for evidence                                                               | Adding or changing tests, or validating a substantive change                    |
| `validation.md`         | Repository checks, contract validators, required commands, and CI expectations                                                | Implementing or changing validation, or preparing a change for review           |
| `modules/`              | Individual module-family specifications: purpose, ownership, structure, contracts, permitted freedom, and acceptance criteria | Creating, modifying, or regenerating a module covered by a module specification |
| `decisions/`            | Accepted architectural decisions and their rationale, consequences, and status                                                | Evaluating a major design choice or understanding why a constraint exists       |

Add a directive when there is a distinct responsibility that needs an authoritative home. Avoid duplicating the same rule across multiple documents;
link to the authoritative directive instead.

## Module Specification Convention

Each convention-bound or otherwise special module family should have a dedicated specification under `modules/`.

The current module specifications are:

- `modules/business.md`, `modules/frontend.md`, `modules/devtools.md`, `modules/scripts.md`, and `modules/directives.md` provide short purpose and placement guides.
- `modules/business.tickster.md`, `modules/business.exp.md`, `modules/business.nodezator_workflows.md`, and `modules/business.nodes_pack.md` define more specific business-family conventions.

Add or refine module specifications as ownership and contracts become clearer.

A module specification should define only what is necessary for reliable implementation and validation:

- Purpose and responsibilities.
- Ownership class and approval requirements.
- Required directory and file structure.
- Required names, symbols, signatures, annotations, registration, discovery, and loading behavior, as applicable.
- Public contracts, dependencies, and behavioral requirements.
- What implementation details AI may choose freely.
- Prohibited changes and known boundaries.
- Acceptance criteria and the checks that verify them.

State exact requirements where the loader or another module depends on them. Keep examples illustrative unless explicitly designated normative.
Do not infer a convention from an example alone.

## Architectural Decisions

Use `decisions/` for decisions whose rationale should remain available over time.
Give each decision a unique, ordered identifier and a descriptive title, for example:

`decisions/ADR_0001_short_title.md`

Record the context, decision, consequences, and status.
When a decision is superseded, update its status and link to the replacement rather than silently rewriting history.
The current architecture and applicable specifications remain the implementation guidance.

## Consistency and Maintenance

- Keep each requirement in one authoritative location wherever practical.
- Link to existing directives rather than copying their content.
- Update this index when a directive is added, renamed, or retired.
- Do not weaken a specification merely to make an implementation pass.
- Keep durable requirements separate from replaceable implementation code where the repository architecture permits.
- Ensure important mechanical rules have automated checks where feasible; prose alone does not enforce repository constraints.

## Repository Boundaries

The repository-wide boundaries and protected paths are defined in the root `AGENTS.md` and the applicable repository and ownership directives.
This index does not grant permission to access or modify any protected path.
