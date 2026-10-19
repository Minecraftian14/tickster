"""Shared, state-only helpers for Tacit Abyss workflow nodes."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from data_representation import render_context_pack
from tickster.workflow.state import WorkflowState, history_item

T = TypeVar("T", bound=BaseModel)


class TradeProposal(BaseModel):
    action: str
    rationale: str
    entry_price: float | None = None
    stop_loss: float | None = None
    target_price: float | None = None
    allocation_percent: float | None = None


class PortfolioRecommendation(BaseModel):
    rating: str
    executive_summary: str
    investment_thesis: str
    key_risks: str


def context_from_state(state: WorkflowState) -> tuple[Any, Any, Any]:
    """Return ``(pack, result, bundle)`` from the agreed message contract."""
    context = (state.get("message") or {}).get("context")
    if not isinstance(context, tuple) or len(context) != 2 or not isinstance(context[1], tuple) or len(context[1]) != 2:
        raise ValueError("message['context'] must be (ContextPack, (EnrichmentResult, CanonicalBundle))")
    return context[0], context[1][0], context[1][1]


def render_context(state: WorkflowState, *, record_types: tuple[str, ...] = ()) -> str:
    pack, _, _ = context_from_state(state)
    if record_types:
        selected = [record for record in pack.source_records if record.__class__.__name__ in record_types]
        pack = pack.model_copy(update={"source_records": selected})
    rendered = render_context_pack(pack).strip()
    return rendered or "No collected evidence was available for this role."


def prior_output(state: WorkflowState, node_name: str) -> Any:
    for item in reversed(state.get("history", [])):
        if item.get("node_name") == node_name:
            return item.get("output")
    return f"No {node_name} result is available."


def outputs(state: WorkflowState, node_names: tuple[str, ...]) -> str:
    return "\n\n".join(f"## {name}\n{prior_output(state, name)}" for name in node_names)


def _content(value: Any) -> str:
    return str(getattr(value, "content", value))


def _parse_structured(text: str, schema: type[T]) -> tuple[dict[str, Any] | None, str | None]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        return None, "model did not return a JSON object"
    try:
        return schema.model_validate(json.loads(match.group(0))).model_dump(), None
    except (json.JSONDecodeError, ValidationError) as exc:
        return None, str(exc)


def model_update(state: WorkflowState, *, node_name: str, prompt: str, schema: type[T] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Invoke the configured model and record a single auditable node result."""
    if "llm" not in state:
        raise ValueError("Tacit Abyss agents require state['llm']")
    raw = state["llm"].invoke(prompt)
    text = _content(raw)
    output: Any = text
    parse_error = None
    if schema is not None:
        parsed, parse_error = _parse_structured(text, schema)
        output = parsed if parsed is not None else {"text": text, "validation_error": parse_error}
    return {"history": [history_item(node_name, output, input_raw=prompt, output_raw={"model_output": text, "validation_error": parse_error})]}


def role_prompt(role: str, task: str, evidence: str, prior: str = "") -> str:
    return f"""You are the {role} in an India-only investment research experiment.
Use only the supplied evidence. Keep collected facts separate from derived metrics and your interpretation. Do not place, simulate, or imply an executable order. State evidence gaps explicitly.

Task: {task}

Evidence:
{evidence}

Prior workflow results:
{prior or 'None'}
"""
