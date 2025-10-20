# retrieval_strategy.py (续)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_community.chat_models.tongyi import ChatTongyi
import os
import logging
from sentence_transformers import CrossEncoder
from typing import List, Dict, Any, Literal, Optional 
from langchain_core.documents import Document

from typing import List, Dict, Any, Literal
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from sentence_transformers import CrossEncoder
import logging
import textwrap

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.environ["DASHSCOPE_API_KEY"] = "sk-cf312af820bb4841a707fc4284f147a4"
class Config:
    CHROMADB_DIRECTORY = "chromaDB"
    # 这是我们之前步骤中填充了数据的集合
    CHROMADB_COLLECTION_NAME = "ESG" 
    RERANKER_MODEL_NAME = 'BAAI/bge-reranker-base'
embedding_function = DashScopeEmbeddings(model="text-embedding-v4", dashscope_api_key="sk-cf312af820bb4841a707fc4284f147a4")


class Reranker:
    def __init__(self, model_name='BAAI/bge-reranker-base'):
        # 加载一个强大的、开源的重排模型
        self.model = CrossEncoder(model_name)
        logger.info(f"重排模型 '{model_name}' 加载成功。")

    def rerank(self, query: str, documents: List[Document], top_n: int = 3) -> List[Document]:
        """对文档列表进行重排，并返回得分最高的 top_n 个文档。"""
        if not documents:
            return []
        pairs = []
        for doc in documents:
            # 结合标题和内容，为 reranker 提供更丰富的上下文
            context = f"章节: {doc.metadata.get('hierarchy', '')}\n内容: {doc.page_content}"
            pairs.append([query, context])
        logger.info(f"开始对 {len(documents)} 个文档进行重排...")
        
        # 创建 [查询, 文档内容] 对
        pairs = [[query, doc.page_content] for doc in documents]
        
        # 计算得分，得分越高越好
        scores = self.model.predict(pairs)
        
        # 将得分附加到文档上并排序
        for doc, score in zip(documents, scores):
            doc.metadata['rerank_score'] = score
            
        # 按重排得分降序排序
        sorted_docs = sorted(documents, key=lambda x: x.metadata['rerank_score'], reverse=True)
        
        logger.info("重排完成。")
        # 返回前 top_n 个结果
        return sorted_docs[:top_n]



# 1. 定义 LLM Router 的输出结构
class RetrievalIntent(BaseModel):
    """
    定义了检索意图的结构，LLM 将输出这个格式。
    """
    retrieval_mode: Literal["risk", "summary", "figure_table", "section", "general"] = Field(
        description="The identified retrieval mode based on the user's query."
    )
    term: Optional[str] = Field(
        None,
        description="The specific search term, required for 'section' or 'figure_table' modes. For example, '经济影响' or 'GDP增速的图表'."
    )

# 2. 创建 LLMRouter 类
class LLMRouter:
    """
    一个使用 LLM 来识别用户检索意图的路由器。
    """
    def __init__(self, llm):
        # 创建一个带有 structured_output 功能的 LLM 实例
        self.structured_llm = llm.with_structured_output(RetrievalIntent)
        
        # 定义提示模板
        self.prompt = ChatPromptTemplate.from_template(
            """
            You are an expert at understanding user queries for a financial report analysis system.
            Your task is to analyze the user's query and determine the best retrieval strategy.

            Here are the available retrieval modes:
            - "risk": Use this for questions about risks, challenges, downsides, or potential problems.
            - "summary": Use this for general questions about the report's core ideas, summary, abstract, or main points.
            - "figure_table": Use this for questions specifically asking for a chart, graph, table, or specific data points.
            - "section": Use this for questions about a specific chapter or section of the report.
            - "general": Use this for all other questions that don't fit the above categories.

            If the mode is "section" or "figure_table", you MUST extract the specific search term. Otherwise, the term should be null.

            User Query:
            "{query}"

            Output the retrieval intent in the specified JSON format.
            """
        )
        
        # 组装成一个 LCEL 链
        self.chain: Runnable = self.prompt | self.structured_llm

    def recognize(self, query: str) -> RetrievalIntent:
        """
        使用 LLM 链来识别意图。
        """
        logger.info(f"使用 LLM Router 识别查询: '{query}'")
        try:
            return self.chain.invoke({"query": query})
        except Exception as e:
            logger.error(f"LLM Router 调用失败: {e}. 将回退到 'general' 模式。", exc_info=True)
            # 设计一个回退机制，保证系统在 LLM 出错时依然可用
            return RetrievalIntent(retrieval_mode="general", term=None)


