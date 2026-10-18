# `business.exp`

## Purpose and Tools

This package contains research experiments expressed as agent or graph nodes, including `exp_zeta_hero`.
Experiments do not by themselves establish validated product behavior.

## Placement and Boundaries

Keep each experiment in its own package under `src/business/exp/`.
Place experiment node functions and local helpers in that package.
Current workflow functions commonly use the shared `WorkflowState` and workflow decorators; preserve those contracts when extending existing flows.
For Nodezator-facing functionality, add or update the corresponding node definition under `nodes_pack/`.

## Ownership and Acceptance

Treat experiment changes as human-reviewed or hybrid unless a narrower class is established.
Keep evidence, forecasts, recommendations, and outcomes distinguishable where the experiment contract requires it.
Do not present experimental value as established without evaluation.
