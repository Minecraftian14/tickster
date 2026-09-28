from collections import defaultdict

from .models import GraphNode, GraphState
from ... import ExecutionGraph


def create_graph_state(graph: ExecutionGraph) -> GraphState:
    names = set(graph.nodes)
    names.update(edge.source for edge in graph.edges)
    names.update(edge.target for edge in graph.edges)

    return GraphState(
        nodes={name: GraphNode(name) for name in names},
        edges=graph.edges,
        start=graph.start,
        last=graph.last,
    )


def adjacency(graph: GraphState):
    outgoing = defaultdict(list)
    incoming = defaultdict(list)

    for edge in graph.edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)

    return outgoing, incoming
