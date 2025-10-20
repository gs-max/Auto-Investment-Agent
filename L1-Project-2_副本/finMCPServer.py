import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from langchain_chroma import Chroma
import akshare as ak
import yfinance as yf
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
import os
from retrival import SmartRetriever
os.environ["DASHSCOPE_API_KEY"] = "sk-cf312af820bb4841a707fc4284f147a4"
load_dotenv()
# 初始化嵌入模型（服务端一次性加载）
# embedding_model = OpenAIEmbeddings(
#     model="text-embedding-v4",  # 指定阿里云模型
#     api_key=os.getenv("LLM_API_KEY"),
#     base_url=os.getenv("LLM_BASE_URL")
# )
embedding_model = DashScopeEmbeddings(
    model="text-embedding-v4", dashscope_api_key=os.getenv("LLM_API_KEY")
)
# 初始化向量存储
vectorstore = Chroma(
    persist_directory="chromaDB",
    collection_name="AIDC_Report_Collection_Chunks",
    embedding_function=embedding_model,
)
retriever = vectorstore.as_retriever()


# 日志相关配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("calculator_mcp_server")

# 初始化 FastMCP 服务器，指定服务名称为 "finTools"
mcp = FastMCP("finTools")
ROUTING_LLM = ChatTongyi(model_name="qwen-plus", streaming=True)
SMART_RETRIEVER_INSTANCE = SmartRetriever(llm=ROUTING_LLM)

@mcp.tool()
def search_financial_reports(query: str) -> str:
    """
    智能研报检索引擎。输入一个自然语言问题，它会分析意图、执行多策略检索并重排，最终返回最相关的文本片段。
    这是获取研报内部信息的首选工具。
    
    Args:
        query (str): 用户的查询问题，例如 "中芯国际的风险有哪些？" 或 "对比A公司和B公司的财务状况"。
        
    Returns:
        str: 格式化后的、最相关的检索结果字符串。如果未找到，则返回提示信息。
    """
    logger.info(f"MCP工具 'search_financial_reports' 被调用，查询: '{query}'")
    
    try:
        # --- 核心逻辑：调用全局的 SMART_RETRIEVER_INSTANCE ---
        retrieved_docs: List[Document] = SMART_RETRIEVER_INSTANCE.retrieve(query)
        
        # --- 格式化输出 ---
        # Agent 更喜欢处理纯文本。我们将 Document 对象列表转换成一个易于阅读的字符串。
        if not retrieved_docs:
            return "未在知识库中找到相关内容。"
        
        output_parts = []
        for i, doc in enumerate(retrieved_docs):
            source = doc.metadata.get('hierarchy', '未知来源')
            score = doc.metadata.get('rerank_score', 0)
            content = doc.page_content
            
            # 格式化每一条结果
            part = (f"--- 相关片段 {i+1} (相关性得分: {score:.4f}) ---\n"
                    f"来源: {source}\n"
                    f"内容: {content}\n"
                    f"-----------------------------------------\n")
            output_parts.append(part)
            
        return "\n".join(output_parts)

    except Exception as e:
        logger.error(f"执行 'search_financial_reports' 工具时发生错误: {e}", exc_info=True)
        # 向 Agent 返回一个清晰的错误信息
        return f"检索时发生内部错误: {str(e)}"

@mcp.tool()
def get_international_financial_product_price(symbol: str) -> str:
    """
    查询国际金融产品价格，支持：
    - 美股:AAPL, TSLA等
    - ETF:SPY, QQQ等
    - 加密:BTC-USD等
    - 期货:GC=F(黄金)、CL=F(原油)等
    - 指数:^GSPC等
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info  # 基本信息
        hist = ticker.history(period="1d")  # 最近行情
        
        if hist.empty:
            return f"❌ 找不到 {symbol} 的数据"

        current_price = hist['Close'].iloc[-1]
        currency = info.get('currency', 'USD')
        name = info.get('longName', symbol)
        
        return f"🌍 {name} ({symbol})\n当前价：{current_price:.2f} {currency}"
    
    except Exception as e:
        return f"❌ 查询失败：{str(e)}"

@mcp.tool()
def get_internal_stock_price(symbol: str) -> str:
    """
    查询A股实时行情（支持中文名或代码）
    示例输入: "宁德时代", "300750"
    """
    raise Exception("API limit reached")
    # try:
    #     # 获取A股实时行情数据
    #     df = ak.stock_zh_a_spot_em()
        
    #     if df.empty:
    #         return "❌ 获取股票数据失败：数据为空"

    #     # 支持股票代码（如 300750）或中文名（如 宁德时代）
    #     if symbol.isdigit():
    #         # 是代码
    #         result = df[df['代码'] == symbol]
    #     else:
    #         # 是名字
    #         result = df[df['名称'] == symbol]

    #     if len(result) == 0:
    #         return f"❌ 未找到股票 '{symbol}'，请检查名称或代码是否正确"

    #     row = result.iloc[0]
    #     price = row['最新价']
    #     change_pct = row['涨跌幅']
    #     name = row['名称']
    #     code = row['代码']
        
    #     return f"📊 {name} ({code})\n当前价：{price} 元\n涨跌幅：{change_pct}%"
    
    # except Exception as e:
    #     return f"❌ 查询失败：{str(e)}"


# 主程序入口
if __name__ == "__main__":
    # 初始化并运行 FastMCP 服务器，使用标准输入输出作为传输方式
    mcp.run(transport='stdio')