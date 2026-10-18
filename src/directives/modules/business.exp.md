# `business.exp`

## Purpose and Ownership

`src/business/exp/` contains experiments that express agent or graph nodes, including the current `exp_zeta_hero` experiment.
Experiments are research implementations and do not by themselves establish validated product behavior.
Treat changes as human-reviewed or hybrid until a narrower ownership class is documented.

## Structure and Contracts

Keep each experiment in its own package under `exp/`.
Place experiment node functions and local helpers in that experiment package.
Current workflow functions commonly accept and return the shared `WorkflowState` and use the workflow decorators; preserve those shared contracts when extending existing flows.

For a node intended to appear in Nodezator, add or update its corresponding node definition under `nodes_pack/` as specified by [the node-pack contract](business.nodes_pack.md).
An experiment function is not automatically a Nodezator node.

## Permitted Freedom and Boundaries

Experiment-specific prompts, analysis methods, and graph composition may vary within the approved research scope.
Keep evidence, forecasts, recommendations, and outcomes distinguishable where the experiment contract requires it.
Do not represent an experiment as proven investment value without appropriate evaluation.

## Acceptance

Experiment functions use the expected state and graph contracts, remain importable from the configured business root, and have relevant behavior checks where tests exist.
Nodezator-facing functionality also satisfies the node-pack specification.
