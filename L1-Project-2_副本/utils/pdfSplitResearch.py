from langchain_community.document_loaders import PDFMinerLoader
from langchain_community.document_loaders.parsers import RapidOCRBlobParser

loader = PDFMinerLoader(
    "../input/20250728-甬兴证券-AIDC行业专题（一）：智算中心加速扩张，政策+需求双轮驱动供电系统升级.pdf",
    mode="page",
    images_inner_format="markdown-img",
    images_parser=RapidOCRBlobParser(),
)
docs = loader.load()

print(docs[22].page_content)