from collections.abc import Callable
from functools import wraps
from random import random
from typing import Optional

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from tickster.workflow.state import WorkflowState

WorkflowNode = Callable[[WorkflowState], WorkflowState]


def issue_name(node):
    return f'{node.__name__}-{random()}'


def execution_state_name_aware(function: WorkflowNode, state_name: str) -> WorkflowNode:
    @wraps(function)
    def wrapper(state: WorkflowState):
        state['state_name'] = state_name
        print("STARTING", state_name)
        state = function(state)
        print("ENDING", state_name)
        if 'state_name' in state: del state['state_name']
        return state

    return wrapper


class Edge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None
    callable: Optional[Callable] = None


class ExecutionGraph(BaseModel):
    nodes: dict[str, WorkflowNode] = Field(default_factory=lambda: {})
    edges: list[Edge] = Field(default_factory=lambda: [])
    start: str = Field(default=None)
    last: str = Field(default=None)

    def add_node(self, node: WorkflowNode, name: str = None, auto_edge: bool = False):
        if name is None: name = issue_name(node)
        node = execution_state_name_aware(node, name)
        self.nodes[name] = node
        if self.start is None: self.start = name
        if auto_edge and self.last is not None: self.add_edge(self.last, name)
        self.last = name
        return name

    def add_edge(self, source: str, target: str, label: str = None, callable: Callable = None):
        self.edges.append(Edge(source=source, target=target, label=label, callable=callable, ))

    def create_langgraph_workflow(self):
        builder = StateGraph(WorkflowState)

        for name, node in self.nodes.items():
            builder.add_node(name, node)

        builder.add_edge(START, self.start)
        builder.add_edge(self.last, END)

        for edge in self.edges:
            builder.add_edge(edge.source, edge.target)

        graph = builder.compile()

        return graph
