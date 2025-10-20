import asyncio
import functools
from pprint import pprint
from langchain_core.messages import HumanMessage, AIMessage
# 从 langgraph.checkpoint.aiopg 导入
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from langchain_mcp_adapters.client import MultiServerMCPClient
# 导入日志模块，用于记录程序运行时的信息
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
# 导入操作系统接口模块，用于处理文件路径和环境变量
import os
import sys
import threading
import time
# 导入UUID模块，用于生成唯一标识符
import uuid
# 从html模块导入escape函数，用于转义HTML特殊字符
from html import escape
# 从typing模块导入类型提示工具
from typing import Literal, Annotated, Sequence, Optional, Any
# 从typing_extensions导入TypedDict，用于定义类型化的字典
from typing_extensions import TypedDict
# 导入LangChain的提示模板类
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
# 导入LangChain的消息基类
from langchain_core.messages import BaseMessage
# 导入消息处理函数，用于追加消息
from langgraph.graph.message import add_messages
# 导入预构建的工具条件和工具节点
from langgraph.prebuilt import tools_condition, ToolNode
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.messages import ToolMessage
# 导入状态图和起始/结束节点的定义
from langgraph.graph import StateGraph, START, END
# 导入基础存储接口
from langgraph.store.base import BaseStore
# 导入可运行配置类
from langchain_core.runnables import RunnableConfig
# 导入Postgres存储类
from langgraph.store.postgres import PostgresStore
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
# 导入 psycopg2 的操作异常类，用于捕获数据库连接错误
from psycopg2 import OperationalError
# 导入Postgres检查点保存类
from langgraph.checkpoint.postgres import PostgresSaver
# 导入PostgreSQL连接池类
from psycopg_pool import ConnectionPool, AsyncConnectionPool
# 导入Pydantic的基类和字段定义工具
from pydantic import BaseModel, Field, model_validator
# 导入自定义的get_llm函数，用于获取LLM模型
from utils.llms import get_llm
# 导入统一的 Config 类
from utils.config import Config
from typing import List
# # 设置日志基本配置，级别为DEBUG或INFO
logger = logging.getLogger(__name__)
# 设置日志器级别为DEBUG
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.INFO)
logger.handlers = []  # 清空默认处理器
# 使用ConcurrentRotatingFileHandler
# 定义消息状态类，使用TypedDict进行类型注解

PLANNER_EXAMPLES = [
    # 示例1: 复杂查询
    ("human", "根据研报，对比一下宁德时代和特斯拉的风险，并分别告诉我它们俩的最新股价。"),
    ("ai", """
    {
        "plan": {
            "thought": "The user wants a risk comparison from the report and real-time stock prices for two different companies from different markets. I need four steps: search the report for CATL's risks, search for Tesla's risks, get CATL's A-share price, and get Tesla's US stock price. I must use the correct price tool for each market.",
            "tasks": [
                {"task_id": 1, "tool_name": "search_financial_reports", "tool_args": {"query": "宁德时代的风险"}, "question": "研报中提到了宁德时代的哪些风险？"},
                {"task_id": 2, "tool_name": "search_financial_reports", "tool_args": {"query": "特斯拉的风险"}, "question": "研报中提到了特斯拉的哪些风险？"},
                {"task_id": 3, "tool_name": "get_internal_stock_price", "tool_args": {"symbol": "宁德时代"}, "question": "宁德时代的最新A股股价是多少？"},
                {"task_id": 4, "tool_name": "get_international_financial_product_price", "tool_args": {"symbol": "TSLA"}, "question": "特斯拉(TSLA)的最新股价是多少？"}
            ]
        },
        "chat_response": null
    }
    """),
    # 示例2: 简单RAG查询
    ("human", "这份报告的核心观点是什么？"),
    ("ai", """
    {
        "plan": {
            "thought": "The user is asking for the main summary of the report. A single step is sufficient.",
            "tasks": [
                {"task_id": 1, "tool_name": "search_financial_reports", "tool_args": {"query": "报告的核心观点和摘要"}, "question": "这份报告的核心观点是什么？"}
            ]
        },
        "chat_response": null
    }
    """),
    # 示例3: 简单聊天
    ("human", "你好"),
    ("ai", """
    {
        "plan": null,
        "chat_response": "您好！我是您的研报分析助手，有什么可以帮您的吗？"
    }
    """)
]