# retrieval_strategy.py (续)

# 假设 CoreRetrievers 和 Reranker 类已经定义好
# 假设 RetrievalIntent 和 LLMRouter 类也已经定义好

class CoreRetrievers:
    """
    一个封装了基础检索器（相似度搜索和MMR）的类。
    """
    def __init__(self, top_k: int = 10):
        try:
            # 连接到已存在的 ChromaDB 集合
            self.vectorstore = Chroma(
                persist_directory=Config.CHROMADB_DIRECTORY,
                collection_name=Config.CHROMADB_COLLECTION_NAME,
                embedding_function=embedding_function
            )
            logger.info(f"成功连接到 ChromaDB 集合 '{Config.CHROMADB_COLLECTION_NAME}'")
        except Exception as e:
            logger.error(f"连接到 ChromaDB 失败: {e}", exc_info=True)
            raise

        # 创建标准相似度检索器
        self.similarity_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k}
        )

        # 创建 MMR 检索器
        # fetch_k > k 是一个好习惯
        self.mmr_retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": top_k, "fetch_k": top_k * 2}
        )
        
    def search_similarity(self, query: str, top_k: Optional[int] = None) -> List[Document]:
        """
        执行标准相似度搜索。
        
        Args:
            query (str): 用户的查询。
            top_k (Optional[int]): 要检索的文档数量。如果为 None，则使用类初始化时设置的默认值。
            
        Returns:
            List[Document]: 检索到的文档列表。
        """
        # 如果调用时没有指定 top_k，就使用类初始化时设定的默认值
        k = top_k if top_k is not None else 3
        
        # 动态创建 retriever，并传入当前的 k 值
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        
        return retriever.get_relevant_documents(query)

    def search_mmr(self, query: str) -> List[Document]:
        return self.mmr_retriever.get_relevant_documents(query)

    def search_with_filter(self, query: str, filter_dict: Dict[str, Any], top_k: int = 5) -> List[Document]:
        """执行带元数据过滤的向量搜索"""
        filtered_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k, "filter": filter_dict}
        )
        return filtered_retriever.get_relevant_documents(query)


