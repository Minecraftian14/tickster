# `business.nodes_pack`

## Purpose and Tools

This package contains Nodezator node packs: collections of node definitions exposed to visual workflows.
Python files directly under `nodes_pack/` support node workflow execution and are not node definitions.

## Placement and Boundaries

Each node pack is a directory under `nodes_pack/`, such as `basic_elements/` or `exp_zeta_hero/`.
Each node definition is a directory inside a pack and must contain `__main__.py`.
That file defines the callable exposed to Nodezator and binds it as `main_callable = function_name`.

The node-definition folder and callable names should match by default.
These paths and symbols are loader-sensitive; missing `__main__.py` or `main_callable` can prevent discovery or startup.
Pack-level helpers may live directly under the pack directory.

Use existing graph and workflow decorators where applicable.
An experiment function is not automatically compatible with Nodezator; a Nodezator-facing function needs a node definition.

## Ownership and Acceptance

Treat node definitions as AI-assisted, contract-bound and shared graph/runtime support as human-reviewed or hybrid.
Every node definition has a valid `main_callable` referencing a callable in `__main__.py`.
Confirm nodes are discoverable under the intended name and connected workflows still load.
