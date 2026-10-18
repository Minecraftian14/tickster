# AGENTS.md — Repository-Wide Instructions

## 1. Authority and Required Workflow

`src/directives/index.md` is the entry point to the authoritative project specifications, architecture, ownership policies, development standards, and module contracts.

Before making a substantive task:

1. Establish the requested outcome and acceptance criteria.
2. Identify affected modules, dependencies, and the ownership class of each affected path.
3. Read the applicable specifications in full, including integration and validation requirements.
4. Make the smallest change that satisfies the requirements and stays within the permitted ownership boundaries.
5. Run the applicable structural, contract, and behavioral checks.
6. Report what changed, what was validated, and any unresolved issues.

A specification reference is not a substitute for reading the specification.
Existing code shows the current implementation; it does not prove that the implementation matches the intended architecture.

Follow explicit repository-wide restrictions and ownership policies.
Module- and language-specific specifications add detail but do not authorize violating those restrictions. If required specifications are missing, incomplete, or contradictory, do not invent a permanent rule, undocumented exception, or unauthorized resolution. Stop the affected work and report the issue when it materially affects implementation. Never change a specification merely to make an implementation appear compliant.

## 2. Repository Layout and Protected Paths

Keep source code and development tooling within their designated `src/` areas.
Do not create additional source roots or move source artifacts outside permitted locations without explicit authorization.
Root-level configuration, repository entry-point documentation, and explicitly permitted metadata may reside outside `src/`;
build and package configuration must remain consistent with these boundaries.

Consult `src/directives/repository.md` for the source map and artifact placement rules.
Use the applicable module specification for module-specific structure and tools.

### Protected paths

The following directories or files are strictly out of bounds:

- `.obsidian/`
- `docs/envault/`
- `.env`

Do not read, modify, create, delete, rename, move, generate, or otherwise operate on these items.
Do not run commands that could affect them, including cleanup, formatting, migration, or generation.
If a task appears to require access to either, stop and report the conflict.

## 3. Ownership and Permitted Changes

Determine ownership before editing. 
Consult the applicable ownership policy in `src/directives/`. 
Unknown ownership is not permission to write; establish the permitted change policy before potentially destructive work.

- **Human-owned modules** (such as designated interfaces, build logic, core business principles, and core business logic): Do not modify, refactor, regenerate, replace, or delete their code without explicit authorization. Do not redefine their public contracts to accommodate downstream code. Adapt the downstream implementation where permitted; report defects or gaps in the contract for a human decision.
- **AI-assisted, contract-bound modules:** Follow the module specification exactly, including required paths, filenames, symbols, signatures, annotations, registration, discovery, and loading conventions. Do not invent alternative layouts or entry points.
- **AI-regenerable modules:** Identify the authoritative purpose specification and public contract before regeneration. Preserve required interfaces, dependencies, behavior, and acceptance criteria. Keep durable requirements and tests separate from replaceable implementation where the architecture permits; regenerate only the intended scope and validate the result.
- **Human-reviewed or hybrid modules:** Make only permitted changes, identify required approvals, and do not bypass review or merge controls. Passing tests does not constitute human approval.

## 4. Implementation and Cross-Module Changes

Prefer established project conventions and existing shared implementations.
Keep changes focused; avoid unnecessary abstractions, dependencies, duplicate implementations, and unrelated refactoring.
Preserve public APIs, module boundaries, dependency direction, runtime behavior, serialization formats, and persistence semantics unless an authorized change explicitly requires otherwise.

Before changing a shared contract or core module, identify downstream dependents, read their specifications, determine permitted coordinated changes, and plan compatibility and validation.
Preserve compatibility unless an authorized breaking change is required.
Do not modify a human-owned or protected dependency merely because it is the easiest way to complete a downstream task.

Inspect relevant code before editing.
Preserve user changes and unrelated work.
Do not delete files because they appear unused, assume unrelated files are disposable, perform broad cleanup or repository-wide reformatting unless requested, or treat generated output as replaceable unless its ownership policy explicitly allows it.
Do not run destructive commands without understanding their scope and obtaining required authorization.
Do not create files outside permitted locations.

Do not fabricate configuration, dependencies, test results, or architectural requirements.
Do not establish new project-wide conventions without documenting them and obtaining the required approval.
Consult the applicable module and language directives for detailed coding standards.

## 5. Specifications, Testing, and Validation

Specifications and implementations are both first-class project artifacts.
When requirements change, update the authoritative specification through its approval process.
If implementation defects expose missing requirements, propose a specification improvement rather than repeatedly regenerating code against an incomplete contract.
Do not weaken requirements to fit an implementation.

Use the repository's documented commands and configuration to run applicable checks.
Depending on the change, these may include:

- Repository structure and protected-path checks.
- Required filenames, symbols, annotations, registration, discovery, and loading checks.
- Formatting, linting, and static analysis.
- Unit, integration, contract, compatibility, and behavioral tests.
- Application builds and package checks.

Do not remove, weaken, or bypass required checks to make a change pass.
If a check cannot be run, state why and identify the remaining verification work.
Report actual results only; do not claim full compliance while applicable specifications or validation remain unresolved.

## 6. Completion Report

For each substantive task, report:

1. **Summary:** What changed and why.
2. **Affected modules:** Which areas were changed.
3. **Ownership and approvals:** Relevant restrictions, reviews, or human decisions.
4. **Validation:** Checks run and their actual results; include checks not run and why.
5. **Limitations:** Unresolved requirements, risks, or remaining work.
6. **Specification changes:** Authoritative directives changed or proposed for change.

Additionally, save these reports as `temp/<timestamp>_<title>.md`. Keep the report concise. Follow `YYYYMMDD_HHMMSS` format for `timestamp` and camel case for `title`.

The goal is not merely working code.
Produce code that fulfills intended requirements, respects human ownership and repository boundaries, conforms to module contracts, and remains maintainable.
When implementation freedom conflicts with an explicit constraint, the constraint takes precedence.
