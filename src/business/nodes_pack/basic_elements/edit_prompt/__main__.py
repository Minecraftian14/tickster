from tickster.workflow.state import WorkflowState


def edit_prompt(state: WorkflowState, prompt: str = "") -> WorkflowState:
    state['prompt'] = prompt
    return state


main_callable = edit_prompt
