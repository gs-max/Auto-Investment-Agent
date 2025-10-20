# vectorSave.py (修改版，使用 PDFMinerLoader 获取文本，然后使用自定义逻辑分块)
import os
import re
import logging
from openai import OpenAI
import chromadb
import uuid
from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain_community.document_loaders import PDFMinerLoader # 你用来成功加载PDF的库
from langchain.docstore.document import Document as LangchainDocument # 导入 Langchain Document 类
from dotenv import load_dotenv # 用于加载环境变量
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List
from langchain_community.embeddings import DashScopeEmbeddings
# --- 1. 加载环境变量 ---
load_dotenv()

# --- 2. 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name='BAAI/bge-reranker-base'):
        # 加载一个强大的、开源的重排模型
        self.model = CrossEncoder(model_name)
        logger.info(f"重排模型 '{model_name}' 加载成功。")

    def rerank(self, query: str, documents: List[Document], top_n: int = 3) -> List[Document]:
        """对文档列表进行重排，并返回得分最高的 top_n 个文档。"""
        if not documents:
            return []
            
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


# --- 3. 配置 LLM 和 Embedding (从环境变量或使用默认值) ---
# 优先从环境变量加载，如果没有则使用代码中的默认值
QWen_API_BASE = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip() # 去掉可能的末尾空格
QWen_EMBEDDING_API_KEY = os.getenv("QWEN_EMBEDDING_API_KEY", "sk-cf312af820bb4841a707fc4284f147a4") # 强烈建议从 .env 文件获取
QWen_EMBEDDING_MODEL = os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v4")

from langchain_chroma import Chroma
from langchain_core.documents import Document

class HybridRetriever:
    def __init__(self, collection_name, embedding_fn, top_k=5):
        # LangChain 的 Chroma 包装器，用于方便地使用 MMR 等高级功能
        self.lc_chroma = Chroma(
            client=chromadb.PersistentClient(path="chromaDB"),
            collection_name=collection_name,
            embedding_function=embedding_fn
        )
        self.top_k = top_k

    def similarity_search(self, query: str) -> List[Document]:
        """策略1: 标准相似度搜索"""
        logger.info(f"执行标准相似度搜索...")
        # 使用 LangChain 的 retriever 更方便
        retriever = self.lc_chroma.as_retriever(search_type="similarity", search_kwargs={"k": self.top_k})
        return retriever.get_relevant_documents(query)

    def mmr_search(self, query: str) -> List[Document]:
        """策略2: 最大边界相关性 (MMR) 搜索"""
        logger.info(f"执行 MMR 搜索...")
        # fetch_k > k 是 MMR 的一个最佳实践，它会先取回更多文档，再在这些文档中进行多样性选择
        retriever = self.lc_chroma.as_retriever(search_type="mmr", search_kwargs={"k": self.top_k, "fetch_k": self.top_k * 2})
        return retriever.get_relevant_documents(query)

    def retrieve(self, query: str) -> List[Document]:
        """合并两种策略的结果并去重"""
        logger.info(f"开始混合检索，查询: '{query}'")
        
        # 并行执行两种搜索策略 (如果需要高性能，可以使用 asyncio.gather)
        sim_docs = self.similarity_search(query)
        mmr_docs = self.mmr_search(query)
        
        # 合并结果
        all_docs = sim_docs + mmr_docs
        
        # 去重
        unique_docs_map = {doc.page_content: doc for doc in all_docs}
        unique_docs = list(unique_docs_map.values())
        
        logger.info(f"混合检索完成。总计找到 {len(all_docs)} 个文档，去重后剩 {len(unique_docs)} 个。")
        return unique_docs


# --- 4. 定义文本处理函数 ---

# 当处理中文文本时，按照标点进行断句
def sent_tokenize(input_string):
    """将输入字符串按中文标点分割成句子"""
    if not input_string:
        return []
    sentences = re.split(r'(?<=[。！？；?!])', input_string)
    # 去掉空字符串和纯空白字符
    return [sentence.strip() for sentence in sentences if sentence.strip()]