class Reflection(BaseModel):
    """
    承载对工具执行结果的深度反思。
    """
    assessment: Literal["success", "failure", "partial_success"] = Field(
        description="Assessment of the tool execution. 'success' if the answer is complete and accurate. 'partial_success' if the information is useful but incomplete. 'failure' if the result is an error, irrelevant, or contains no information."
    )
    
    reasoning: str = Field(
        description="A brief, critical explanation for the assessment. Explain what was good or what was missing."
    )
    
    suggestion_for_next_step: Optional[str] = Field(
        default=None,
        description="Actionable suggestion for the next step if assessment is not 'success'. E.g., 'Retry with a broader search term like financial risks', or 'The stock symbol might be wrong, try searching for the company name'."
    )
    
    # 新增字段
    is_sufficient: bool = Field(
        description="A boolean flag indicating if the information obtained is sufficient to stop the process, even if not a complete success."
    )

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
    
    plan: Optional[Plan] = Field(
        default=None, 
        description="A detailed, step-by-step plan if the query requires tool use. Should be null if a direct chat response is provided."
    )
    
    chat_response: Optional[str] = Field(
        default=None, 
        description="A direct response to the user if the query is a simple chat message that does not require any tools. Should be null if a plan is generated."
    )

    # 使用 @model_validator 对整个模型进行验证
    @model_validator(mode='after')
    def check_plan_or_response_exclusive(self) -> 'PlannerOutput':
        # 在 'after' 模式下，我们可以访问 self，即模型实例
        plan_exists = self.plan is not None
        response_exists = self.chat_response is not None

        # 规则1: 不能两个都存在
        if plan_exists and response_exists:
            raise ValueError("Either 'plan' or 'chat_response' can be provided, but not both.")
        
        # 规则2: 必须有一个存在
        if not plan_exists and not response_exists:
            raise ValueError("Either 'plan' or 'chat_response' must be provided.")
        
        # 验证通过，返回 self
        return self

class MessagesState(TypedDict):
    # 定义messages字段，类型为消息序列，使用add_messages处理追加
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # 定义plan字段，用于存储问题的计划
    plan: Optional[Plan]
    # 用于跟踪已完成的任务ID
    completed_tasks: List[int]
    # 定义reflection字段，用于存储反思结果
    reflection: Optional[Reflection]      

async def tool_executor_node(state: MessagesState,* , all_tools) -> dict:
    logger.info(">>Node：ToolExcutor")
    plan = state["plan"]
    next_task = None

    for task in plan.tasks:
        if task.status == "pending":
            next_task = task
            break

    if next_task is None:
        logger.info("No pending tasks found")
        return {}
    
    tool_2_call = all_tools[next_task.tool_name]
    logger.info(f"执行任务 #{next_task.task_id}，调用工具：{tool_2_call}")

    try:
        result = await tool_2_call.ainvoke(next_task.tool_args)
        result_str = str(result)

        next_task.status = "completed"
        next_task.result = result_str

    except Exception as e:
        logger.error(f"Error executing tool {next_task.tool_name}: {e}")
        next_task.status = "failed"
        next_task.result = str(e)

    tool_message = ToolMessage(
        content=next_task.result,
        name=next_task.tool_name,
        tool_call_id=f"call_{next_task.task_id}"
    )

    completed_tasks = state.get("completed_tasks", [])
    completed_tasks.append(next_task.task_id)
    

    return {"plan": plan, "completed_tasks": completed_tasks, "messages":[tool_message]}

def format_plan_results(plan: Plan) -> str:
    formatted_string = ""
    for task in plan.tasks:
        if task.status == "completed":
            formatted_string += f"Question:{task.question}\nAnswer:{task.result}\n"
        elif task.status == "failed":
            formatted_string += f"Question:{task.question}\nAttempt failed. Error: {task.result}\n\n"

    return formatted_string

async def synthesizer_node(state: MessagesState, *, llm_chat) -> dict:
    logger.info(">>Node：Synthesizer")

    synthesizer_chain = create_chain(llm_chat, Config.PROMPT_TEMPLATE_TXT_SYNTHESIZER)
    
    original_query = get_latest_question(state)
    plan_results = format_plan_results(state["plan"])

    fianl_answer = await synthesizer_chain.ainvoke({
        "original_query": original_query,
        "formatted_plan_results": plan_results
    })

    return {"messages": [fianl_answer]}

handler = ConcurrentRotatingFileHandler(
    # 日志文件
    Config.LOG_FILE,
    # 日志文件最大允许大小为5MB，达到上限后触发轮转
    maxBytes = Config.MAX_BYTES,
    # 在轮转时，最多保留3个历史日志文件
    backupCount = Config.BACKUP_COUNT
)
# 设置处理器级别为DEBUG
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logger.addHandler(handler)




# 文档相关性评分
class DocumentRelevanceScore(BaseModel):
    # 定义binary_score字段，表示相关性评分，取值为"yes"或"no"
    binary_score: str = Field(description="Relevance score 'yes' or 'no'")

# 自定义异常，表示数据库连接池初始化或状态异常
class ConnectionPoolError(Exception):
    """自定义异常，表示数据库连接池初始化或状态异常"""
    pass


