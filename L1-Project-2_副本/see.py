import pprint
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
import os
import sys

os.environ["DASHSCOPE_API_KEY"] = "sk-cf312af820bb4841a707fc4284f147a4"

# --- 配置 ---
DB_DIRECTORY = "./chromaDB"
COLLECTION_NAME = "financial_reports_collections" # 确保这个名字和你入库时用的完全一样

# 1. 初始化你自己的、与入库时相同的嵌入模型
llm_embeddings = DashScopeEmbeddings(
    model="text-embedding-v4", 
    dashscope_api_key="sk-cf312af820bb4841a707fc4284f147a4"
)

import chromadb


# --- 配置 ---
DB_DIRECTORY = "./chromaDB"
COLLECTION_NAME = "financial_reports_collection" # 确保这是正确的名称

# --- 模型初始化 ---
# (这里省略了，假设与之前相同)
# ...

# --- 从命令行获取参数 ---
try:
    offset = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    # 新增参数：如果第三个参数是 "full"，则显示完整内容
    show_full_content = sys.argv[3].lower() == 'full' if len(sys.argv) > 3 else False
except (ValueError, IndexError):
    print("用法: python see.py [offset] [limit] [full]")
    print("示例 1 (默认): python see.py 0 5")
    print("示例 2 (完整内容): python see.py 0 5 full")
    exit()

# --- 连接数据库 ---
try:
    # 删掉 ellipsis (...)，换成完整的初始化代码
    vectorstore = Chroma(
        persist_directory=DB_DIRECTORY,
        collection_name=COLLECTION_NAME,
        embedding_function=llm_embeddings
    )
    
    # 我们可以通过 vectorstore._collection 访问底层的原生 collection 对象
    collection = vectorstore._collection
    
    print(f"成功加载集合 '{COLLECTION_NAME}' from '{DB_DIRECTORY}' via LangChain wrapper.")

except Exception as e:
    print(f"加载集合时发生错误: {e}", exc_info=True) # 加上 exc_info=True 可以看到更详细的 Traceback
    print(f"请确认集合 '{COLLECTION_NAME}' 是否存在于 '{DB_DIRECTORY}' 目录中。")
    exit()

# --- 获取并打印数据 ---
collection_count = collection.count()
print(f"\n--- 集合 '{COLLECTION_NAME}' 基本信息 ---")
print(f"文档总数: {collection_count}")

if collection_count == 0:
    print("集合为空。")
elif offset >= collection_count:
    print(f"错误: offset ({offset}) 超出或等于文档总数 ({collection_count})。")
else:
    print(f"\n--- 查看从第 {offset} 条开始的 {limit} 条数据 ---")
    data = collection.get(
        limit=limit,
        offset=offset,
        include=["metadatas", "documents"]
    )
    
    # 格式化并打印数据
    for i in range(len(data['ids'])):
        print(f"\n--- Document (全局索引 {offset + i}) ---")
        print(f"  ID: {data['ids'][i]}")
        print("  Metadata:")
        pprint.pprint(data['metadatas'][i], indent=4)
        print("  Document Content:")
        
        content = data['documents'][i]
        
        # 根据命令行参数决定是显示完整内容还是预览
        if show_full_content:
            print("    --- START OF CONTENT ---")
            print(content)
            print("    --- END OF CONTENT ---")
        else:
            # 替换换行符并截断，以获得整洁的单行预览
            preview = content.replace('\n', ' ').replace('\r', '')
            print(f"    '{preview[:300]}...'")

    # 6. (可选) 进行一次查询测试，使用 LangChain 的方法
    # print("\n--- 进行一次查询测试 (使用 LangChain 方法) ---")
    # query_text = "核心观点"
    # print(f"查询: '{query_text}'")
    
    # # .similarity_search 会自动使用正确的嵌入模型处理查询
    # results = vectorstore.similarity_search(query_text, k=5)

    # print("\n查询结果:")
    # # LangChain 返回的是 Document 对象列表
    # for doc in results:
    #     print("\n--- Retrieved Document ---")
    #     pprint.pprint(doc)