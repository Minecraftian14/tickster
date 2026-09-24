from tickster.workflow.state import WorkflowState


def add_message(state: WorkflowState, message_key: str = "key", message: str = "value") -> WorkflowState:
    if 'message' not in state: state['message'] = {}
    state['message'][message_key] = message
    return state


main_callable = add_message
