import operator
from datetime import datetime
from typing import TypedDict, Any, Optional, Annotated, Required

from langchain_core.language_models import BaseChatModel


class HistoryItem(TypedDict):
    node_name: str
    output: Any
    timestamp: datetime
    input_raw: Optional[Any]
    output_raw: Optional[Any]


def history_item(node_name: str, output: Any, timestamp: datetime = None, input_raw: Optional[Any] = None, output_raw: Optional[Any] = None) -> HistoryItem:
    if timestamp is None: timestamp = datetime.now()
    return {'node_name': node_name, 'output': output, 'timestamp': timestamp, 'input_raw': input_raw, 'output_raw': output_raw}


def merge_dict(left: dict, right: dict) -> dict:
    if left is None: left = {}
    if right is None: right = {}
    if 'node_name' in left: left = {'history': left}
    if 'node_name' in right: right = {'history': right}
    return {**left, **right}


# This is not just a state, but a whole environment for our system to run on
class WorkflowState(TypedDict, total=False):
    # For internal use by agents only
    llm: BaseChatModel

    # General instruction or just a starter message
    # Only for use by prompt constructors
    prompt: str

    # Agent/Tool-specific message
    # Given by agents/tools for next in line agents/tools
    message: Annotated[dict[str, str | Any], merge_dict]

    # All tools or notes should add their entry here
    history: Required[Annotated[list[HistoryItem], operator.add]]

    # Helper variable to control how data is cached
    cache_key: Any

    # Helper variable to prevent unnecessary LLM calls
    mock: bool