# 定义获取最新问题的辅助函数
def get_latest_question(state: MessagesState) -> Optional[str]:
    """从状态中安全地获取最新用户问题。

    Args:
        state: 当前对话状态，包含消息历史。

    Returns:
        Optional[str]: 最新问题的内容，如果无法获取则返回 None。
    """
    try:
        # 检查状态是否包含消息列表且不为空
        if not state.get("messages") or not isinstance(state["messages"], (list, tuple)) or len(state["messages"]) == 0:
            logger.warning("No valid messages found in state for getting latest question")
            return None

        # 从后向前遍历消息，找到最近的 HumanMessage（用户输入）
        for message in reversed(state["messages"]):
            if message.__class__.__name__ == "HumanMessage" and hasattr(message, "content"):
                return message.content

        # 如果没有找到 HumanMessage，返回 None
        logger.info("No HumanMessage found in state")
        return None

    except Exception as e:
        logger.error(f"Error getting latest question: {e}")
        return None


# 定义线程内的持久化存储消息过滤函数
def filter_messages(messages: list) -> list:
    """过滤消息列表，仅保留 AIMessage 和 HumanMessage 类型消息"""
    # 过滤出 AIMessage 和 HumanMessage 类型的消息
    filtered = [msg for msg in messages if msg.__class__.__name__ in ['AIMessage', 'HumanMessage']]
    # 如果过滤后的消息超过N条，返回最后N条，否则返回过滤后的完整列表
    return filtered[-5:] if len(filtered) > 5 else filtered


# 定义跨线程的持久化存储的存储和过滤函数
async def store_memory(question: BaseMessage, config: RunnableConfig, store: BaseStore) -> str:
    """存储用户输入中的记忆信息。

    Args:
        question: 用户输入的消息。
        config: 运行时配置。
        store: 数据存储实例。

    Returns:
        str: 用户相关的记忆信息字符串。
    """
    # 在 store_memory 函数开头附近
    logger.debug(f"store_memory called with question content: {repr(question.content)}, type: {type(question.content)}")
    namespace = ("memories", config["configurable"]["user_id"])
    try:
                # 确保查询内容是有效的字符串
        query_content = ""
        if hasattr(question, 'content') and question.content:
            if isinstance(question.content, str):
                query_content = question.content.strip()
            elif isinstance(question.content, (list, tuple)):
                # 如果是列表或元组，提取字符串内容
                query_content = " ".join([str(item) for item in question.content if item])
            else:
                query_content = str(question.content).strip()
        
        # 验证查询内容不为空且是有效字符串
        if not query_content or len(query_content.strip()) == 0:
            logger.warning("Empty or invalid query content, skipping memory search")
            return ""
        
        # 限制查询长度，避免API限制
        if len(query_content) > 1000:
            query_content = query_content[:1000]
            logger.debug(f"Truncated query content to 1000 characters")
        
        logger.debug(f"Searching memories with query: {repr(query_content)}")
        # 在跨线程存储数据库中搜索相关记忆
        memories = await store.asearch(namespace, query=query_content)
        user_info = "\n".join([d.value["data"] for d in memories])

        # 如果包含“记住”，存储新记忆
        if "记住" in query_content.lower():
            memory = escape(query_content)
            await store.aput(namespace, str(uuid.uuid4()), {"data": memory})
            logger.info(f"Stored memory: {memory}")

        return user_info
    except Exception as e:
        logger.error(f"Error in store_memory: {e}")
        return ""


def format_examples_for_prompt(examples: list) -> str:
    """
    将 few-shot 示例列表格式化为单个字符串，以便注入到 prompt 模板中。
    """
    if not examples:
        return "" # 如果没有示例，返回空字符串
    
    formatted_str = ""
    for example_pair in examples:
        # 假设 example_pair 是 ("human", "...") 或 ("ai", "...") 的元组
        # 我们可以根据需要格式化它
        # 这里采用一种类似 Markdown 的格式
        if example_pair[0] == "human":
            formatted_str += f"*   **User Query**: \"{example_pair[1]}\"\n"
        elif example_pair[0] == "ai":
            formatted_str += f"*   **Your Output**:\n    ```json\n{example_pair[1].strip()}\n    ```\n\n"

    
            
    return formatted_str.strip()

# 我们暂时不考虑缓存，专注于核心逻辑
def create_chain(
    llm_chat: Any,
    template_file: str, 
    structured_output: Optional[Any] = None
):
    """
    从文件加载一个模板并创建一个 LLM Chain。
    模板中的所有变量都期望在 .ainvoke() 时被提供。
    """
    try:
        # 1. 直接使用 PromptTemplate.from_file 加载模板。
        # LangChain 会自动识别 {examples}, {query}, {history} 等占位符。
        prompt = PromptTemplate.from_file(template_file, encoding="utf-8")
        # 2. 转换为 ChatPromptTemplate 并组装 Chain
        # 我们假设整个模板都是 human message 的一部分
        chat_prompt = ChatPromptTemplate.from_messages([
            ("human", prompt.template)
        ])
        
        return chat_prompt | (llm_chat.with_structured_output(structured_output) if structured_output else llm_chat)
    except Exception as e:
            logger.error(f"Error getting latest question: {e}")
            return None


