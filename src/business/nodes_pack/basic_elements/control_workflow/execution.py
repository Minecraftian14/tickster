from contextlib import redirect_stdout
from datetime import datetime
from threading import Thread

from nodes_pack import ExecutionGraph
from tickster.workflow.state import create_state
from .models import GraphState


def start_execution(graph: ExecutionGraph, state: GraphState):
    def execute():
        with open("temp/stdout.log", "w", encoding='utf-8') as file_out:
            with redirect_stdout(file_out):
                print(datetime.now(), flush=True)
                workflow = graph.create_langgraph_workflow()
                agent_state = create_state()
                agent_state['on_start_execution'] = lambda name: state.set_active(name)
                agent_state['on_finish_execution'] = lambda name: state.set_active(name, False)
                print("state.result", state.result)
                state.result = workflow.invoke(agent_state)
                print("state.result", state.result)

    Thread(target=execute, daemon=True).start()
