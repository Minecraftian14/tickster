# `business.exp`

## Purpose and Tools

This package contains the final, framework-compatible implementations of experiments and research as LangGraph workflow nodes.
Research notes, source papers, exploratory outputs, and project systems are inputs to migration, not runtime package contents.
Keep only the code and runtime resources needed by the implemented experiment, such as helper functions and prompt templates.

An experiment is not validated product behavior.
Preserve the distinction between source evidence, derived analysis, forecasts, recommendations, and observed outcomes.
Experiments must not trigger autonomous trading or bypass human judgment and risk oversight.

## Placement and Boundaries

### Package structure and migration inputs

- Place each experiment in its own package under `src/business/exp/`. Keep its final node functions and experiment-specific helpers in that package.
- Transform research material into compatible implementation. Do not copy a research project wholesale or retain unrelated dashboards, APIs, persistence systems, monitoring services, or other project infrastructure from its source.
- Keep reusable collection and enrichment capabilities in their respective business packages rather than duplicating them inside an experiment. Follow their existing public APIs and the applicable package contracts.
- Keep implementation prompt templates with the experiment when they are part of its runtime behavior. Do not treat source research documents as prompt templates without adapting and reviewing them for the framework.

### Migration method

Migrate the research behavior, not its original software architecture. 
Expect to rewrite substantial parts of a source project: 
the research's concepts and evidence may be retained, while its agents, data flow, tools, memory, and runtime must be expressed through this repository's contracts.

For each migration:

1. **Inventory the source.** Read the research description and relevant materials. List its agents, inputs, outputs, prompts, calculations, source data, derived features, tools, memory needs, external services, and claimed outcomes. Mark which items are requirements, evidence, implementation details, or unrelated project infrastructure. Do not claim equivalence for behavior that has not been mapped.
2. **Classify and map each item.** Map source acquisition to `data_collection`; canonical identity, provenance, and evidence to `data_foundation`; reusable calculations and derived values to `data_enrichment`; readable prompt context to `data_representation`; and research decisions or interpretations to experiment workflow nodes. Classify tools as collectors/enrichers or agent-invoked tools using the section below. Classify memory as transient workflow context and check it against `WorkflowState`. Record every requirement that has no supported destination as a migration blocker.
3. **Reuse existing contracts first.** Inspect the relevant package specification and public APIs before implementation. Reuse providers, canonical records and bundles, enrichers, representations, and workflow/model support where they fit. Add a shared capability only in its owning package and under that package's contract; do not create an experiment-local duplicate to avoid a missing shared capability.
4. **Decompose and implement.** Keep deterministic transformations as ordinary helpers or reusable enrichers. Make each graph-facing agent a separate `WorkflowState` node. Adapt source prompt and data formats to the framework, and preserve meaningful intermediate and final values in the node's history. Do not carry over source-framework orchestration or infrastructure merely because it exists in the research project.
5. **Trace requirements to outputs.** For each research requirement, identify the implementation node or shared capability and the observable history/evidence that demonstrates it. Keep collected facts, derived analysis, model interpretation, recommendations, and observed outcomes distinguishable.
6. **Integrate and validate.** Add Nodezator definitions following [business.nodes_pack.md](business.nodes_pack.md) when required for the migration. Review package checks and behavioral evidence. If a required capability or contract is unsupported or unresolved, stop the affected migration and use the pause/resume procedure instead of coding around the gap.

### Agent node contract

- Every agent exposed to the workflow is a function accepting one `WorkflowState` and returning a state update compatible with `WorkflowState`.
- Decorate each agent function with `@workflow_node` from `tickster.workflow.helpers`. Keep helper calculations as ordinary functions unless they are independently intended to be graph nodes.
- Import the shared state and history helpers from `tickster.workflow.state`. The state contract is authoritative; inspect it and its consumers before relying on fields beyond those documented here.
- Every agent must append a history entry using `history_item(...)` and return it in a singleton `history` list, for example: `return {"history": [history_item("agent_name", output)]}`. A node returns its update, not a replacement copy of the accumulated history. LangGraph's `history` reducer accumulates entries.
- `history` is required and is the trace of each node's shared result and, where useful, raw input/output. Put the result intended for downstream interpretation in `output`; include `input_raw` and/or `output_raw` when those values materially differ from the shared, readable result. Do not omit the history entry because a value is also placed in another state field. The `history` reducer appends updates, so return only the current node's singleton addition rather than copying prior entries.
- The `@workflow_node` wrapper supplies the latest history item as `reference` only when the incoming state has no `reference`. Do not assume it overwrites an existing reference. Read the state and helper implementation when node behavior depends on reference propagation.
- Prefer sharing an agent's result through `history`. Use `reference` only where the immediate downstream node needs an explicit reference to a history item. Use `message` for named values only when a later, potentially non-adjacent node needs a shared value. Avoid propagating the same result through all three channels without a clear consumer.
- Research may require run-specific user specifications such as starting capital, risk tolerance, investment horizon, or constraints. When such inputs are supplied by the experiment's Nodezator user-specifications node, they arrive in named keys under `WorkflowState.message`. Agents must read these values defensively and remain runnable without that node or without any particular key: use a supplied value when present, and otherwise apply a documented field-specific default. Do not assert that `message` or every user-specification key exists. Keep each default explicit and consistent with the research; if no defensible default can be established for a required value, treat it as an unresolved migration requirement rather than silently inventing one.
- For inter-agent context and memory, use only values carried through `WorkflowState` and its history. Do not add process-global variables, hidden mutable state, or database-backed memory. The state contract currently includes `history`, `reference`, and `message` for workflow communication; `history` is required, while `reference` and `message` are optional mechanisms with the preference order above. Other fields have specific runtime purposes and are not a license to add undocumented memory. If the research requires durable, cross-run, or retrieval memory that this state-only model cannot provide, pause under the migration handoff procedure below.

