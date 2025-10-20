import json
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
import logging

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReportParser:
    """
    一个用于解析特定结构化 JSON 研报的解析器。
    它负责将扁平的 layouts 列表重组成一个有逻辑层级的结构。
    """
    def __init__(self, json_data: Dict[str, Any]):
        if json_data.get("Status") != "Success" or not json_data.get("Data", {}).get("layouts"):
            raise ValueError("JSON data is not valid or does not contain layouts.")
        self.layouts = json_data["Data"]["layouts"]
        self.doc_id = json_data.get("Id", "unknown_doc")
        self.global_metadata = {}

    def _extract_global_metadata(self):
        """提取文档级别的全局元数据。"""
        # (此方法无需修改)
        for layout in self.layouts:
            sub_type = layout.get("subType")
            if sub_type == "doc_title":
                self.global_metadata['doc_title'] = layout.get("text", "").strip()
            elif sub_type == "doc_subtitle":
                self.global_metadata['doc_subtitle'] = layout.get("text", "").strip()
        if not self.global_metadata.get('doc_title'):
             for layout in self.layouts:
                if layout.get("type") == "title":
                    self.global_metadata['doc_title'] = layout.get("text", "").strip()
                    break
        logger.info(f"提取到全局元数据: {self.global_metadata}")

    def _build_logical_structure(self) -> List[Document]:
        """
        构建逻辑结构，将内容归属到标题下，并明确分类。
        """
        structured_elements = []
        current_titles = [] 

        for layout in self.layouts:
            layout_type = layout.get("type")
            sub_type = layout.get("subType")
            text = layout.get("text", "").strip()
            page_num = layout.get("pageNum")

            # --- 1. 过滤噪音和不必要的信息 ---
            # 过滤掉空块、页眉/页脚、以及明确的目录信息
            if not text or layout_type in ["header", "footer"] or sub_type in ["cate", "cate_title"] or layout_type in ["contents", "contents_title"]:
                continue
            
            # --- 2. 识别并构建章节层级 (Hierarchy) ---
            # 只有 para_title, doc_title, doc_subtitle 才被认为是会影响层级的标题
            if sub_type in ["para_title", "doc_title", "doc_subtitle"]:
                level = layout.get("level", 0)
                current_titles = current_titles[:level]
                current_titles.append(text)
            
            # --- 3. 创建 Document 对象并赋予明确的元数据 ---
            # 根据 type 和 subType 决定 chunk_type
            chunk_type = "unknown"
            if sub_type == "picture" or layout_type == "figure":
                chunk_type = "picture"
            elif sub_type == "pic_title" or layout_type == "figure_name":
                # 我们现在将图表标题视为普通文本，因为它会被合并到章节中
                # 并且它的标题信息会从 picture 块的 OCR 内容中提取
                chunk_type = "text"
            elif sub_type in ["para", "none"] or layout_type == "text":
                chunk_type = "text"
            elif sub_type in ["para_title", "doc_title", "doc_subtitle"]:
                chunk_type = "title"

            doc = Document(
                page_content=text,
                metadata={
                    **self.global_metadata,
                    "doc_id": self.doc_id,
                    "chunk_type": chunk_type,
                    "subType": sub_type, # 保留原始 subType 供调试
                    "pageNum": page_num,
                    "uniqueId": layout.get("uniqueId"),
                    "hierarchy": " | ".join(current_titles) if current_titles else self.global_metadata.get('doc_title', '')
                }
            )
            structured_elements.append(doc)
        
        logger.info(f"构建了 {len(structured_elements)} 个初步的结构化元素。")
        return structured_elements

    def parse(self) -> List[Document]:
        """执行完整的解析流程。"""
        logger.info("开始第一步：预处理与结构重组...")
        self._extract_global_metadata()
        logical_structure = self._build_logical_structure()
        logger.info("第一步完成。")
        return logical_structure


# --- 示例用法 ---
if __name__ == '__main__':
    # 1. 加载你的 JSON 文件
    try:
        with open("./utils/20250728.json", 'r', encoding='utf-8') as f:
            report_json_data = json.load(f)
    except FileNotFoundError:
        logger.error("错误: 20250728.json 文件未找到。请确保它在正确的路径下。")
        exit()
    except json.JSONDecodeError:
        logger.error("错误: 20250728.json 文件格式不正确。")
        exit()

    # 2. 实例化解析器并执行解析
    parser = ReportParser(report_json_data)
    preliminary_docs = parser.parse()

    # 3. 打印一些结果来检查
    print("\n--- 解析结果概览 ---")
    print(f"总计生成了 {len(preliminary_docs)} 个初步文档块。")
    print("\n--- 示例：核心观点部分的块 ---")
    for doc in preliminary_docs:
        if "核心观点" in doc.metadata.get("hierarchy", ""):
            print(f"类型: {doc.metadata['chunk_type']}, "
                  f"层级: {doc.metadata['hierarchy']}, "
                  f"内容: '{doc.page_content[:50]}...'")
            
    print("\n--- 示例：第一个图表的块 ---")
    found_figure = False
    for doc in preliminary_docs:
        if doc.metadata.get("chunk_type") == "picture":
            print(f"类型: {doc.metadata['chunk_type']}, "
                  f"层级: {doc.metadata['hierarchy']}, "
                  f"页码: {doc.metadata['pageNum']}, "
                  f"内容 (OCR 结果): '{doc.page_content[:50]}...'")
            found_figure = True
            break
    if not found_figure:
        print("未找到图表块。")