# 模拟从PDF提取文本并按行组织 (因为我们已经有了文本，这步简化)
# 但保留逻辑：将所有文本合并，然后按空行分段落
def organize_text_into_paragraphs(full_text: str, min_line_length: int = 1) -> list:
    """
    将一大段文本模拟成按行读取并重组为段落的过程。
    这里简化处理：直接按双换行符 \n\n 分割段落。
    你可以根据需要替换为更复杂的逻辑。
    """
    logger.debug("开始组织文本成段落...")
    if not full_text.strip():
        logger.warning("输入的全文为空")
        return []

    # 按双换行符分割段落 (模拟按空行分隔)
    raw_paragraphs = re.split(r'\n\s*\n', full_text)
    
    paragraphs = []
    buffer = ''
    
    for para in raw_paragraphs:
        lines = para.split('\n') # 模拟将段落再按单行处理
        for text in lines:
            text = text.strip()
            if len(text) >= min_line_length:
                # 简单的行拼接逻辑，这里简化处理
                buffer += (' ' + text) if buffer else text
            elif buffer:
                # 空行或短行，表示当前buffer段落结束
                paragraphs.append(buffer)
                buffer = ''
        # 段落结束，添加buffer
        if buffer:
            paragraphs.append(buffer)
            buffer = ''
            
    # 处理最后可能剩余的buffer
    if buffer:
        paragraphs.append(buffer)
        
    logger.debug(f"组织完成，共得到 {len(paragraphs)} 个段落")
    # 可以打印前几个段落检查
    # for i, p in enumerate(paragraphs[:3]):
    #     logger.debug(f"段落 {i+1}: {p[:100]}...")
    return paragraphs

# 将段落列表按一定粒度，部分重叠式地切割文本
def split_text(paragraphs: list, chunk_size: int = 200, overlap_size: int = 50) -> list:
    """
    将段落列表按指定大小和重叠进行切割，生成最终的文本块。
    """
    logger.debug("开始切割文本...")
    if not paragraphs:
        logger.warning("输入段落列表为空")
        return []

    # 1. 将所有段落按句子分割
    sentences = [s.strip() for p in paragraphs for s in sent_tokenize(p) if s.strip()]
    if not sentences:
        logger.warning("段落中未分割出任何句子")
        return []

    logger.debug(f"共分割出 {len(sentences)} 个句子")

    chunks = []
    i = 0
    while i < len(sentences):
        # 2. 构建当前chunk的主体
        chunk = sentences[i]
        next_idx = i + 1

        # 3. 向后添加句子，直到达到chunk_size
        while next_idx < len(sentences):
            next_sentence = sentences[next_idx]
            # 简单估算加入下一个句子后的总长度
            if len(chunk) + len(next_sentence) + 1 <= chunk_size:
                chunk += ' ' + next_sentence
                next_idx += 1
            else:
                break

        # 4. 添加重叠（向前）
        overlap = ''
        prev_idx = i - 1
        while prev_idx >= 0 and len(overlap) + len(sentences[prev_idx]) <= overlap_size:
            overlap = sentences[prev_idx] + ' ' + overlap
            prev_idx -= 1

        # 5. 组合最终的chunk
        final_chunk = (overlap + chunk).strip()
        if final_chunk:
            chunks.append(final_chunk)

        # 6. 移动到下一个独立块的开始
        i = next_idx

    logger.debug(f"文本切割完成，共生成 {len(chunks)} 个文本块")
    # 可以打印前几个块检查
    # for i, c in enumerate(chunks[:3]):
    #     logger.debug(f"文本块 {i+1}: {c[:100]}...")
    return chunks

# --- 5. 定义向量生成函数 ---
def get_embeddings(texts):
    """使用阿里云 Qwen API 生成文本嵌入向量"""
    # 过滤掉空字符串
    valid_texts = [text for text in texts if isinstance(text, str) and text.strip()]
    if not valid_texts:
        logger.warning("get_embeddings received no valid texts to process")
        return []

    try:
        client = OpenAI(
            base_url=QWen_API_BASE,
            api_key=QWen_EMBEDDING_API_KEY
        )
        logger.debug(f"Calling embedding API for {len(valid_texts)} texts...")
        response = client.embeddings.create(input=valid_texts, model=QWen_EMBEDDING_MODEL)
        embeddings = [item.embedding for item in response.data]
        logger.debug(f"Received {len(embeddings)} embeddings")
        # 增加长度检查
        if len(embeddings) != len(valid_texts):
             logger.error(f"Mismatch in embeddings count: requested {len(valid_texts)}, got {len(embeddings)}")
             return []
        return embeddings
    except Exception as e:
        logger.error(f"生成向量时出错: {e}")
        return []

