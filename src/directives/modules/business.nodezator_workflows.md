# `business.nodezator_workflows`

## Purpose and Ownership

`src/business/nodezator_workflows/` stores Nodezator workflow documents that compose node-pack definitions into visual flows.
These workflow files are operational business artifacts because they encode executable composition.
Treat them as human-reviewed or hybrid unless maintainers define narrower ownership and review rules.

## Structure and Contracts

Keep workflow documents in this directory and retain the file format expected by the configured Nodezator tooling.
Use node definitions from `nodes_pack/`; do not embed assumptions about a node's implementation where the node contract is the appropriate boundary.
Preserve workflow filenames and paths referenced by commands, users, or other project artifacts.

## Permitted Freedom and Boundaries

Workflow composition may change to support an approved research or development goal.
Coordinate changes with the affected node definitions and experiment functions.
Do not treat timestamped workflow copies as disposable without an explicit maintenance decision.

## Acceptance

The workflow opens in the project's Nodezator environment, references discoverable nodes, and has its intended graph connectivity after the change.
For a workflow edit, record the manual or automated check used to establish this.
