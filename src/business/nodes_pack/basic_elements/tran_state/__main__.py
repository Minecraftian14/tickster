import json
from typing import Any

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


def tran_state(state: WorkflowState, extract: ExtractOptions = "Last History Output", output: OutputOptions = "JSON") -> Any:
    match extract:
        case "Reference": state = state['reference']
        case "Last History Item": state = state['history'][-1]
        case "Last History Output": state = state['history'][-1]['output']
    match output:
        case "String": state = str(state)
        case "JSON": state = json.dumps(state)
        case "Pretty JSON": state = json.dumps(state, indent=2)
    return state


main_callable = tran_state
