from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_community.chat_models.tongyi import ChatTongyi
import os
os.environ["DASHSCOPE_API_KEY"] = "sk-cf312af820bb4841a707fc4284f147a4"

@tool
def search(query: str):
    """Searches for the query."""
    return f"Search results for {query}"

tools = [search]

model = ChatTongyi(
    model_name="qwen-plus",
    streaming=True
).bind_tools(tools)

DB_URI = "postgresql://kevin:123456@localhost:5432/postgres?sslmode=disable"
checkpointer = PostgresSaver.from_conn_string(DB_URI)

def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"

def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

builder = StateGraph(MessagesState)

builder.add_node("agent", call_model)
builder.add_node("action", ToolNode(tools))

builder.set_entry_point("agent")

builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": "__end__"
    }
)

builder.add_edge("action", "agent")

graph = builder.compile(checkpointer=checkpointer)

config = {
    "configurable": {
        "thread_id": "1"
    }
}

for chunk in graph.stream(
    {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
    config,
    stream_mode="values"
):
    chunk["messages"][-1].pretty_print()

for chunk in graph.stream(
    {"messages": [{"role": "user", "content": "what's my name?"}]},
    config,
    stream_mode="values"
):
    chunk["messages"][-1].pretty_print()