# 数据库重试机制,最多重试3次,指数退避等待2-10秒,仅对数据库操作错误重试
@retry(stop=stop_after_attempt(3),wait=wait_exponential(multiplier=1, min=2, max=10),retry=retry_if_exception_type(OperationalError))
def test_connection(db_connection_pool: ConnectionPool) -> bool:
    """测试连接池是否可用"""
    with db_connection_pool.getconn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result != (1,):
                raise ConnectionPoolError("连接池测试查询失败，返回结果异常")
    return True


# 周期性检查连接池状态，记录可用连接数和异常情况，提前预警
def monitor_connection_pool(db_connection_pool: ConnectionPool, interval: int = 60):
    """周期性监控连接池状态"""
    def _monitor():
        while not db_connection_pool.closed:
            try:
                stats = db_connection_pool.get_stats()
                active = stats.get("connections_in_use", 0)
                total = db_connection_pool.max_size
                logger.info(f"Connection db_connection_pool status: {active}/{total} connections in use")
                if active >= total * 0.8:
                    logger.warning(f"Connection db_connection_pool nearing capacity: {active}/{total}")
            except Exception as e:
                logger.error(f"Failed to monitor connection db_connection_pool: {e}")
            time.sleep(interval)

    monitor_thread = threading.Thread(target=_monitor, daemon=True)
    monitor_thread.start()
    return monitor_thread


async def planner_agent(state: MessagesState, config: RunnableConfig, *, store: BaseStore, llm_chat) -> dict:
    """代理函数，根据用户问题决定是否调用工具或结束。

    Args:
        state: 当前对话状态。
        config: 运行时配置。
        store: 数据存储实例。
        llm_chat: Chat模型。
        tool_config: 工具配置参数。

    Returns:
        dict: 更新后的对话状态。
    """
    # 记录代理开始处理查询
    logger.info("Planner Agent processing user query")
    # 定义存储命名空间，使用用户ID
    namespace = ("memories", config["configurable"]["user_id"])
    # 尝试执行以下代码块
    
    try:
        # 获取最后一条消息即用户问题
        question = state["messages"][-1]
        # 自定义线程内存储逻辑 过滤消息
        messages = filter_messages(state["messages"])
        logger.info(f"agent question:{question}")
        # 在 agent 函数中，获取 question 之后
        logger.debug(f"Processing question message: {type(question)}, content type: {type(question.content)}")
        # 自定义跨线程持久化存储记忆并获取相关信息
        user_info = await store_memory(question, config, store)
        examples_str = format_examples_for_prompt(PLANNER_EXAMPLES)
        # examples_chat_response_str = format_examples_for_prompt(PLANNER_EXAMPLES_CHAT_RESPONSE)
        # 创建代理处理链
        agent_chain = create_chain(llm_chat, Config.PLANNER_AGENT_PROMPT)
        # 调用代理链处理消息
        responses = await agent_chain.ainvoke({"query": question,"history": messages, "examples": examples_str})
        logger.info(f"Planner Agent response: {responses}")

        llm_output_str = responses.content
        logger.info(f"LLM Raw Output String:\n---\n{llm_output_str}\n---")

        # --- 调试步骤 2: 手动执行解析和验证 ---
        response = None
        try:
            # a. 从 Markdown 中提取 JSON
            import re
            import json
            from pydantic import ValidationError
            match = re.search(r"```(json)?\n(.*)```", llm_output_str, re.DOTALL)
            if match:
                print("it has markdown code")
                json_str = match.group(2)
            else:
                print("it has no markdown code")
                json_str = llm_output_str
            
            logger.info(f"Extracted JSON String:\n---\n{json_str}\n---")
            
            # b. 解析 JSON 字符串
            data_dict = json.loads(json_str)
            
            # c. 验证 Pydantic 模型
            response = PlannerOutput(**data_dict)
            
            logger.info("Manual parsing and validation successful!")

        except json.JSONDecodeError as e:
            logger.error(f"Manual JSON Decode Failed: {e}")
        except ValidationError as e:
            logger.error(f"Manual Pydantic Validation Failed: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during manual parsing: {e}")
        if response is None:
            logger.error("LLM failed to return a valid PlannerOutput object. It returned None.")
            # 当解析失败时，我们无法知道用户的意图，最好的做法是向用户请求澄清
            error_message = AIMessage(content="I'm sorry, I'm having trouble understanding your request. Could you please rephrase it?")
            print("\n" + "="*20 + " 最终答案 " + "="*20)
            print(f"🤖 **Assistant**: {error_message.content}")
            print("="*50 + "\n")
            # 返回一个明确的“无计划”状态
            return {**state, "messages": state["messages"] + [error_message], "plan": None}
        
        if response.chat_response:
            print("make a response")
            logger.info(f"Planner decided to chat directly. Response: {response.chat_response}")
            # 我们返回这个消息，并且 plan 为 None，这将导致图直接结束
            return {**state, "messages": [response.chat_response], "plan": None}
        elif response.plan:
            print("make a plan")
            logger.info(f"Planner created a new plan. Thought: {response.plan.thought}")
            # 返回新的计划，并清空 completed_tasks
            return {**state, "plan": response.plan, "completed_tasks": []}

        # 兜底情况，虽然 Pydantic validator 应该能阻止这种情况
        else:
            logger.error("Planner output was invalid (neither plan nor chat_response).")
            # 返回一个错误消息
            error_message = AIMessage(content="I'm sorry, I had trouble understanding that. Could you please rephrase?")
            return {**state, "messages": [error_message], "plan": None}

    except Exception as e:
        logger.error(f"Error in agent processing: {e}", exc_info=True)
        return {"messages": [{"role": "system", "content": "处理请求时出错"}]}


