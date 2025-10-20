import json
import uuid
from typing import List, Tuple
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.storage import InMemoryStore
from reportParsers import RobustReportParser
import logging
import re

# 假设第一步的 RobustReportParser 已经在一个名为 report_parser.py 的文件中
# from report_parser import RobustReportParser 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedChunkingStrategy:
    """
    一个先进的切分策略，它首先将初步文档合并成逻辑完整的“父文档”，
    然后再将父文档切分成用于检索的“子文档”。
    """
    
    def __init__(self, preliminary_docs: List[Document]):
        self.preliminary_docs = preliminary_docs
        # 子文档切分器，用于创建更小的、适合精确检索的块
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,  # 较小的 chunk_size 以提高检索精度
            chunk_overlap=50,
            length_function=len,
        )
        # 文档存储区，用于存储父文档
        self.docstore = InMemoryStore()

    def chunk(self) -> Tuple[List[Document], InMemoryStore]:
        """
        执行完整的父子文档切分策略。
        
        Returns:
            Tuple[List[Document], InMemoryStore]: 
                - 一个包含所有子文档的列表，用于存入向量数据库。
                - 一个包含所有父文档的 InMemoryStore。
        """
        logger.info("开始第二步：父子文档切分策略...")
        
        parent_docs = [] # 用于临时存放合并好的父文档
        child_docs_for_indexing = [] # 最终要存入向量库的子文档

        # --- 步骤 A: 通过上下文组合，创建逻辑完整的父文档 ---
        i = 0
        while i < len(self.preliminary_docs):
            doc = self.preliminary_docs[i]
            chunk_type = doc.metadata.get("chunk_type")

            # 逻辑1: 组合标题及其后续段落，形成一个父文档
            if chunk_type == "title":
                current_title_doc = doc
                content_docs_text = []
                
                j = i + 1
                while j < len(self.preliminary_docs):
                    next_doc = self.preliminary_docs[j]
                    if next_doc.metadata.get("chunk_type") in ["title", "figure"]:
                        break # 遇到下一个标题或图片时停止
                    content_docs_text.append(next_doc.page_content)
                    j += 1
                
                title_text = current_title_doc.page_content
                paragraphs_text = "\n".join(content_docs_text)
                full_content = f"{title_text}\n\n{paragraphs_text}".strip()
                
                metadata = current_title_doc.metadata.copy()
                if "核心观点" in title_text:
                    metadata['final_chunk_type'] = 'summary'
                elif "风险提示" in title_text:
                    metadata['final_chunk_type'] = 'risk_warning'
                else:
                    metadata['final_chunk_type'] = 'section'
                
                parent_docs.append(Document(page_content=full_content, metadata=metadata))
                i = j
                continue

            # 逻辑2: 将图表及其相关信息视为一个父文档
            elif chunk_type == "figure":
                # (这个逻辑可以根据需要进一步完善，比如合并标题和来源)
                parent_docs.append(doc) # 暂时将图表描述本身作为一个父文档
                i += 1
                continue

            # 其他独立的、有意义的块也可以作为父文档
            else:
                if len(doc.page_content) > 100: # 过滤掉太短的无用文本
                     parent_docs.append(doc)
                i += 1
        
        logger.info(f"步骤 A 完成: 已合并生成 {len(parent_docs)} 个逻辑完整的父文档。")

        # --- 步骤 B: 基于父文档，创建子文档并存入 docstore ---
        parent_ids = [str(uuid.uuid4()) for _ in parent_docs]
        
        # 1. 将父文档存入 docstore
        self.docstore.mset(list(zip(parent_ids, parent_docs)))
        
        # 2. 从父文档创建子文档
        for i, p_doc in enumerate(parent_docs):
            parent_id = parent_ids[i]
            # 对父文档的内容进行二次切分
            sub_docs = self.child_splitter.split_documents([p_doc])
            # 为每个子文档添加 parent_id 元数据
            for _doc in sub_docs:
                _doc.metadata["parent_id"] = parent_id
            child_docs_for_indexing.extend(sub_docs)
            
        logger.info(f"步骤 B 完成: 已生成 {len(child_docs_for_indexing)} 个子文档用于向量索引。")
        logger.info("第二步完成。")
        
        return child_docs_for_indexing, self.docstore

