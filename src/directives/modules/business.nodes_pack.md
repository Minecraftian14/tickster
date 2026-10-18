# `business.nodes_pack`

## Purpose and Ownership

`src/business/nodes_pack/` contains Nodezator node packs: collections of node definitions that expose functions and data to visual workflows.
Python files directly in `nodes_pack/` support node workflow execution and are not individual node definitions.
Treat node definitions as AI-assisted, contract-bound; treat shared graph/runtime support as human-reviewed or hybrid until separately classified.

## Required Structure and Discovery Contract

Each node pack is a package directory under `nodes_pack/`, such as `basic_elements/` or `exp_zeta_hero/`.
Each individual node definition is a directory inside a pack and must contain `__main__.py`.
That file defines the callable function exposed to Nodezator and binds the public entry point with `main_callable = function_name`.

The node-definition folder name and callable name should match by default so the displayed node name is predictable.
If a node intentionally differs, document the reason and verify the name displayed by Nodezator.
These paths and symbols are loader-sensitive; missing `__main__.py` or `main_callable` can prevent discovery or startup.

Pack-level shared helpers may live in Python files directly under the pack directory.
Shared node execution support may live directly under `nodes_pack/`; do not create additional node definitions at that level unless they follow the required folder contract.

## Contracts and Permitted Freedom

Node entry points should expose inputs and outputs through the callable signature and return values expected by Nodezator and the relevant workflow.
Use existing graph and workflow decorators where applicable; preserve their runtime contracts.
Implementation details inside a node are flexible when they preserve discovery, signature behavior, and connected workflow expectations.

When a node wraps a function from `exp/`, keep the node definition thin and coordinate any shared state or callable contract change with the experiment owner.
Do not assume every LangGraph function is directly compatible with Nodezator.

## Acceptance

- Every node definition directory contains `__main__.py`.
- Every definition exposes a valid `main_callable` referring to a callable in that module.
- The node is discoverable and displays the intended name in Nodezator.
- Connected workflows still load and execute through the expected graph/runtime path.
- Relevant Python checks pass, and any manual Nodezator validation is reported.