async def reflector_node(state: MessagesState, *, llm_chat) -> dict:
    logger.info(">>Node：Reflector")
    try:
        plan = state.get("plan")
        completed_tasks = state.get("completed_tasks", [])

        if not completed_tasks:
            return {"reflection": Reflection(assessment="success", reasoning="No tasks to reflect on.")}

        last_completed_id = completed_tasks[-1]
        last_task = next((task for task in plan.tasks if task.task_id == last_completed_id), None)

        if not last_task:
            logger.error(f"FATAL: Cannot find task with ID {last_completed_id} in the plan.")
            # 严重错误，强制失败
            return {"reflection": Reflection(assessment="failure", reasoning=f"Task ID {last_completed_id} not found in plan.")}
        logger.info(f"Reflecting on Task {last_task.task_id}: '{last_task.question}'")
        logger.info(f"Tool Result: '{str(last_task.result)[:500]}...'")

        reflector_chain = create_chain(llm_chat, Config.REFLECTOR_AGENT_PROMPT)
        reflection_result: Reflection = await reflector_chain.ainvoke({
            "question": last_task.question,
            "result": str(last_task.result)
        })
        llm_output_str = reflection_result.content
        # --- 调试步骤 2: 手动执行解析和验证 ---
        response = None
        try:
            # a. 从 Markdown 中提取 JSON
            import re
            import json
            from pydantic import ValidationError
            match = re.search(r"```(json)?\n(.*)```", llm_output_str, re.DOTALL)
            if match:
                print("it has markdown code")
                json_str = match.group(2)
            else:
                print("it has no markdown code")
                json_str = llm_output_str
            
            logger.info(f"Extracted JSON String:\n---\n{json_str}\n---")
            
            # b. 解析 JSON 字符串
            data_dict = json.loads(json_str)
            
            # c. 验证 Pydantic 模型
            response = Reflection(**data_dict)
            
            logger.info("Manual parsing and validation successful!")

        except json.JSONDecodeError as e:
            logger.error(f"Manual JSON Decode Failed: {e}")
        except ValidationError as e:
            logger.error(f"Manual Pydantic Validation Failed: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during manual parsing: {e}")
        reflection_result = response
        logger.info(f"Reflection Result: {reflection_result}")
        logger.info(f"Reflection Assessment: {reflection_result.assessment} | Reasoning: {reflection_result.reasoning}")
        return {"reflection": reflection_result}
    except (IndexError, KeyError) as e:
        logger.error(f"Message access error: {e}")
        return {
            "messages": [{"role": "system", "content": "无法评判任务"}],
            "reflection": None
        }
    except Exception as e:
        logger.error(f"Unexpected error in grading: {e}")
        return {
            "messages": [{"role": "system", "content": "评判任务过程中出错"}],
            "reflection": None
        }
        


