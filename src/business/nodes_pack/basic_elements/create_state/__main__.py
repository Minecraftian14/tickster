from typing import Optional, Any

from langchain_openrouter import ChatOpenRouter

from gai_providers import OPENROUTER_CONFIG
from tickster.workflow.state import WorkflowState, history_item


def create_state(model: str = 'openrouter/free', api_key: str = 'default', cache_key: Any = None, mock: bool = False) -> WorkflowState:
    return {
        'llm': ChatOpenRouter(
            model=model,
            temperature=0,
            api_key=OPENROUTER_CONFIG[api_key],
        ),
        'history': [history_item('create_state', 'LLM Initialized')],
        'cache_key': cache_key,
        'mock': mock,
    }


main_callable = create_state