### Translating research agents

Research may describe agents that are not directly compatible with the framework. 
Adapt the behavior according to its computational role:

- **Non-LLM agent:** Implement its calculations as ordinary helpers and/or workflow nodes. When the calculation is a reusable data transformation with declared data dependencies, implement that transformation in the enrichment package and have the workflow node call the enricher. The conceptual agent remains an agent node in the experiment graph; using an enricher for its calculation does not turn the agent itself into an enricher.
- **LLM-only agent:** Obtain the required `WorkflowState` inputs, including the relevant bundle or canonical records, render data into readable text through `data_representation`, construct the adapted prompt, invoke the configured model through the framework-supported state/model path, and record the output in history. Do not assume the research's original input format or response is directly compatible. Structured output is optional unless the research behavior requires it; when required, validate and record parse/validation failures rather than silently treating malformed output as valid. Supply only the context the prompt needs, preserving provenance and collected-versus-derived distinctions where they affect interpretation.
- **Mixed agent:** Extract deterministic transformations and calculations into ordinary helpers or reusable enrichers. Keep the model interaction in the workflow node, and record the final agent output and any meaningful intermediate raw inputs/outputs in history.
- Keep provider-specific model and external-service behavior at integration edges. Do not introduce a new shared agent/tool framework inside `exp` to avoid an existing contract gap.

### Data, collection, and enrichment

- Treat source data, market data, features, strategy calculations, backtest/algotrade results, and suggestions according to whether they are collected facts or derived outputs; do not collapse those categories.
- For data acquired directly from a source, inspect the existing `data_collection` providers, result types, and contracts first. Reuse an existing provider where it covers the source and fields. If no provider fits, add a provider in the collection package according to its established design; do not scrape or fetch the same data privately from an experiment node.
- The foundation bundle (`CanonicalBundle`) carries canonical records and related evidence/index data. Match incoming collection results to the existing collection/foundation ingestion path; do not invent a parallel bundle or silently discard provenance, quality, identity, or time information.
- Treat values produced by processing collected data—such as market metrics, features, strategy calculations, and proposed trades—as derived/enriched data. Put reusable transformations in `data_enrichment`, declare their required and produced capabilities according to that package's design, and invoke them through its supported APIs. Keep experiment-specific interpretation in the experiment node when it is not a reusable data transformation.
- For LLM context, prefer the existing `data_representation` rendering functions over ad hoc serialization of bundles or canonical records. Render only the context the prompt needs, and preserve source/derived distinctions and provenance where they affect interpretation.
- If the needed provider, canonical capability, enrichment contract, representation behavior, or ownership permission is missing, do not hide the gap in experiment-local code. Pause and create a project-objective TODO as described below.

### Tools described by research

Classify each research tool before implementing it:

- A tool used only to gather source information belongs in the collection package, with any reusable normalization or feature calculation in enrichment. The experiment consumes the supported outputs.
- A tool that an agent actively chooses to call must be adapted as a LangGraph-compatible callable and invoked from the relevant agent/node. Record the call's meaningful input, result, and failure in history. Keep credentials and provider-specific behavior at the integration edge.
- If the framework has no supported way to model, execute, configure, or trace a required agent-invoked tool, pause and make it a separate project objective. Do not add a one-off convention that other experiments cannot discover or use.

### Nodezator integration

An agent function decorated with `@workflow_node` is not automatically a Nodezator node.
A corresponding Nodezator definition under `nodes_pack/`, following [business.nodes_pack.md](business.nodes_pack.md), is the expected companion for each agent.
Coordinate changes to experiment nodes and node definitions.
If Nodezator integration is explicitly deferred for a migration, record that follow-up and its reason in the migration resume context; do not report the visual workflow integration as complete.

### Migration-derived implementation decisions

- A migration may adapt a research system from one market or jurisdiction to another.
  Record the target market explicitly and map every retained role to local providers, canonical record types, enrichers, and terminology.
  Do not retain a source-specific provider, data source, or claim merely because it was present in the source project.
  Identify every substitution and every unavailable source in the migration inventory.
