from datetime import date, timedelta

from nodes_pack import ExecutionGraph, execution_node
from nodes_pack.data_elements.collect_data.__main__ import collect_data
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


@execution_node
def initialize(
        graph: ExecutionGraph = None,
        ticker: str = "",
        start: str = str(date.today() - timedelta(weeks=12)),
        end: str = str(date.today()),
        period: str = '1d',

) -> ExecutionGraph:
    dataset = collect_data(ticker, start=start, end=end, period=period)['dataset']
    dataset = next(iter(dataset.values()))

    @workflow_node
    def initialize_node(state: WorkflowState) -> WorkflowState:
        return {
            'history': [history_item('initialize', f'Derived context for {ticker}, from {start} to {end} by {period}')],
            'message': {'context': dataset},
        }

    graph.add_node(initialize_node, auto_edge=True)
    return graph


main_callable = initialize