# --- 6. 定义批处理函数 ---
def generate_vectors(data, max_batch_size=10): # *** 关键修改：将 max_batch_size 从 25 改为 10 ***
    """对文本按批次进行向量计算"""
    if not data:
        logger.warning("generate_vectors received empty data")
        return []
    results = []
    total_items = len(data)
    total_batches = (total_items - 1) // max_batch_size + 1
    for i in range(0, total_items, max_batch_size):
        batch = data[i:i + max_batch_size]
        current_batch_num = i // max_batch_size + 1
        logger.info(f"Processing batch {current_batch_num}/{total_batches} (size: {len(batch)})")
        response = get_embeddings(batch)
        if response and len(response) == len(batch): # 增加长度检查
            results.extend(response)
        else:
            logger.warning(f"Batch {current_batch_num} failed or mismatch, skipping {len(batch)} items. Response length: {len(response) if response else 'None'}")
    logger.info(f"Finished processing all batches. Total embeddings generated: {len(results)}")
    return results

# --- 7. 定义 ChromaDB 的嵌入函数 ---
class MyEmbeddingFunction(EmbeddingFunction):
    def __init__(self): # 添加 __init__ 修复警告
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return generate_vectors(input)

# --- 8. 定义向量数据库连接器 ---
class MyVectorDBConnector:
    def __init__(self, collection_name, embedding_fn):
        self.db_directory = "chromaDB"
        os.makedirs(self.db_directory, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=self.db_directory)
        self.collection = chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_fn = embedding_fn

    def add_documents(self, documents):
        """添加 LangChain Document 对象列表到集合"""
        if not documents:
             logger.warning("No documents provided to add_documents")
             return

        # 提取文本内容和元数据 (这里元数据可能需要合并页码等信息)
        texts = [doc.page_content for doc in documents if hasattr(doc, 'page_content') and isinstance(doc.page_content, str) and doc.page_content.strip()]
        # 为分块后的文档创建新的元数据，可以包含来源页码等信息
        metadatas = [doc.metadata for doc in documents if hasattr(doc, 'page_content') and isinstance(doc.page_content, str) and doc.page_content.strip()]
        ids = [str(uuid.uuid4()) for _ in texts]

        if not texts:
            logger.warning("No valid text content found in documents")
            return

        logger.info(f"准备添加 {len(texts)} 个文档到向量库...")
        try:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info("文档添加成功!")
        except Exception as e:
            logger.error(f"添加文档时出错: {e}", exc_info=True)

    def search(self, query, top_n=5):
        """检索向量数据库"""
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning("查询内容为空或无效")
            return []
        try:
            results = self.collection.query(
                query_texts=[query.strip()],
                n_results=top_n
            )
            return results
        except Exception as e:
            logger.error(f"检索向量数据库时出错: {e}", exc_info=True)
            return []

# --- 9. 主函数：加载PDF，处理文本，存入向量库 ---
def vectorStoreSave():
    INPUT_PDF = "input/20250728-甬兴证券-AIDC行业专题（一）：智算中心加速扩张，政策+需求双轮驱动供电系统升级.pdf"
    CHROMADB_COLLECTION_NAME = "AIDC_Report_Collection_Chunks"

    # 1. 使用 PDFMinerLoader 加载 PDF (你已验证成功的方法)
    logger.info("开始加载PDF...")
    loader = PDFMinerLoader(
        INPUT_PDF,
        mode="page", # 关键：按页加载
        pages_delimiter="\n-------THIS IS A CUSTOM END OF PAGE-------\n"
    )
    page_docs = loader.load() # List of Document, each representing a page
    logger.info(f"PDF加载完成，共 {len(page_docs)} 页。")
    for doc in page_docs:
        print(doc.page_content)
    # print(page_docs[0].page_content)

    # 2. 将所有页面的文本合并成一个大字符串
    logger.info("合并所有页面文本...")
    full_text = "\n\n".join([doc.page_content for doc in page_docs if doc.page_content.strip()]) # 用双换行符分隔页面
    logger.info(f"合并后文本总长度: {len(full_text)} 字符")

    # 3. 使用自定义逻辑组织段落
    # logger.info("组织文本成段落...")
    # paragraphs = organize_text_into_paragraphs(full_text, min_line_length=1)
    # if not paragraphs:
    #     logger.error("未能从合并文本中组织出段落")
    #     return

    # 4. 使用自定义逻辑切割段落成更小的文本块
    logger.info("将段落切割成文本块...")
    text_splitter = RecursiveCharacterTextSplitter(
        separators = ["\n\n", "\n", ".", " ", ""],
        chunk_size = 200,
        chunk_overlap = 20,
        length_function = len,
    )
    text_chunks = text_splitter.split_text(full_text)
    print(f"文本被分割成 {len(text_chunks)} 个块。")
    # text_chunks = split_text(full_text, chunk_size=800, overlap_size=200)
    # if not text_chunks:
    #     logger.error("未能生成任何文本块")
    #     return
    # logger.info(f"文本处理完成，共生成 {len(text_chunks)} 个文本块。")

    # 5. 将文本块转换为 Langchain Document 对象列表 (可选：添加元数据)
    logger.info("将文本块封装为 Document 对象...")
    
    chunk_docs = [LangchainDocument(page_content=chunk, metadata={"source": INPUT_PDF, "chunk_id": i}) for i, chunk in enumerate(text_chunks)]
    logger.info(f"封装完成，共 {len(chunk_docs)} 个 Document 对象。")

    # 6. 初始化向量数据库连接器
    logger.info("初始化向量数据库...")
    embedding_fn = MyEmbeddingFunction()
    vector_db = MyVectorDBConnector(CHROMADB_COLLECTION_NAME, embedding_fn)

    # 7. 将文档块添加到向量数据库
    logger.info("开始将文档块添加到向量库...")
    vector_db.add_documents(chunk_docs)

    # 8. 测试检索
    logger.info("进行检索测试...")
    # 测试查询1：直接相关
    user_query1 = "文中提到了有关英伟达的什么信息？"
    search_results1 = vector_db.search(user_query1, top_n=2)
    logger.info(f"检索 '{user_query1}' 的结果:")
    _print_search_results(search_results1)

    # 测试查询2：具体技术
    user_query2 = "HVDC相比UPS有哪些优势？"
    search_results2 = vector_db.search(user_query2, top_n=2)
    logger.info(f"检索 '{user_query2}' 的结果:")
    _print_search_results(search_results2)

    # 测试查询3：具体公司
    user_query3 = "研报的核心观点是什么？"
    search_results3 = vector_db.search(user_query3, top_n=2)
    logger.info(f"检索 '{user_query3}' 的结果:")
    _print_search_results(search_results3)

