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

### Creating a Nodezator category for an experiment

When an experiment already exists under `src/business/exp/<experiment>/`, create its corresponding node pack at `src/business/nodes_pack/<experiment>/`. Use `src/business/nodes_pack/exp_zeta_hero/` alongside `src/business/exp/exp_zeta_hero/` as the concrete mapping example: the pack contains one node-definition directory for each agent, and each definition imports the corresponding `@workflow_node` agent function from the experiment package. The Nodezator wrapper assembles the graph; it does not duplicate the agent's research logic.

For example, `nodes_pack/exp_zeta_hero/warren_buffett/__main__.py` imports `warren_buffett` from `exp.exp_zeta_hero.warren_buffett_analyst` and adds that function to the graph; `risk_manager/__main__.py` does the same for the `risk_manager` function. The agent module and node folder names need not be identical when the established project naming differs, but each wrapper must import the intended implementation explicitly.

Each agent node definition follows the loader contract above: put its implementation in `<agent_name>/__main__.py`, wrap a graph-assembly function with `@execution_node`, add the imported agent to the supplied `ExecutionGraph` with `auto_edge=True` for the ordinary sequential flow, return the graph, and bind the wrapper as `main_callable`. Match the folder and exported node callable names by default. Use `ExecutionGraph.add_edge(...)` for intentional non-sequential connections; do not assume that `@execution_node` itself creates an edge or invokes the agent immediately.

`ExecutionGraph` is a builder for LangGraph execution: `add_node` registers a workflow callable and makes the first and most recently added nodes the graph's start and end; `auto_edge=True` connects the previously added node to the new one. `create_langgraph_workflow()` compiles the registered nodes and edges. `@execution_node` is for Nodezator-facing graph-assembly functions: it creates an `ExecutionGraph` when none is supplied, or copies the supplied graph before the function extends it. The agent callable placed inside the graph still follows the `business.exp` `WorkflowState` contract and uses `@workflow_node`; these decorators have different jobs.

The `basic_elements` pack illustrates the main patterns to follow or compose:

- `start` creates an empty `ExecutionGraph`.
- `add_message` adds a workflow node that records a history item and places a named value in `WorkflowState.message`.
- `edit_prompt` and `edit_reference` add nodes that initialize those respective state fields and record the change in history.
- `call_llm` adds a workflow node that reads the prompt and model from state, invokes the model, and records the response.
- `merge` combines graph structures, while `tran_state` provides a state inspection/serialization utility. `orchestrate` is a direct state helper rather than an `ExecutionGraph` node definition.

Research may require run-specific user details such as starting capital, risk tolerance, investment horizon, or constraints. In that case, add a user-specifications node to the same experiment pack and place it before the agent nodes in the graph. Give it Nodezator inputs for the details the research actually uses; its inner `@workflow_node` should seed those named values in `WorkflowState.message` (and add the required history entry), so downstream agents receive them as part of the initial run state. Use the `add_message` pattern as a starting point, with a single node able to seed multiple related fields where appropriate. Coordinate the message keys and value shapes with the agents; do not put these run-specific values in module globals or bake them into graph construction.

The agent remains responsible for being runnable when a user value is absent: read `message` defensively, apply a documented field-specific default for each missing or unspecified user detail, and use the supplied value when present. Do not require `message` to exist merely because the research can accept user settings. Keep the default behavior in the experiment agent contract as well as any UI-facing defaults, so the workflow remains usable when run without the Nodezator input node. See [business.exp.md](business.exp.md) for the agent-side rule.

## Ownership and Acceptance

Treat node definitions as AI-assisted, contract-bound and shared graph/runtime support as human-reviewed or hybrid.
Every node definition has a valid `main_callable` referencing a callable in `__main__.py`.
Confirm nodes are discoverable under the intended name and connected workflows still load.