async def replanner_node(state: MessagesState, *,llm_chat) -> dict:
    logger.info(">>Node：Replanner")
    try:
        last_reflection = state.get("reflection")
        original_plan = state.get("plan")
        completed_tasks = state.get("completed_tasks", [])

        if not last_reflection or not original_plan:
            logger.error("RePlanner called without reflection or plan. Aborting.")
            return {}

        last_completed_id = completed_tasks[-1] if completed_tasks else 0
        failed_task = next((task for task in original_plan.tasks if task.task_id == last_completed_id), original_plan.tasks[0])
        # 格式化原始计划，包含已成功的结果
        plan_with_results_str = ""
        for task in original_plan.tasks:
            plan_with_results_str += f"Task {task.task_id}: {task.question}\n"
            if task.task_id in completed_tasks:
                plan_with_results_str += f"  Status: Success\n  Result: {task.result}\n"
            elif task.task_id == failed_task.task_id:
                plan_with_results_str += f"  Status: Failed\n"
            else:
                plan_with_results_str += f"  Status: Pending\n"
        
        replanner_chain = create_chain(llm_chat, Config.REPLANNER_AGENT_PROMPT)

        new_plan = await replanner_chain.ainvoke({
            "original_plan_with_results": plan_with_results_str,
            "failed_task_id": failed_task.task_id,
            "failed_task_question": failed_task.question,
            "failure_reason": last_reflection.reasoning,
            "suggestion": last_reflection.suggestion_for_next_step
        })
        llm_output_str = new_plan.content
        response = None
        try:
            # a. 从 Markdown 中提取 JSON
            import re
            import json
            from pydantic import ValidationError
            match = re.search(r"```(json)?\n(.*)```", llm_output_str, re.DOTALL)
            if match:
                print("it has markdown code")
                json_str = match.group(2)
            else:
                print("it has no markdown code")
                json_str = llm_output_str
            
            logger.info(f"Extracted JSON String:\n---\n{json_str}\n---")
            
            # b. 解析 JSON 字符串
            data_dict = json.loads(json_str)
            
            # c. 验证 Pydantic 模型
            response = PlannerOutput(**data_dict)
            
            logger.info("Manual parsing and validation successful!")

        except json.JSONDecodeError as e:
            logger.error(f"Manual JSON Decode Failed: {e}")
        except ValidationError as e:
            logger.error(f"Manual Pydantic Validation Failed: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during manual parsing: {e}")
        new_plan = response
        logger.info(f"Replanning complete. New plan has {len(new_plan.plan.tasks)} tasks.")
        logger.info(f"New plan: {new_plan.plan}")
        return {"plan": new_plan.plan}
    except (IndexError, KeyError) as e:
        # 记录错误日志
        logger.error(f"Message access error in replanner: {e}")
        # 返回错误消息
        return {"messages": [{"role": "system", "content": "无法重写查询"}]}
        



    
def decide_next_step(state: MessagesState) -> Literal["end", "continue", "replanner"]:
    reflection = state.get("reflection")
    if reflection and reflection.assessment == "failure":
        logger.info("Reflection indicates failure. Routing to RePlanner.")
        return "replanner"

    plan = state.get("plan")
    completed_tasks = state.get("completed_tasks", [])
    if not plan or len(completed_tasks) == len(plan.tasks):
        logger.info("Plan completed or does not exist. Routing to end.")
        return "end"
    else:
        logger.info("Plan not completed. Routing to continue.")
        return "continue"
    
def decide_after_planner(state: MessagesState) -> Literal["end", "call_tool"]:
    if state.get("plan") and state["plan"].tasks:
        logger.info("Plan exists and has tasks. Routing to call_tool.")
        return "call_tool"
    else:
        logger.info("Plan does not exist or has no tasks. Routing to end.")
        return "end"
    


# 保存状态图的可视化表示
def save_graph_visualization(graph: StateGraph, filename: str = "graph.png") -> None:
    """保存状态图的可视化表示。

    Args:
        graph: 状态图实例。
        filename: 保存文件路径。
    """
    # 尝试执行以下代码块
    try:
        # 以二进制写模式打开文件
        with open(filename, "wb") as f:
            # 将状态图转换为Mermaid格式的PNG并写入文件
            f.write(graph.get_graph().draw_mermaid_png())
        # 记录保存成功的日志
        logger.info(f"Graph visualization saved as {filename}")
    # 捕获IO错误
    except IOError as e:
        # 记录警告日志
        logger.warning(f"Failed to save graph visualization: {e}")


