from collections.abc import Callable
from functools import wraps
from textwrap import dedent

from diskcache import Cache
from diskcache.core import full_name
from langgraph.graph.state import _get_channels

from tickster.workflow.state import WorkflowState

WorkflowNode = Callable[[WorkflowState], WorkflowState]


def clean(message: str) -> str:
    return dedent(message).strip()


workflow_cache = Cache('temp/workflow_cache')


def cache_aware(function: WorkflowNode) -> WorkflowNode:
    function_name = full_name(function)

    @wraps(function)
    def wrapper(state: WorkflowState):
        if 'cache_key' in state and state['cache_key'] is not None:
            cache_key = f'{state['cache_key']}.{function_name}'
            if cache_key in workflow_cache:
                return workflow_cache[cache_key]
            state = function(state)
            workflow_cache[cache_key] = state
        return state

    return wrapper


def merge_states(left: WorkflowState, right: WorkflowState) -> WorkflowState:
    channels, managed, _ = _get_channels(WorkflowState)

    for key, value in left.items():
        if key in channels:
            channels[key].update([value])

    for key, value in right.items():
        if key in channels:
            channels[key].update([value])

    return {
        key: channel.get()
        for key, channel in channels.items()
        if channel.is_available()
    }


def state_stable(function: WorkflowNode) -> WorkflowNode:
    @wraps(function)
    def wrapper(initial: WorkflowState):
        final = function(initial)
        # return merge_states(initial, final)
        return final

    return wrapper


def workflow_node(function: WorkflowNode) -> WorkflowNode:
    function = state_stable(function)
    function = cache_aware(function)
    return function
