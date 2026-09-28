from __future__ import annotations

from functools import wraps

from nodes_pack import ExecutionGraph


def auto_create_execution_graph(function):
    @wraps(function)
    def wrapper(graph: ExecutionGraph, *args, **kwargs):
        if graph is None: graph = ExecutionGraph()
        return function(graph, *args, **kwargs)

    return wrapper


def execution_node(function):
    function = auto_create_execution_graph(function)
    return function
