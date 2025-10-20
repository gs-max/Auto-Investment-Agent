import os
import logging
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain.chat_models import init_chat_model
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
#from langchain_qwq import ChatQwQ




os.environ["DASHSCOPE_API_KEY"] = "sk-cf312af820bb4841a707fc4284f147a4"


# 设置日志模版
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 模型配置字典
MODEL_CONFIGS = {
    # "openai": {
    #     "base_url": os.getenv("OPENAI_BASE_URL"),
    #     "api_key": os.getenv("OPENAI_API_KEY"),
    #     "chat_model": "gpt-4o",
    #     "embedding_model": "text-embedding-3-small"
    # },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-cf312af820bb4841a707fc4284f147a4",
        "chat_model": "qwen-plus",
        "embedding_model": "text-embedding-v3"
     },
    # "oneapi": {
    #     "base_url": "http://139.224.72.218:3000/v1",
    #     "api_key": os.getenv("DASHSCOPE_API_KEY"),
    #     "chat_model": "qwen-max",
    #     "embedding_model": "text-embedding-v1"
    # },
    # "ollama": {
    #     "base_url": "http://localhost:11434/v1",
    #     "api_key": "ollama",
    #     "chat_model": "qwen2.5:32b",
    #     "embedding_model": "bge-m3:latest"
    
}


# 默认配置
DEFAULT_LLM_TYPE = "qwen"
DEFAULT_TEMPERATURE = 0.5


class LLMInitializationError(Exception):
    """自定义异常类用于LLM初始化错误"""
    pass


def initialize_llm(llm_type: str = DEFAULT_LLM_TYPE) -> tuple[ChatOpenAI, OpenAIEmbeddings]:
    """
    初始化LLM实例

    Args:
        llm_type (str): LLM类型，可选值为 'openai', 'oneapi', 'qwen', 'ollama'

    Returns:
        ChatOpenAI: 初始化后的LLM实例

    Raises:
        LLMInitializationError: 当LLM初始化失败时抛出
    """
    try:
        # 检查llm_type是否有效
        if llm_type not in MODEL_CONFIGS:
            raise ValueError(f"不支持的LLM类型: {llm_type}. 可用的类型: {list(MODEL_CONFIGS.keys())}")

        config = MODEL_CONFIGS[llm_type]

        # 特殊处理 ollama 类型
        if llm_type == "ollama":
            os.environ["OPENAI_API_KEY"] = "NA"

        # 创建LLM实例
        # llm_chat = ChatOpenAI(
        #     base_url=config["base_url"],
        #     api_key=config["api_key"],
        #     model=config["chat_model"],
        #     temperature=DEFAULT_TEMPERATURE,
        #     timeout=30,  # 添加超时配置（秒）
        #     max_retries=2  # 添加重试次数
        # )
        llm_chat = ChatTongyi(
            model_name="qwen-turbo",
            streaming=True
        )
        # llm_chat = ChatQwQ(
        #     model="qwq-plus",
        #     max_tokens=3_000,
        #     timeout=None,
        #     max_retries=2,

        # )

        llm_embeddings = DashScopeEmbeddings(
            model="text-embedding-v2",  dashscope_api_key="sk-cf312af820bb4841a707fc4284f147a4"
        )

        logger.info(f"成功初始化 {llm_type} LLM")
        return llm_chat, llm_embeddings

    except ValueError as ve:
        logger.error(f"LLM配置错误: {str(ve)}")
        raise LLMInitializationError(f"LLM配置错误: {str(ve)}")
    except Exception as e:
        logger.error(f"初始化LLM失败: {str(e)}")
        raise LLMInitializationError(f"初始化LLM失败: {str(e)}")


def get_llm(llm_type: str = DEFAULT_LLM_TYPE) -> ChatOpenAI:
    """
    获取LLM实例的封装函数，提供默认值和错误处理

    Args:
        llm_type (str): LLM类型

    Returns:
        ChatOpenAI: LLM实例
    """
    try:
        return initialize_llm(llm_type)
    except LLMInitializationError as e:
        logger.warning(f"使用默认配置重试: {str(e)}")
        if llm_type != DEFAULT_LLM_TYPE:
            return initialize_llm(DEFAULT_LLM_TYPE)
        raise  # 如果默认配置也失败，则抛出异常


# 示例使用
if __name__ == "__main__":
    try:
        # 测试不同类型的LLM初始化
        #llm_openai = get_llm("qwen")
        llm_qwen, llm_qwen_embedding = get_llm("qwen")
        try:
            # --- 方法 1: 使用 embed_query 测试单个文本 ---
            print("正在测试 embed_query...")
            
            embedding = llm_qwen_embedding.embed_query("你好，世界！")
            
            # 检查返回结果
            if isinstance(embedding, list) and len(embedding) > 0:
                print(f"✅ embed_query 测试成功!")
                print(f"   返回向量维度: {len(embedding)}") 
                # 如果是 text-embedding-v4，维度应该是 1792
                if len(embedding) == 1024:
                    print(f"   ✅ 向量维度符合 text-embedding-v4 预期 (1024)")
                else:
                    print(f"   ⚠️  向量维度 ({len(embedding)}) 与 text-embedding-v4 预期 (1024) 不符")
                print(f"   向量示例 (前10维): {embedding[:10]}")
            else:
                print(f"❌ embed_query 测试失败: 返回结果不是有效的向量列表。返回值: {embedding}")

        except Exception as e:
            print(f"❌ embed_query 测试失败，发生异常: {e}")

        # 测试无效类型
        llm_invalid = get_llm("invalid_type")
    except LLMInitializationError as e:
        logger.error(f"程序终止: {str(e)}")