# 创建并配置状态图
def create_graph(db_connection_pool: ConnectionPool, llm_chat, llm_embedding, all_tools) -> StateGraph:
    """创建并配置状态图。

    Args:
        db_connection_pool: 数据库连接池。
        llm_chat: Chat模型。
        llm_embedding: Embedding模型。
        all_tools: 工具配置字典。

    Returns:
        StateGraph: 编译后的状态图。

    Raises:
        ConnectionPoolError: 如果连接池未正确初始化或状态异常。
    """
    if db_connection_pool is None or db_connection_pool.closed:
        logger.error("Connection db_connection_pool is None or closed")
        raise ConnectionPoolError("数据库连接池未初始化或已关闭")
    try:
        # 获取当前活动连接数和最大连接数
        active_connections = db_connection_pool.get_stats().get("connections_in_use", 0)
        max_connections = db_connection_pool.max_size
        if active_connections >= max_connections:
            logger.error(f"Connection db_connection_pool exhausted: {active_connections}/{max_connections} connections in use")
            raise ConnectionPoolError("连接池已耗尽，无可用连接")
        if not test_connection(db_connection_pool):
            raise ConnectionPoolError("连接池测试失败")
        logger.info("Connection db_connection_pool status: OK, test connection successful")
    except OperationalError as e:
        logger.error(f"Database operational error during connection test: {e}")
        raise ConnectionPoolError(f"连接池测试失败，可能已关闭或超时: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to verify connection db_connection_pool status: {e}")
        raise ConnectionPoolError(f"无法验证连接池状态: {str(e)}")

    # 线程内持久化存储
    try:
        # 创建Postgres检查点保存实例
        checkpointer = PostgresSaver(db_connection_pool)
        # 初始化检查点
        checkpointer.setup()
    except Exception as e:
        logger.error(f"Failed to setup PostgresSaver: {e}")
        raise ConnectionPoolError(f"检查点初始化失败: {str(e)}")

    # try:
    # # 临时使用内存 Checkpointer
    #     from langgraph.checkpoint.memory import MemorySaver
    #     checkpointer = MemorySaver()
    #     logger.info("使用内存 Checkpointer（开发/测试模式）")
    # except Exception as e:
    #     logger.error(f"Failed to setup MemorySaver: {e}")
    #     raise ConnectionPoolError(f"检查点初始化失败: {str(e)}")

    # 跨线程持久化存储
    try:
        # 创建Postgres存储实例，指定嵌入维度和函数
        store = PostgresStore(db_connection_pool, index={"dims": 1024, "embed": llm_embedding})
        store.setup()
    except Exception as e:
        logger.error(f"Failed to setup PostgresStore: {e}")
        raise ConnectionPoolError(f"存储初始化失败: {str(e)}")

    workflow = StateGraph(MessagesState)
    # 添加代理节点
    agent_with_args = functools.partial(
                                planner_agent, 
                                store=store, 
                                llm_chat=llm_chat, 
                            )
    tool_executor_node_with_args = functools.partial(
                                tool_executor_node,
                                all_tools=all_tools
                            )
    synthesizer_node_with_args = functools.partial(
                                synthesizer_node,
                                llm_chat=llm_chat
                            )
    reflector_node_with_args = functools.partial(
                                reflector_node,
                                llm_chat=llm_chat
                            )
    replanner_node_with_args = functools.partial(
                                replanner_node,
                                llm_chat=llm_chat
                            )
    
    workflow.add_node("planner_agent", agent_with_args)
    # 添加工具节点，使用并行工具节点
    workflow.add_node("call_tools", tool_executor_node_with_args)
    # 添加重写节点
    workflow.add_node("replanner", replanner_node_with_args)
    # 添加生成节点
    workflow.add_node("synthesizer", synthesizer_node_with_args)
    # 添加文档相关性评分节点
    workflow.add_node("reflector", reflector_node_with_args)

    # 添加从起始到代理的边
    workflow.add_edge(START, end_key="planner_agent")
    # 添加代理的条件边，根据工具调用的工具名称决定下一步路由
    workflow.add_conditional_edges(source="planner_agent", path=decide_after_planner, path_map={"end": END, "call_tool": "call_tools"})
    # 添加检索的条件边，根据工具调用的结果动态决定下一步路由
    workflow.add_edge(start_key="call_tools", end_key="reflector")
    # 添加检索的条件边，根据状态中的评分结果决定下一步路由
    workflow.add_conditional_edges(source="reflector", path=decide_next_step, path_map={"end": "synthesizer", "replanner": "replanner","continue": "call_tools"})
    # 添加从生成到结束的边
    workflow.add_edge(start_key="synthesizer", end_key=END)
    # 添加从重写到代理的边
    workflow.add_edge(start_key="replanner", end_key="call_tools")

    # 编译状态图，绑定检查点和存储
    return workflow.compile(checkpointer=checkpointer, store=store)


# 定义响应函数
async def graph_response(graph: StateGraph, user_input: str, config: dict) -> None:
    """
    一个适配规划型 Agent 的响应函数。
    它会像解说一样，实时展示 Agent 的思考、计划、行动和最终答案。
    """
    logger.info("="*50)
    logger.info(f"开始处理新查询: '{user_input}'")
    logger.info("="*50)

    try:
        # 初始状态，明确所有字段
        initial_state = {
            "messages": [("user", user_input)],
            "plan": None,
            "completed_tasks": [],
            "reflection": None,
        }
        
        # 启动事件流
        events = graph.astream(initial_state, config)
        
        # 遍历事件流
        async for event in events:
            # event 的键就是当前执行完毕的节点名
            node_name = list(event.keys())[0]
            state_update = event[node_name]

            # --- 像解说员一样，根据节点名打印不同的信息 ---

            if node_name == "planner":
                plan = state_update.get("plan")
                if plan and plan.tasks:
                    print(f"🤔 **思考与规划中...**")
                    print(f"   - 核心思路: {plan.thought}")
                    print(f"   - 制定了 {len(plan.tasks)} 个步骤的计划：")
                    for task in plan.tasks:
                        print(f"     - 步骤 {task.task_id}: 使用工具 `{task.tool_name}` 来回答 '{task.question}'")

            elif node_name == "tool_executor":
                # 从 state_update 中获取最新的 plan 和 messages
                plan = state_update.get("plan")
                last_message = state_update.get("messages", [])[-1] if state_update.get("messages") else None

                if plan and isinstance(last_message, ToolMessage):
                    # 找到刚刚执行的任务
                    last_completed_id = state_update.get("completed_tasks", [])[-1]
                    completed_task = next((t for t in plan.tasks if t.task_id == last_completed_id), None)
                    
                    if completed_task:
                        print(f"🛠️ **执行任务中...** (步骤 {completed_task.task_id}/{len(plan.tasks)})")
                        print(f"   - 调用工具: `{completed_task.tool_name}`")
                        print(f"   - 工具参数: {completed_task.tool_args}")
                        # 打印部分结果，避免刷屏
                        print(f"   - 获得结果: '{completed_task.result[:150]}...'")

            elif node_name == "reflector":
                reflection = state_update.get("reflection")
                if reflection:
                    if reflection.assessment == "success":
                        print(f"✅ **反思结果: 成功**")
                        print(f"   - 评估: 工具结果有效。")
                    else:
                        print(f"❌ **反思结果: 失败**")
                        print(f"   - 评估: {reflection.reasoning}")
                        if reflection.suggestion_for_next_step:
                             print(f"   - 建议: {reflection.suggestion_for_next_step}")

            elif node_name == "replanner":
                new_plan = state_update.get("plan")
                if new_plan:
                    print(f"🔄 **调整计划中...**")
                    print(f"   - 原始计划存在问题，正在生成新计划...")
                    # 可以在这里打印新计划的 thought

            elif node_name == "synthesizer":
                final_answer_message = state_update.get("messages", [])[-1] if state_update.get("messages") else None
                if final_answer_message:
                    print("\n" + "="*20 + " 最终答案 " + "="*20)
                    print(f"🤖 **Assistant**: {final_answer_message.content}")
                    print("="*50 + "\n")
            
            # 可以在这里加一个 pprint(event) 来进行深度调试
            # from pprint import pprint
            # pprint(event)

    except Exception as e:
        logger.error(f"处理响应时发生严重错误: {e}", exc_info=True)
        print("\n❌ **错误**: 处理您的请求时发生了一个内部错误。请稍后再试。")

