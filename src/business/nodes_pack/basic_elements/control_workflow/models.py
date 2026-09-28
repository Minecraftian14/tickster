from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

from pygame import Rect

from tickster.workflow.state import WorkflowState


@dataclass
class GraphNode:
    name: str
    rect: Rect = field(default_factory=Rect)


@dataclass
class GraphState:
    nodes: dict[str, GraphNode]
    edges: list
    start: Optional[str]
    last: Optional[str]
    active_nodes: set[str] = field(default_factory=set)
    width: int = 0
    height: int = 0
    lock: Lock = field(default_factory=Lock)
    result: WorkflowState = None

    def set_active(self, name: str, active: bool = True):
        print("SET_ACTIVE", name, active)
        with self.lock:
            if active: self.active_nodes.add(name)
            else: self.active_nodes.discard(name)

    def active(self) -> set[str]:
        with self.lock:
            return self.active_nodes.copy()
