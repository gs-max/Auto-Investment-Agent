import json
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
import re
# 假设 ReportParser 在 report_parser.py 中
from reportParsers import RobustReportParser 
from langchain.storage import InMemoryStore
import uuid
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedChunkingStrategy:
    """
    一个更先进的切分策略，通过单次遍历来识别和组合逻辑单元，
    以处理 ReportParser 输出的初步文档列表。
    """
    
    def __init__(self, preliminary_docs: List[Document]):
        self.preliminary_docs = preliminary_docs
        self.parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
        self.child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        # 文档存储区，用于存储父文档
        self.docstore = InMemoryStore()

    def chunk(self) -> (List[Document], InMemoryStore): # 返回子文档和文档存储
        logger.info("开始第二步：父子文档切分策略...")
        
        # 假设我们已经有了合并好的逻辑章节文本列表 (parent_texts)
        # 这里简化一下流程，直接对 preliminary_docs 进行处理
        
        # 1. 创建父文档 (较大的块)
        parent_docs = self.parent_splitter.split_documents(self.preliminary_docs)

        # 2. 为父文档创建并存储子文档
        child_docs = []
        parent_ids = []
        for i, p_doc in enumerate(parent_docs):
            _id = str(uuid.uuid4())
            parent_ids.append(_id)
            sub_docs = self.child_splitter.split_documents([p_doc])
            for _doc in sub_docs:
                _doc.metadata["parent_id"] = _id
            child_docs.extend(sub_docs)

        # 3. 将父文档存入 docstore
        self.docstore.mset(list(zip(parent_ids, parent_docs)))
        
        logger.info(f"切分完成。生成 {len(child_docs)} 个子文档和 {len(parent_docs)} 个父文档。")
        return child_docs, self.docstore

    def _merge_and_split_if_needed(self, content: str, metadata: dict) -> List[Document]:
        """
        一个辅助函数，用于处理可能过长的合并后内容。
        如果内容不长，返回单个Document；如果过长，则分割成多个。
        """
        cleaned_content = content.strip()
        
        # 检查文本长度，如果适合，直接返回
        if len(cleaned_content) <= self.text_splitter._chunk_size:
            return [Document(page_content=cleaned_content, metadata=metadata)]
        else:
            # 如果内容过长，使用文本分割器进行二次切分
            logger.info(f"内容过长 (长度 {len(cleaned_content)})，正在进行二次分割...")
            # create_documents 会自动继承元数据
            return self.text_splitter.create_documents([cleaned_content], metadatas=[metadata])

    # def chunk(self) -> List[Document]:
    #     """
    #     执行完整的、基于上下文的切分策略。
    #     """
    #     logger.info("开始第二步：核心切分策略 (基于上下文)...")
    #     final_chunks = []
        
    #     i = 0
    #     while i < len(self.preliminary_docs):
    #         doc = self.preliminary_docs[i]
    #         chunk_type = doc.metadata.get("chunk_type")

    #         # --- 策略1: 组合标题及其后续段落 ---
    #         if chunk_type == "title":
    #             current_title_doc = doc
    #             content_docs = []
    #             # 向后查找，合并所有属于这个标题的连续段落
    #             j = i + 1
    #             while j < len(self.preliminary_docs):
    #                 next_doc = self.preliminary_docs[j]
    #                 # 遇到下一个标题或非段落内容时停止
    #                 if next_doc.metadata.get("chunk_type") not in ["paragraph", "figure_title"]:
    #                     break
    #                 content_docs.append(next_doc)
    #                 j += 1
                
    #             # 合并标题和段落内容
    #             title_text = current_title_doc.page_content
    #             paragraphs_text = "\n".join([d.page_content for d in content_docs])
    #             full_content = f"{title_text}\n\n{paragraphs_text}"
                
    #             # 创建元数据，并根据标题内容确定最终的 chunk_type
    #             metadata = current_title_doc.metadata.copy()
    #             if "核心观点" in title_text:
    #                 metadata['chunk_type'] = 'summary'
    #             elif "风险提示" in title_text:
    #                 metadata['chunk_type'] = 'risk_warning'
    #             else:
    #                 metadata['chunk_type'] = 'section'
                
    #             final_chunks.extend(self._merge_and_split_if_needed(full_content, metadata))
                
    #             # 跳过已经处理过的段落
    #             i = j
    #             continue

    #         # --- 策略2: 组合图表标题、图表本身和来源 ---
    #         # (这个逻辑在新版 Parser 中变得更简单，因为来源等信息可能已被合并或标记)
    #         elif chunk_type == "figure":
    #             figure_doc = doc
    #             figure_title = "未知图表"
    #             source_text = "未知来源"
                
    #             # 尝试在附近寻找图表标题和来源
    #             # 向前看一个块，找标题
    #             if i > 0 and self.preliminary_docs[i-1].metadata.get("chunk_type") == "figure_title":
    #                 figure_title = self.preliminary_docs[i-1].page_content
    #             # 向后看一个块，找来源
    #             if i + 1 < len(self.preliminary_docs) and self.preliminary_docs[i+1].metadata.get("chunk_type") == "source":
    #                 source_text = self.preliminary_docs[i+1].page_content
                
    #             # 生成描述性内容
    #             description = (f"图表标题: {figure_title}\n"
    #                            f"数据来源: {source_text}\n"
    #                            f"注意: 这是一个图表，以下是OCR识别的初步内容: '{figure_doc.page_content[:150]}...'")

    #             metadata = figure_doc.metadata.copy()
    #             metadata['chunk_type'] = 'figure' # 确认类型
    #             metadata['figure_title'] = figure_title
    #             metadata['source'] = source_text
                
    #             final_chunks.append(Document(page_content=description, metadata=metadata))
                
    #             i += 1
    #             continue

    #         # --- 默认策略: 对于未被组合的独立块 ---
    #         else:
    #             # 比如分析师信息等，如果它们很重要，也可以保留
    #             # 这里我们简单地将它们作为独立的 chunk，但可以加一些过滤条件
    #             if len(doc.page_content) > 30: # 过滤掉太短的无用文本
    #                 final_chunks.append(doc)
    #             i += 1

    #     logger.info(f"第二步完成。总计生成了 {len(final_chunks)} 个高质量的文档块。")
    #     return final_chunks


