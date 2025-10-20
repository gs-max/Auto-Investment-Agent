import json
import re
from typing import List, Dict, Any
from langchain_core.documents import Document
import logging

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



class RobustReportParser:
    """
    一个更健壮的研报解析器，能够应对上游解析结果不稳定的问题 (如 subType='none')。
    它使用一套启发式规则来推断块的类型和结构。
    """
    def __init__(self, json_data: Dict[str, Any]):
        if json_data.get("Status") != "Success" or not json_data.get("Data", {}).get("layouts"):
            raise ValueError("JSON data is not valid or does not contain 'layouts'.")
        self.layouts = json_data["Data"]["layouts"]
        self.doc_id = json_data.get("Id", "unknown_doc")
        self.global_metadata = {}

    def _extract_global_metadata(self):
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

    def _infer_chunk_type(self, layout: Dict[str, Any]) -> str:
        """
        [核心] 使用启发式规则推断一个 layout 块的真实类型。
        """
        layout_type = layout.get("type")
        sub_type = layout.get("subType")
        text = layout.get("text", "").strip()

        # 1. 强规则优先
        if sub_type == "picture" or layout_type == "figure": return "figure"
        if sub_type == "table" or layout_type == "table": return "table"
        if sub_type == "doc_title" or sub_type == "doc_subtitle": return "title"
        
        # 2. 启发式规则推断
        # 推断标题
        if sub_type == "para_title" or layout_type == "title":
             return "title"
        # 当 subType 为 none 时的标题推断
        if sub_type == "none" or sub_type == "para":
            # 规则 a: 以数字/编号开头，长度短，不以标点结尾
            if re.match(r'^\s*([❑\d\.]+|第[一二三四五六七八九十]章?)\s+', text) and len(text) < 30 and text[-1] not in "。；）":
                return "title"
            # 规则 b: 文本内容是“核心观点”或“风险提示”
            if text in ["核心观点", "风险提示"]:
                return "title"

        # 推断图表标题
        if re.match(r'^\s*(图|表)\s*\d+[:：]', text):
            return "figure_title"
        
        # 推断来源
        if text.startswith("资料来源："):
            return "source"

        # 3. 默认规则
        if layout_type == "text" or sub_type == "para":
            return "paragraph"

        return "other" # 其他无法识别的类型

    def _build_logical_structure(self) -> List[Document]:
        """
        构建逻辑结构，使用推断出的块类型来增强鲁棒性。
        """
        structured_elements = []
        current_titles = [] 

        for layout in self.layouts:
            text = layout.get("text", "").strip()
            page_num = layout.get("pageNum")
            
            # 过滤空块和明确的噪音
            if not text or layout.get("type") in ["header", "footer", "contents"]:
                continue
            if "法律声明" in text or "投资评级说明" in text or "免责条款" in text:
                continue

            # --- 核心改动：调用推断函数 ---
            inferred_type = self._infer_chunk_type(layout)

            # 根据推断出的类型进行处理
            if inferred_type == "title":
                level = layout.get("level", 0)
                # 使用 level 来维护层级，这比依赖标题文本更可靠
                current_titles = current_titles[:level] 
                current_titles.append(text)
            
            # 忽略来源块，因为它们将在第二步被合并到图表块中
            if inferred_type == "source":
                continue

            # 创建 Document 对象
            metadata = {
                **self.global_metadata,
                "doc_id": self.doc_id,
                "chunk_type": inferred_type, # 使用推断出的类型
                "page_num": page_num,
                "level": layout.get("level"),
                "hierarchy": " | ".join(current_titles) if current_titles else self.global_metadata.get('doc_title', ''),
                "unique_id": layout.get("uniqueId")
            }
            doc = Document(page_content=text, metadata=metadata)
            structured_elements.append(doc)
        
        logger.info(f"构建了 {len(structured_elements)} 个初步的结构化元素。")
        return structured_elements

    def parse(self) -> List[Document]:
        """执行完整的解析流程。"""
        logger.info("开始第一步：预处理与结构重组 (鲁棒模式)...")
        self._extract_global_metadata()
        logical_structure = self._build_logical_structure()
        logger.info("第一步完成。")
        return logical_structure



# --- 示例用法 (用于测试) ---
if __name__ == '__main__':
    try:
        with open("./utils/20250807.json", 'r', encoding='utf-8') as f:
            report_json_data = json.load(f)

        parser = RobustReportParser(report_json_data)
        preliminary_docs = parser.parse()

        print("\n--- 全局元数据 ---")
        print(parser.global_metadata)

        print("\n--- 解析结果概览 ---")
        print(f"总计生成了 {len(preliminary_docs)} 个初步文档块。")
        
        print("\n--- 示例：核心观点部分的块 ---")
        for doc in preliminary_docs:
            if doc.metadata.get("hierarchy") and "核心观点" in doc.metadata["hierarchy"]:
                print(f"类型: {doc.metadata['chunk_type']}, "
                      f"层级: {doc.metadata['hierarchy']}, "
                      f"内容: '{doc.page_content[:50]}...'")
            
        print("\n--- 示例：一个图表相关的块 (类型为 'figure') ---")
        found_figure = False
        for doc in preliminary_docs:
            if doc.metadata.get("chunk_type") == "figure":
                print(f"类型: {doc.metadata['chunk_type']}, "
                      f"层级: {doc.metadata['hierarchy']}, "
                      f"页码: {doc.metadata['page_num']}, "
                      f"内容 (OCR): '{doc.page_content[:50]}...'")
                found_figure = True
                break
        if not found_figure:
            print("未找到图表块。")

    except FileNotFoundError:
        logger.error("错误: 20250728.json 文件未找到。")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)