class SmartRetriever:
    """
    一个集成了 LLM 意图识别、多策略检索和重排的智能检索器。
    """
    def __init__(self, llm, initial_k: int = 10, final_k: int = 3):
        # --- 核心改动：用 LLMRouter 替换 IntentRecognizer ---
        self.router = LLMRouter(llm)
        # ---------------------------------------------------
        
        self.core_retrievers = CoreRetrievers(top_k=initial_k)
        self.reranker = Reranker()
        self.final_k = final_k
        logger.info("智能检索器 (SmartRetriever) [LLM-Powered] 初始化完成。")

    def retrieve(self, query: str) -> List[Document]:
        logger.info(f"\n===== 开始智能检索 (LLM-Powered)，查询: '{query}' =====")
        
        # --- 核心改动：调用 LLMRouter ---
        # 1. 意图识别
        intent_obj = self.router.recognize(query)
        intent = intent_obj.retrieval_mode
        term = intent_obj.term
        logger.info(f"LLM Router 识别到意图: '{intent}', 关键词: '{term}'")
        # ----------------------------------
        
        candidate_docs = []
        
        # 2. 根据意图执行不同的检索策略 (这部分逻辑几乎不变)
        if intent == "risk":
            logger.info("--> 策略: 元数据过滤 (风险)")
            candidate_docs = self.core_retrievers.search_with_filter(query, {"chunk_type": "risk"})
        
        elif intent == "summary":
            logger.info("--> 策略: 元数据过滤 (摘要)")
            candidate_docs = self.core_retrievers.search_with_filter(query, {"chunk_type": "summary"})

        elif intent == "figure_table" and term:
            logger.info(f"--> 策略: 元数据过滤 (图表/表格: {term})")
            candidate_docs = self.core_retrievers.search_with_filter(term, {"chunk_type": {"$in": ["figure"]}})
        
        elif intent == "section" and term:
            logger.info(f"--> 策略: 广泛搜索后进行Python过滤 (章节: {term})")
            
            # 1. 先进行一次广泛的相似度搜索
            # 我们可以稍微增加 k 的值，以确保相关的章节不会被漏掉
            initial_docs = self.core_retrievers.search_similarity(query, top_k=5)

            filter_condition = {"hierarchy": {"$like": f"%{term}%"}}

            # 2. 调用数据库，数据库内部会先过滤再搜索
            candidate_docs = self.core_retrievers.search_with_filter(
                query, 
                filter_dict=filter_condition,
                top_k=5) 

            # 3. 最终重排
            if not candidate_docs:
                logger.warning("所有检索策略均未找到任何文档。")
                return []
                
            logger.info("--> 开始最终重排...")
            reranked_docs = self.reranker.rerank(query, candidate_docs+initial_docs, top_n=self.final_k)
            
            logger.info(f"===== 智能检索结束，返回 Top {len(reranked_docs)} 个文档 =====")
            return reranked_docs

        # 如果是通用问题，或者精确打击没找到结果，就用混合搜索
        if intent == "general" or not candidate_docs:
            if not candidate_docs and intent != "general":
                logger.info("精确打击未找到结果，切换到混合向量搜索策略。")
            else:
                logger.info("--> 策略: 混合向量搜索")

            sim_docs = self.core_retrievers.search_similarity(query)
            mmr_docs = self.core_retrievers.search_mmr(query)
            
            all_docs = sim_docs + mmr_docs
            unique_docs_map = {doc.page_content: doc for doc in all_docs}
            candidate_docs = list(unique_docs_map.values())
            
        logger.info(f"初步检索完成，共获得 {len(candidate_docs)} 个候选文档。")
        
        # 3. 最终重排 (无变化)
        if not candidate_docs:
            logger.warning("所有检索策略均未找到任何文档。")
            return []
            
        logger.info("--> 开始最终重排...")
        reranked_docs = self.reranker.rerank(query, candidate_docs, top_n=self.final_k)
        
        logger.info(f"===== 智能检索结束，返回 Top {len(reranked_docs)} 个文档 =====")
        return reranked_docs


# --- 示例用法 (在 if __name__ == "__main__": 中) ---
if __name__ == "__main__":
    # 初始化一个用于路由的 LLM (可以用一个速度快、成本低的模型)
    # 确保你的 API Key 环境变量已设置
    routing_llm = ChatTongyi(model_name="qwen-plus", streaming=True)


    # 实例化新的 SmartRetriever
    smart_retriever = SmartRetriever(llm=routing_llm, initial_k=10, final_k=3)
    
    # 测试的 queries 列表保持不变
    queries = [
        "有关上海打造国际绿色金融枢纽的报告的核心观点是什么？",# 通用问题，可以测试拼写错误
    ]
    
    for q in queries:
        final_results = smart_retriever.retrieve(q)
        print(f"\n--- 最终结果 for query: '{q}' ---")
        if not final_results:
            print("未找到相关内容。")
        else:
            for i, doc in enumerate(final_results):
                score = doc.metadata.get('rerank_score', 'N/A')
                               # 1. 准备要打印的内容
                # 我们不再替换换行符，让 textwrap 处理
                content_to_print = doc.page_content
                
                # 2. 使用 textwrap.fill 进行格式化
                # width=80:  设置每行最大宽度为80个字符 (您可以根据您的终端调整)
                # initial_indent='    ':  设置第一行的缩进 (4个空格)
                # subsequent_indent='    ': 设置后续所有行的缩进 (4个空格)
                formatted_content = textwrap.fill(
                    content_to_print, 
                    width=80, 
                    initial_indent='    ', 
                    subsequent_indent='    '
                )
                
                # 3. 打印格式化后的内容
                print(f"  Top {i+1} (Score: {score:.4f}) | Source: {doc.metadata.get('hierarchy', 'N/A')}")
                print(f"  Content:")
                print(formatted_content)
                print("-" * 20)
                