# --- 示例用法 ---
if __name__ == '__main__':
    try:
        with open("./utils/20250806.json", 'r', encoding='utf-8') as f:
            report_json_data = json.load(f)
        
        # 运行第一步
        parser = RobustReportParser(report_json_data)
        preliminary_docs = parser.parse()

        # 运行第二步
        chunker = AdvancedChunkingStrategy(preliminary_docs)
        final_chunks = chunker.chunk()
        
        # ... (后续的打印和检查代码保持不变，可以用来验证新策略的效果) ...
        print("\n--- 切分结果概览 ---")
        print(f"总计生成了 {len(final_chunks)} 个最终文档块。")

        print("\n--- 示例：核心观点合并后的 Chunk ---")
        for chunk in final_chunks:
            if chunk.metadata.get("chunk_type") == "summary":
                print(f"类型: {chunk.metadata['chunk_type']}")
                print(f"层级: {chunk.metadata['hierarchy']}")
                print(f"内容长度: {len(chunk.page_content)}")
                print(f"内容预览: '{chunk.page_content[:200].replace(chr(10), ' ')}...'")
                print("-" * 20)

        print("\n--- 示例：处理后的图表 Chunk ---")
        found = False
        for chunk in final_chunks:
            if chunk.metadata.get("chunk_type") == "figure":
                print(f"类型: {chunk.metadata['chunk_type']}")
                print(f"图表标题: {chunk.metadata['figure_title']}")
                print(f"内容 (生成描述): '{chunk.page_content}'")
                print(f"元数据: {chunk.metadata}")
                print("-" * 20)
                found = True
                break
        if not found:
            print("未找到图表块。")

    except FileNotFoundError:
        logger.error("错误: 20250728.json 文件未找到。")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)