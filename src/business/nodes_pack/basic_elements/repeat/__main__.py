from random import random

from nodes_pack import ExecutionGraph, execution_node
from nodes_pack.execution_graph import Edge, execution_state_name_aware
from tickster.workflow.helpers import WorkflowNode
from tickster.workflow.state import WorkflowState, history_item

START_NODE = "START"
END_NODE = "END"


def make_name(name, index):
    if "-" in name:
        splits = name.rsplit("-", 1)
        return "-".join((splits[0], str(index), splits[1]))
    return f"{name}-{index}"


@execution_node
def repeat(
        graph: ExecutionGraph,
        body: ExecutionGraph,
        times: int = 1,
) -> ExecutionGraph:
    merged_nodes: dict[str, WorkflowNode] = graph.nodes
    merged_edges: list[Edge] = graph.edges
    start_node = graph.start
    end_node = graph.last

    for index in range(times):

        for name, node in body.nodes.items():
            name = make_name(name, index)
            # TODO: Verify if node was wrapped using execution_state_name_aware before, only then use node.__wrapped__, otherwise just node
            node = execution_state_name_aware(node.__wrapped__, name)
            merged_nodes[name] = node
        for edge in body.edges:
            merged_edges.append(Edge(source=make_name(edge.source, index), target=make_name(edge.target, index), label=edge.label, callable=edge.callable))

        merged_edges.append(Edge(source=end_node, target=make_name(body.start, index)))
        end_node = make_name(body.last, index)

    return ExecutionGraph(
        nodes=merged_nodes,
        edges=merged_edges,
        start=start_node,
        last=end_node,
    )


main_callable = repeat
