from typing import Optional
from langchain_community.chat_models.tongyi import ChatTongyi
from pydantic import BaseModel, Field
from typing import Literal, Annotated, Sequence, Optional, Any, List
import os
os.environ["DASHSCOPE_API_KEY"] = "sk-cf312af820bb4841a707fc4284f147a4"


llm = ChatTongyi(   
    model_name="qwen-turbo",
    streaming=True
)
# Pydantic
class SubTask(BaseModel):
    task_id: int = Field(description="Unique ID for the sub-task, starting from 1.")
    tool_name: str = Field(description="The name of the tool to be called for this task.")
    tool_args: dict = Field(description="The arguments to be passed to the tool.")
    question: str = Field(description="The natural language question this sub-task aims to answer.")
    status: str = Field(default="pending", description="Status of the task: pending, completed, failed.")
    result: Optional[str] = Field(default=None, description="The result obtained after executing the tool.")

class Plan(BaseModel):
    thought: str = Field(description="A brief summary of the overall plan and reasoning.")
    tasks: List[SubTask] = Field(description="A list of sub-tasks to be executed.")


class PlannerOutput(BaseModel):
    """
    一个可以包含计划或直接聊天回复的输出模型。
    这两者必须是互斥的。
    """
    
    task: Optional[SubTask] = Field(
        default=None, 
        description="A detailed, step-by-step task if the query requires tool use. Should be null if a direct chat response is provided."
    )
    
    chat_response: Optional[str] = Field(
        default=None, 
        description="A direct response to the user if the query is a simple chat message that does not require any tools. Should be null if a plan is generated."
    )


structured_llm = llm.with_structured_output(PlannerOutput)

print(structured_llm.invoke("帮我查询拼多多公司的股价"))