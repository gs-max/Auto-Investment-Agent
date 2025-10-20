import uuid
import chromadb
import logging
from typing import List, Dict, Any
from langchain_core.documents import Document
from chunk_new import AdvancedChunkingStrategy
from reportParsers import RobustReportParser
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
import json
logger = logging.getLogger(__name__)

import hashlib

def generate_deterministic_id(doc: Document) -> str:
    # 使用文档内容和一些关键元数据来生成哈希值
    unique_string = doc.page_content + str(doc.metadata.get('pageNum')) + doc.metadata.get('hierarchy', '')
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

class MyVectorDBConnector:
    def __init__(self, collection_name, embedding_function=None):
        """
        初始化 ChromaDB 连接器。
        注意：原生 chromadb 客户端使用自己的嵌入函数处理方式。
        我们将在这里传递一个 embedding_function 对象，但在 add_documents 时手动使用它。
        """
        self.db_directory = "chromaDB"
        self.chroma_client = chromadb.PersistentClient(path=self.db_directory)
        
        # 在这里，我们不把 embedding_function 传给 get_or_create_collection
        # 因为 LangChain 的 embedding function 对象和 chromadb 内置的可能不完全兼容
        # 我们将在添加时手动生成嵌入
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # 保存 LangChain 的嵌入函数对象
        self.embedding_fn = embedding_function
        logger.info(f"向量数据库连接器初始化完成，集合: '{collection_name}'")

    def add_documents(self, documents: List[Document], batch_size: int = 10):
        """
        将 LangChain Document 对象列表批量添加到 ChromaDB 集合中。
        """
        if not documents:
             logger.warning("没有提供任何文档用于添加。")
             return

        # 确保我们有一个可用的嵌入函数
        if not hasattr(self.embedding_fn, 'embed_documents'):
            logger.error("提供的 embedding_function 对象没有 embed_documents 方法。")
            raise ValueError("无效的嵌入函数对象")

        logger.info(f"准备将 {len(documents)} 个文档块分批添加到向量库...")

        # 分批处理
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            
            # 1. 提取文本、元数据和生成唯一ID
            texts = [doc.page_content for doc in batch_docs]
            metadatas = [doc.metadata for doc in batch_docs]
            # ids = [doc.metadata.get("uniqueId", str(uuid.uuid4())) for doc in batch_docs]
            ids = [generate_deterministic_id(doc) for doc in batch_docs]

            # 过滤掉空的文本块
            valid_indices = [i for i, text in enumerate(texts) if text.strip()]
            if not valid_indices:
                logger.warning(f"批次 {i//batch_size + 1} 中没有有效的文本内容，跳过。")
                continue
            
            texts = [texts[i] for i in valid_indices]
            metadatas = [metadatas[i] for i in valid_indices]
            ids = [ids[i] for i in valid_indices]

            try:
                logger.info(f"正在处理批次 {i//batch_size + 1}/{len(documents)//batch_size + 1}，包含 {len(texts)} 个文档...")
                
                # 2. 手动为批次文本生成嵌入 (这是与 LangChain 集成的关键)
                embeddings = self.embedding_fn.embed_documents(texts)

                # 3. 添加到 ChromaDB 集合
                self.collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"批次 {i//batch_size + 1} 添加成功!")

            except Exception as e:
                logger.error(f"添加批次 {i//batch_size + 1} 的文档时出错: {e}", exc_info=True)
        
        logger.info("所有文档批次处理完成。")
        
    def get_collection_count(self) -> int:
        """获取集合中文档的数量"""
        return self.collection.count()

    # search 方法可以保持不变，但为了完整性，我们把它也放在这里
    def search(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        # ... (这个方法可以根据需要实现，例如用于测试)
        pass

if __name__ == '__main__':
    try:
        # --- 准备工作 ---
        # 1. 初始化嵌入模型 (只需要一次)
        logger.info("正在初始化嵌入模型...")
        # 注意：这里需要你根据自己的配置来实例化 llm_embedding
        embedding_function = DashScopeEmbeddings(
            model="text-embedding-v4", dashscope_api_key="sk-cf312af820bb4841a707fc4284f147a4"
        )
        logger.info("嵌入模型初始化成功。")
        
        # 2. 加载原始 JSON 数据
        logger.info("正在加载 JSON 文件...")
        with open("./utils/20250806.json", 'r', encoding='utf-8') as f:
            report_json_data = json.load(f)
        logger.info("JSON 文件加载成功。")

        # --- 第一步：解析与重组 ---
        parser = RobustReportParser(report_json_data)
        preliminary_docs = parser.parse()

        # --- 第二步：核心切分 ---
        chunker = AdvancedChunkingStrategy(preliminary_docs)
        final_chunks = chunker.chunk()
        logger.info(f"成功生成 {len(final_chunks)} 个最终文档块。")

        # --- 第三步：向量化与入库 ---
        collection_name = "ESG"
        
        # 3. 初始化数据库连接器
        db_connector = MyVectorDBConnector(
            collection_name=collection_name,
            embedding_function=embedding_function
        )

        # 4. 执行添加文档
        logger.info(f"开始将文档块添加到集合 '{collection_name}'...")
        db_connector.add_documents(final_chunks)
        
        # 5. 验证结果
        final_count = db_connector.get_collection_count()
        logger.info(f"所有文档块添加完成！集合 '{collection_name}' 中现在共有 {final_count} 个文档。")

    except Exception as e:
        logger.error(f"整个处理流程发生严重错误: {e}", exc_info=True)


