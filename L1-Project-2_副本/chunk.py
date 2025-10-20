import json
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
from reportparser import ReportParser
from typing import Optional
import re
# (假设你已经运行了第一步的 ReportParser，并得到了 preliminary_docs)
# from step1_parser import ReportParser # 假设第一步代码在 step1_parser.py

logger = logging.getLogger(__name__)

# 导入 re 模块用于正则表达式
import re

class ChunkingStrategy:
    """
    应用核心切分策略，将初步解析的文档列表转换为最终的、
    适合向量化的高质量 Chunks。
    """
    def __init__(self, preliminary_docs: List[Document]):
        self.preliminary_docs = preliminary_docs
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )

    # _group_by_hierarchy 和 _merge_groups_to_chunks 方法保持不变
    def _group_by_hierarchy(self) -> Dict[str, List[Document]]:
        # ... (无变化)
        groups = {}
        for doc in self.preliminary_docs:
            chunk_type = doc.metadata.get("chunk_type", "")
            if chunk_type in ["cate", "contents_title"]: continue
            hierarchy = doc.metadata.get("hierarchy")
            if hierarchy:
                if hierarchy not in groups: groups[hierarchy] = []
                groups[hierarchy].append(doc)
        logger.info(f"按层级分成了 {len(groups)} 个逻辑组。")
        return groups

    def _merge_groups_to_chunks(self, groups: Dict[str, List[Document]]) -> List[Document]:
        # ... (无变化)
        merged_chunks = []
        for hierarchy, docs in groups.items():
            docs.sort(key=lambda d: d.metadata.get("index", float('inf')))
            full_content = "\n\n".join([doc.page_content for doc in docs])
            base_metadata = docs[0].metadata.copy()
            base_metadata["chunk_type"] = "logical_section"
            base_metadata.pop("uniqueId", None)
            if "核心观点" in hierarchy:
                base_metadata['chunk_type'] = 'summary'
            elif "风险提示" in hierarchy:
                 base_metadata['chunk_type'] = 'risk'
            else:
                base_metadata['chunk_type'] = 'section'
            if len(full_content) > self.text_splitter._chunk_size:
                split_docs = self.text_splitter.create_documents([full_content], metadatas=[base_metadata])
                merged_chunks.extend(split_docs)
            else:
                merged_chunks.append(Document(page_content=full_content, metadata=base_metadata))
        return merged_chunks

    # --- 全新、更健壮的 _handle_special_objects 方法 ---
    def _handle_special_objects(self) -> List[Document]:
        """
        单独处理如图表之类的特殊对象。
        新策略：直接从图片块的 OCR 内容中提取标题。
        """
        special_chunks = []
        
        for doc in self.preliminary_docs:
            if doc.metadata.get("chunk_type") == "picture":
                ocr_text = doc.page_content.strip()
                
                # 尝试从 OCR 文本中提取标题
                # 研报图片的 OCR 文本通常以标题开头，后面跟着图例或杂乱的轴标签
                # 我们可以通过换行符或一些关键词来分割
                # 这是一个简化的正则表达式，它会匹配开头的非数字、非字母字符直到第一个换行符或长串数字/乱码
                title_match = re.match(r"^([^(\n0-9)]{5,})", ocr_text)
                figure_title = title_match.group(1).strip() if title_match else "未知图表"
                
                print(f"[调试] 正在处理图片 {doc.metadata.get('uniqueId')}, 提取到的标题是: '{figure_title}'")
                
                # 使用多模态模型生成描述的理想位置
                # description = call_multimodal_model(doc.metadata['imageUrl'])
                
                # 当前的简化策略：使用提取出的标题和占位符
                description = f"图表标题: {figure_title}\n" \
                              f"注意：这是图表的文本描述占位符。原始OCR内容为: '{ocr_text[:100]}...'. " \
                              f"请查看原始文档第 {doc.metadata.get('pageNum', 'N/A')} 页获取详细信息。"

                metadata = doc.metadata.copy()
                metadata['chunk_type'] = 'figure'
                metadata['figure_title'] = figure_title
                metadata['original_ocr_text'] = ocr_text # 保留原始 OCR 文本
                
                special_chunks.append(Document(page_content=description, metadata=metadata))
        
        return special_chunks


    def chunk(self) -> List[Document]:
        """
        执行完整的切分策略。
        """
        logger.info("开始第二步：核心切分策略...")
        
        groups = self._group_by_hierarchy()
        final_text_chunks = self._merge_groups_to_chunks(groups)
        final_special_chunks = self._handle_special_objects()
        
        final_chunks = final_text_chunks + final_special_chunks
        
        logger.info(f"第二步完成。总计生成了 {len(final_chunks)} 个高质量的文档块。")
        return final_chunks

# --- 示例用法 ---
if __name__ == '__main__':
    # 假设你已经有了第一步的 `preliminary_docs`
    # 这里我们重新运行第一步来获取它
    # (实际项目中，你可以将这两个步骤连接起来)
    try:
        with open("./utils/20250728.json", 'r', encoding='utf-8') as f:
            report_json_data = json.load(f)
        
        # 运行第一步
        # 假设 ReportParser 在同一个文件中或已导入
        parser = ReportParser(report_json_data)
        preliminary_docs = parser.parse()

        # 运行第二步
        chunker = ChunkingStrategy(preliminary_docs)
        final_chunks = chunker.chunk()

        print("\n\n--- 深度调试：检查图片块的邻居 ---")
        first_pic_index = None
        # 找到第一个 picture 块的索引
        for i, doc in enumerate(preliminary_docs):
            if doc.metadata.get("chunk_type") == "picture":
                first_pic_index = i
                break

        if first_pic_index is not None:
            print(f"第一个 'picture' 块位于索引 {first_pic_index}。")
            print("打印它和它前后各 3 个邻居的信息：")
            
            # 定义打印范围，并确保不越界
            start = max(0, first_pic_index - 3)
            end = min(len(preliminary_docs), first_pic_index + 4)
            
            for i in range(start, end):
                doc = preliminary_docs[i]
                marker = ">> HERE >>" if i == first_pic_index else ""
                print(f"  Index {i}: Type='{doc.metadata.get('chunk_type')}', "
                    f"SubType='{doc.metadata.get('subType', 'N/A')}', "
                    f"Content='{doc.page_content.strip()[:50]}...' {marker}")
        else:
            print("在 preliminary_docs 中未找到任何 'picture' 类型的块。")

        # 打印一些结果来检查
        print("\n--- 切分结果概览 ---")
        print(f"总计生成了 {len(final_chunks)} 个最终文档块。")

        print("\n--- 示例：核心观点合并后的 Chunk ---")
        for chunk in final_chunks:
            if "核心观点" in chunk.metadata.get("hierarchy", ""):
                print(f"类型: {chunk.metadata['chunk_type']}")
                print(f"层级: {chunk.metadata['hierarchy']}")
                print(f"内容长度: {len(chunk.page_content)}")
                print(f"内容预览: '{chunk.page_content[:200].replace(chr(10), ' ')}...'")
                print("-" * 20)

        print("\n--- 示例：处理后的图表 Chunk ---")
        for chunk in final_chunks:
            if chunk.metadata.get("chunk_type") == "figure":
                print(f"类型: {chunk.metadata['chunk_type']}")
                print(f"层级: {chunk.metadata['hierarchy']}")
                print(f"图表标题: {chunk.metadata['figure_title']}")
                print(f"内容 (生成描述): '{chunk.page_content}'")
                print("-" * 20)
                break # 只打印一个示例

    except FileNotFoundError:
        logger.error("错误: 20250728.json 文件未找到。")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)