- A `ContextPackProfile` declares bounded context selection; it does not itself fetch data or run enrichers.
  Keep collector/enricher planning outside the experiment unless their package contract explicitly supplies a supported orchestration API.
  When an experiment receives a composite collection result, document one stable `WorkflowState.message` key and validate its shape before use.
  Prefer consuming the supplied `ContextPack`; rebuild a narrower pack from its result and bundle only when a role has a concrete, documented need for focused evidence.
- Convert research tools that only acquire or deterministically transform data into pre-collected canonical evidence and reusable enrichment before an agent runs.
  Retain agent-invoked tools only when the research behavior genuinely requires the model to choose a call at run time.
  A reusable indicator, statistic, or feature belongs in `data_enrichment`, including declared capabilities, lineage, and insufficient-data behavior, rather than in an experiment helper.
- Preserve semantically distinct evidence types as distinct collection records.
  For example, public social/forum posts are not editorial news even when both inform a sentiment role.
  A new external-source collector must be provider-neutral, preserve raw payload references, retrieval and publication times, instrument association, provenance, deduplication, and explicit unavailable/rate-limited/error results.
- Parallel graph branches must not concurrently update an unreduced `WorkflowState` field.
  In particular, `@workflow_node` may set `reference` when it is absent, while `reference` is a single-value channel.
  Seed a stable reference before a parallel fan-out, or make that fan-out sequential, and use reducer-backed `history` for concurrent agent outputs.
- An experiment may provide an optional `__main__.py` that demonstrates graph wiring without becoming a runtime requirement.
  Keep that file limited to graph assembly and demonstration values; agents and their package must remain usable without it.
  Deferring Nodezator does not permit Nodezator-specific behavior inside the experiment package.
- When a source requires structured output, retain the raw model response and record JSON/schema validation failures as history evidence.
  A malformed response may be retained as unvalidated text for review, but it must not be represented as a valid structured decision.
- When one source in a multi-source role is unavailable, make the absence visible in the affected agent's output and confidence framing.
  Create the required TODO and resume handoffs for the missing source; do not silently treat partial-source behavior as equivalent to the source research.

### Unsupported requirements and safe pause/resume

Pause the affected migration when a required capability is unsupported, its contract is unclear, a needed change crosses into a human-owned/shared contract without authorization, or a correct implementation would require prohibited global state or project infrastructure.
Do not substitute a mock, silently drop the research behavior, or claim equivalence.

For each independent gap, create a detailed project-objective plan at `temp/TODO_<title>.md`.
Treat it as a separate objective for another agent, not as a list of speculative implementation choices.
State the required behavior and its research basis, why current contracts cannot support it, affected packages/contracts and ownership boundaries, acceptance criteria, dependencies, and validation evidence expected.
Make the objective implementable and reviewable independently, without requiring that agent to perform the paused experiment migration.
Do not write the missing capability into `exp/` as a temporary substitute.

Create `temp/RESUME_<title>.md` for the paused migration.
Record the source material reviewed, migration work already completed, changed paths, remaining steps, each gap and why it is deferred, links/paths to the TODO plans, and any assumptions or known risks.
Give the next agent explicit resume instructions: verify that each prerequisite TODO has been implemented, reviewed as required, and passes its stated acceptance criteria; inspect the current contracts and working tree; then continue only the remaining migration.
If a prerequisite is unresolved or does not satisfy its criteria, update the handoff and pause again rather than coding around it.

Keep these migration handoff files in `temp/`, outside the experiment package.
In the stash/resume workflow, leave the new TODO plan out of the stash so it remains available to the separate capability implementation agent; stash the partial migration and its resume context together.
After the capability work is complete, restore the migration stash and follow the resume instructions, including re-checking that the prerequisite is actually satisfied. 
Do not treat the handoff documents as final experiment implementations.

## Ownership and Acceptance

Treat experiment implementations as human-reviewed or hybrid. Changes to shared workflow state, collection/foundation/enrichment/representation contracts, tool infrastructure, or Nodezator contracts must follow the ownership and approval policy of the affected module; an experiment's need does not authorize changing a human-owned contract.

A migration is complete when:

- Every intended agent is a `WorkflowState`-to-`WorkflowState` function decorated with `@workflow_node`, and every invocation contributes an appropriate `history_item` through a singleton `history` update.
- The research behavior has been mapped to compatible workflow nodes, helpers, collection providers, enrichers, LLM calls, and agent-invoked tools, without silently dropping required behavior or bypassing package boundaries.
- Data consumed by agents uses existing collection, canonical bundle, enrichment, and representation contracts, with needed provenance and data-quality distinctions retained.
- Required Nodezator definitions are discoverable and satisfy [business.nodes_pack.md](business.nodes_pack.md), or the explicit deferral is recorded in the resume context.
- Applicable package checks and behavioral evidence have been reviewed; unsupported requirements have TODO and resume handoffs and are not represented as implemented.
- Experimental evidence, derived analysis, recommendations, and outcomes remain distinguishable, and no autonomous real-world trading path has been introduced.