# 定义一个辅助函数来异步获取输入
async def ainput(prompt: str = ""):
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: input(prompt)
    )
# 定义主函数
async def main():
    """主函数，初始化并运行聊天机器人。"""
    # 初始化连接池为None
    db_connection_pool = None
    try:
        # 调用get_llm函数初始化Chat模型实例和Embedding模型实例
        llm_chat, llm_embedding = get_llm(Config.LLM_TYPE)
        client = MultiServerMCPClient(
            {
                "finMCPServer": {
                    "command": "python",
                    # Make sure to update to the full absolute path to your math_server.py file
                    "args": ["finMCPServer.py"],
                    "transport": "stdio",
                }
            }
        )

        # 获取工具列表
        # tools = get_tools(llm_embedding)
        tools = await client.get_tools()
        all_tools = {tool.name: tool for tool in tools}


        # 定义数据库连接参数，自动提交且无预准备阈值，5秒超时
        connection_kwargs = {"autocommit": True, "prepare_threshold": 0, "connect_timeout": 5}
        db_connection_pool = ConnectionPool(conninfo=Config.DB_URI, max_size=20, min_size=2, kwargs=connection_kwargs, timeout=10)
        # 创建状态图
        try:
            graph = create_graph(db_connection_pool, llm_chat, llm_embedding, all_tools)
        except ConnectionPoolError as e:
            logger.error(f"Graph creation failed: {e}")
            print(f"错误: {e}")
            sys.exit(1)


        # 保存状态图可视化
        save_graph_visualization(graph)

        # 打印机器人就绪提示
        print("聊天机器人准备就绪！输入 'quit'、'exit' 或 'q' 结束对话。")
        # 定义运行时配置，包含线程ID和用户ID
        config = {"configurable": {"thread_id": "1", "user_id": "1"}}
        # 进入主循环
        while True:
            # 获取用户输入并去除首尾空格
            #user_input = input("User: ").strip()
            user_input = (await ainput("User: ")).strip()
            # 检查是否退出
            if user_input.lower() in {"quit", "exit", "q"}:
                print("拜拜!")
                break
            # 检查输入是否为空
            if not user_input:
                print("请输入聊天内容！")
                continue
            # 处理用户输入并选择是否流式输出响应
            await graph_response(graph, user_input, config)

    except ConnectionPoolError as e:
        # 捕获连接池相关的异常
        logger.error(f"Connection pool error: {e}")
        print(f"错误: 数据库连接池问题 - {e}")
        sys.exit(1)
    except RuntimeError as e:
        # 捕获其他运行时错误
        logger.error(f"Initialization error: {e}")
        print(f"错误: 初始化失败 - {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        # 捕获键盘中断
        print("\n被用户打断。再见！")
    except Exception as e:
        # 捕获未预期的其他异常
        logger.error(f"Unexpected error: {e}")
        print(f"错误: 发生未知错误 - {e}")
        sys.exit(1)
    finally:
        # 清理资源
        if db_connection_pool and not db_connection_pool.closed:
            db_connection_pool.close()
            logger.info("Database connection pool closed")


# 检查是否为主模块运行
if __name__ == "__main__":
    # 调用主函数
    asyncio.run(main())