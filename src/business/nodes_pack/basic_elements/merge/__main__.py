from random import random

from nodes_pack import ExecutionGraph, execution_node
from nodes_pack.execution_graph import Edge
from tickster.workflow.helpers import WorkflowNode
from tickster.workflow.state import WorkflowState, history_item

START_NODE = "START"
END_NODE = "END"


@execution_node
def merge(*graphs: ExecutionGraph) -> ExecutionGraph:
    merged_nodes: dict[str, WorkflowNode] = {}
    merged_edges: list[Edge] = []

    seen_edges: set[tuple[str, str]] = set()

    start_node = f'{START_NODE}.{random()}'
    end_node = f'{END_NODE}.{random()}'
    merge_key = f'{start_node}.{end_node}'

    def merge_starter(state: WorkflowState) -> WorkflowState:
        state['message'] = {merge_key: len(state['history'])}
        return state

    def merge_ender(state: WorkflowState) -> WorkflowState:
        length = state['message'].pop(merge_key)
        state['reference'] = history_item('merge_node', state['history'][length:])
        return state

    merged_nodes[start_node] = merge_starter
    merged_nodes[end_node] = merge_ender

    def add_edge(edge: Edge) -> None:
        key = (edge.source, edge.target)
        print("KEY", key)
        if key not in seen_edges:
            print("ADDED")
            seen_edges.add(key)
            merged_edges.append(edge.model_copy())

    for graph in graphs:
        for node_id, node in graph.nodes.items():
            if node_id not in merged_nodes:
                merged_nodes[node_id] = node
            # if node_id in merged_nodes:
            #     if merged_nodes[node_id] != node:
            #         raise ValueError(f"Conflicting definitions for node {node_id!r}")
            # else:
            #     merged_nodes[node_id] = node

        for edge in graph.edges:
            add_edge(edge)

        if graph.start is not None:
            add_edge(Edge(source=start_node, target=graph.start))

        if graph.last is not None:
            add_edge(Edge(source=graph.last, target=end_node))

    return ExecutionGraph(
        nodes=merged_nodes,
        edges=merged_edges,
        start=start_node,
        last=end_node,
    )


main_callable = merge