if __name__ == '__main__':
    # ... (加载 JSON, 初始化 embedding_function) ...
    try:
        with open("./utils/20250807.json", 'r', encoding='utf-8') as f:
            report_json_data = json.load(f)
        # --- 第一步：解析 ---
        parser = RobustReportParser(report_json_data)
        preliminary_docs = parser.parse()

        # --- 第二步：切分 ---
        # 现在 chunker 返回两个值
        chunker = AdvancedChunkingStrategy(preliminary_docs)
        child_docs, docstore = chunker.chunk() 
        
        # --- 1. 总体统计信息 ---
        print("\n--- 1. 总体统计信息 ---")
        num_parent_docs = len(list(docstore.yield_keys()))
        num_child_docs = len(child_docs)
        print(f"-> 成功生成了 {num_parent_docs} 个逻辑完整的父文档。")
        print(f"-> 基于父文档，共切分出 {num_child_docs} 个用于向量索引的子文档。")
        if num_parent_docs > 0:
            avg_chunks_per_parent = num_child_docs / num_parent_docs
            print(f"-> 平均每个父文档被切分为 {avg_chunks_per_parent:.2f} 个子文档。")
        
        # --- 2. 父文档 (Parent Document) 示例 ---
        print("\n--- 2. 父文档 (Parent Document) 示例 ---")
        print("父文档是逻辑完整的单元，存储在 docstore 中，用于最终返回给 LLM。")
        
        # 随机抽取一个父文档的 key (ID)
        if num_parent_docs > 0:
            sample_parent_id = list(docstore.yield_keys())[1]
            sample_parent_doc = docstore.mget([sample_parent_id])[0]
            
            print("\n  [示例父文档]:")
            print(f"  ID: {sample_parent_id}")
            print(f"  内容预览 (前250个字符): '{sample_parent_doc.page_content[:250].replace(chr(10), ' ')}...'")
            print(f"  内容总长度: {len(sample_parent_doc.page_content)} 字符")
            print(f"  元数据: {sample_parent_doc.metadata}")
        else:
            print("  未生成任何父文档。")

        # --- 3. 子文档 (Child Document) 示例 ---
        print("\n--- 3. 子文档 (Child Document) 示例 ---")
        print("子文档是更小的文本块，将被存入向量数据库用于精确检索。")

        if num_child_docs > 0:
            # 找到与上面那个父文档关联的子文档
            related_child_docs = [doc for doc in child_docs if doc.metadata.get("parent_id") == sample_parent_id]
            
            if related_child_docs:
                print(f"\n  以下是与上述父文档 (ID: {sample_parent_id[:8]}...) 关联的 {len(related_child_docs)} 个子文档:")
                for i, child in enumerate(related_child_docs):
                    print(f"\n    [子文档 {i+1}]:")
                    print(f"    内容 (完整): '{child.page_content}'")
                    print(f"    内容长度: {len(child.page_content)} 字符")
                    print(f"    元数据: {child.metadata}")
            else:
                print("\n  [随机示例子文档]:")
                sample_child_doc = child_docs[0]
                print(f"  内容 (完整): '{sample_child_doc.page_content}'")
                print(f"  内容长度: {len(sample_child_doc.page_content)} 字符")
                print(f"  元数据: {sample_child_doc.metadata}")
        else:
            print("  未生成任何子文档。")
        
        print("\n" + "="*50)
        print("          分析结束")
        print("="*50)
        logger.info("数据处理和入库全部完成！")
    except FileNotFoundError:
        logger.error("错误: 20250728.json 文件未找到。")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)
