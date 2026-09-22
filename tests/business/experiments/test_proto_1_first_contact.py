from typing import TypedDict
import pytest
from dotenv import load_dotenv
load_dotenv()

from gai_providers import OPENROUTER_CONFIG

from langgraph.graph import StateGraph, START, END
from langchain_openrouter import ChatOpenRouter


class State(TypedDict):
    message: str
    response: str


llm = ChatOpenRouter(
    model="openrouter/free",
    temperature=0,
    api_key=OPENROUTER_CONFIG["default"],
)


def chatbot(state: State):
    response = llm.invoke(state["message"])
    return { "response": response.content }


def test_gai_first_contact():
    graph_builder = StateGraph(State)

    graph_builder.add_node("chatbot", chatbot)

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)

    graph = graph_builder.compile()

    result = graph.invoke({
        "message": "Explain LangGraph in one sentence.",
    })
    print()
    print(result["response"])
