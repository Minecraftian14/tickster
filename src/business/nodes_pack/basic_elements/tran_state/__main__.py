import dataclasses
import json
from typing import Any

from pydantic import BaseModel

from tickster.workflow.state import WorkflowState

ExtractOptions = {
    'widget_name': 'option_menu',
    'widget_kwargs': {
        'options': [
            'Raw',
            'Reference',
            'Last History Item',
            'Last History Output',
        ]
    },
}

OutputOptions = {
    'widget_name': 'option_menu',
    'widget_kwargs': {
        'options': [
            'Raw',
            'String',
            'JSON',
            'Pretty JSON',
        ]
    },
}

def handle_unknowns(obj):
    if isinstance(obj, BaseModel):
        return obj.model_dump(fallback=handle_unknowns)
    if dataclasses.is_dataclass(obj):
        if "lock" in dir(obj):
            obj.lock = None
        return dataclasses.asdict(obj)
    return str(obj)


def tran_state(state: WorkflowState, extract: ExtractOptions = "Last History Output", output: OutputOptions = "JSON") -> Any:
    match extract:
        case "Reference": state = state['reference']
        case "Last History Item": state = state['history'][-1]
        case "Last History Output": state = state['history'][-1]['output']
    match output:
        case "String": state = str(state)
        case "JSON": state = json.dumps(state, default=handle_unknowns)
        case "Pretty JSON": state = json.dumps(state, indent=2, default=handle_unknowns)
    return state


main_callable = tran_state
