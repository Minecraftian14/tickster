from typing import Optional

from tickster.workflow.state import WorkflowState


def orchestrate(state: WorkflowState, prompt: Optional[str] = None, message_key: Optional[str] = None, message: Optional[str] = None) -> WorkflowState:
    if prompt is not None: state['prompt'] = prompt
    if message_key is not None: state['message'] = {message_key: message}
    return state


main_callable = orchestrate