def _print_search_results(search_results):
    """辅助函数：打印检索结果"""
    if search_results and 'documents' in search_results and search_results['documents']:
        # 遍历每个 top_k 结果 (这里是 top_2)
        for i in range(len(search_results['documents'])): 
            print(f"\n--- 相关文档块 {i+1} ---")
            
            # 打印文档内容 (可能包含多个，但通常只有一个)
            doc_list = search_results['documents'][i]
            if doc_list:
                for j, doc_text in enumerate(doc_list): # 遍历文档列表 (虽然通常只有一个)
                    print(f"内容 {j+1}: {doc_text[:300]}...")
            else:
                print("内容: 无")

            # 打印元数据 (可能包含多个，但通常只有一个)
            metadata_list = search_results.get('metadatas', [])[i] if i < len(search_results.get('metadatas', [])) else []
            if metadata_list:
                for k, metadata in enumerate(metadata_list): # 遍历元数据列表 (虽然通常只有一个)
                    print(f"元数据 {k+1}: {metadata}")
            else:
                print("元数据: N/A")

            # 打印距离 (如果需要)
            distance_list = search_results.get('distances', [])[i] if i < len(search_results.get('distances', [])) else []
            if distance_list:
                 for l, distance in enumerate(distance_list):
                     print(f"距离 {l+1}: {distance}") # 越小越相似
            # else: # 距离可能不总是返回，可以不打印

    else:
        logger.info("未检索到相关结果。")





if __name__ == "__main__":
    # vectorStoreSave()
    # print("\n向量库构建流程结束。")
    embedding_model = DashScopeEmbeddings(
    model="text-embedding-v4", dashscope_api_key="sk-cf312af820bb4841a707fc4284f147a4")
    # 1. 初始化混合检索器
    collection_name = "financial_reports_collection"
    hybrid_retriever = HybridRetriever(collection_name=collection_name, embedding_fn=embedding_model, top_k=5)

    # 2. 初始化重排器
    reranker = Reranker()

    # 3. 定义最终的检索函数
    def search_and_rerank(query: str, final_top_n: int = 3) -> List[Document]:
        # a. 使用混合策略进行初步检索
        retrieved_docs = hybrid_retriever.retrieve(query)
        
        # b. 对检索结果进行重排
        reranked_docs = reranker.rerank(query, retrieved_docs, top_n=final_top_n)
        
        return reranked_docs
    
    user_query3 = "研报所展示的核心观点是什么？"
    search_results3 = search_and_rerank(user_query3, final_top_n=3)
    print(f"\n最终检索和重排结果 for query: '{user_query3}':\n")
    for i, doc in enumerate(search_results3):
        print(f"--- Top {i+1} (Score: {doc.metadata['rerank_score']:.4f}) ---")
        print(doc.page_content)
        print(f"Metadata: {doc.metadata}")
        print("-" * 20)

