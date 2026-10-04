import os
from typing import TypedDict

from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, START, END

from gai_providers import OPENROUTER_CONFIG

# Configuration
DOCS_DIR = "C:/BASE/WORKSPACES/CODING/tickster/src/business/data_collection"
DB_DIR = "chroma_db_storage"


# 1. Define the Shared Graph State
class GraphState(TypedDict):
    question: str
    context: str
    response: str


# 2. Setup or Load Local Knowledge Base
def get_local_retriever():
    embeddings = OpenAIEmbeddings(
        model='liquid/lfm-2.5-embedding-350m:free',
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_CONFIG["default"],
    )

    # Check if vector DB already exists locally
    if os.path.exists(DB_DIR) and os.listdir(DB_DIR):
        print("Loading existing local Chroma DB...")
        vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    else:
        print("No local vector database found. Processing documents...")
        if not os.path.exists(DOCS_DIR) or not os.listdir(DOCS_DIR):
            raise FileNotFoundError(f"Please put PDFs inside the '{DOCS_DIR}' directory.")
        loader = DirectoryLoader(
            DOCS_DIR,
            glob="**/*.py",
            loader_cls=TextLoader,
            show_progress=True
        )
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=DB_DIR)

    return vectorstore.as_retriever(search_kwargs={"k": 3})


retriever = get_local_retriever()

# 3. Initialize OpenRouter Client
# OpenRouter is fully API-compatible with the standard OpenAI SDK client format
llm = ChatOpenRouter(
    model="openrouter/free",
    temperature=0,
    api_key=OPENROUTER_CONFIG["default"],
)


# 4. Define Graph Nodes
def retrieve_node(state: GraphState):
    """Fetches relevant context chunks from the local SQLite/Chroma DB."""
    print("--- RETRIEVING LOCAL CONTEXT ---")
    question = state["question"]
    docs = retriever.invoke(question)
    context_str = "\n\n".join([doc.page_content for doc in docs])
    return {"context": context_str}


def generate_node(state: GraphState):
    """Sends combined context and prompt to OpenRouter Cloud LLM."""
    print("--- GENERATING ANSWER VIA OPENROUTER ---")
    question = state["question"]
    context = state["context"]

    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know.\n\n"
        "Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    chain = prompt | llm
    ai_message = chain.invoke({"context": context, "input": question})
    return {"response": ai_message.content}


# 5. Compile the LangGraph Control Flow
workflow = StateGraph(GraphState)

# Add processing units (Nodes)
workflow.add_node("retrieve_docs", retrieve_node)
workflow.add_node("generate_answer", generate_node)

# Map operational flow (Edges)
workflow.add_edge(START, "retrieve_docs")
workflow.add_edge("retrieve_docs", "generate_answer")
workflow.add_edge("generate_answer", END)

rag_app = workflow.compile()

# 6. Runtime Execution Loop
if __name__ == "__main__":
    print("\n LangGraph + OpenRouter Hybrid RAG Ready!")
    while True:
        user_query = input("\nUser: ")
        if user_query.lower() in ['exit', 'quit']:
            break

        initial_state = {"question": user_query, "context": "", "response": ""}
        output_state = rag_app.invoke(initial_state)

        print(f"\nAI: {output_state['response']}")
