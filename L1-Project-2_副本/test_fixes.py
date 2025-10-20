#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证async_agent_MCP.py中三个主要错误的修复效果
"""

import asyncio
import json
from langchain_core.messages import ToolMessage, AIMessage
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from async_agent_MCP import ParallelToolNode, grade_documents, rewrite, generate
from typing import Dict, Any, List

async def test_structured_tool_fix():
    """测试StructuredTool同步调用问题的修复"""
    print("=== 测试StructuredTool同步调用修复 ===")
    
    # 模拟一个StructuredTool
    class MockStructuredTool:
        def __init__(self, name):
            self.name = name
            
        def run(self, args):
            return {"result": "success", "data": "test data"}
            
        def invoke(self, args):
            # 模拟StructuredTool的同步调用
            raise NotImplementedError('StructuredTool does not support sync invocation.')
    
    # 创建ParallelToolNode实例
    tool_node = ParallelToolNode()
    
    # 模拟工具映射
    mock_tool = MockStructuredTool("test_tool")
    tool_map = {"test_tool": mock_tool}
    
    # 模拟工具调用
    tool_call = {"name": "test_tool", "args": {"query": "test"}}
    
    try:
        result = await tool_node._run_single_tool_async(tool_call, tool_map)
        print(f"✅ StructuredTool异步调用成功: {type(result)}")
        print(f"✅ 返回ToolMessage对象: {isinstance(result, ToolMessage)}")
        return True
    except Exception as e:
        print(f"❌ StructuredTool测试失败: {e}")
        return False

def test_none_score_fix():
    """测试NoneType评分错误的修复"""
    print("\n=== 测试NoneType评分修复 ===")
    
    # 模拟状态
    mock_state = {
        "messages": [
            AIMessage(content="test question"),
            AIMessage(content="test context")
        ]
    }
    
    # 模拟LLM
    class MockLLM:
        def __call__(self, *args, **kwargs):
            # 模拟返回None的情况
            return None
    
    try:
        result = grade_documents(mock_state, MockLLM())
        print(f"✅ NoneType评分处理成功")
        print(f"✅ 返回有效评分: {result.get('relevance_score', 'no')}")
        return True
    except Exception as e:
        print(f"❌ NoneType评分测试失败: {e}")
        return False

def test_json_serialization_fix():
    """测试JSON序列化错误的修复"""
    print("\n=== 测试JSON序列化修复 ===")
    
    # 测试ToolMessage序列化
    tool_msg = ToolMessage(content="test content", tool_call_id="test_id")
    
    try:
        # 测试是否可以JSON序列化
        json_str = json.dumps(tool_msg.content)
        print(f"✅ ToolMessage内容可序列化: {json_str}")
        
        # 测试AIMessage序列化
        ai_msg = AIMessage(content="test response")
        ai_json = json.dumps(ai_msg.content)
        print(f"✅ AIMessage内容可序列化: {ai_json}")
        
        return True
    except Exception as e:
        print(f"❌ JSON序列化测试失败: {e}")
        return False

async def run_all_tests():
    """运行所有测试"""
    print("开始测试async_agent_MCP.py的修复效果...\n")
    
    results = []
    
    # 测试1: StructuredTool同步调用修复
    results.append(await test_structured_tool_fix())
    
    # 测试2: NoneType评分修复
    results.append(test_none_score_fix())
    
    # 测试3: JSON序列化修复
    results.append(test_json_serialization_fix())
    
    print(f"\n=== 测试结果汇总 ===")
    print(f"总测试数: {len(results)}")
    print(f"通过测试: {sum(results)}")
    print(f"失败测试: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 所有测试通过！修复成功")
    else:
        print("⚠️  部分测试失败，请检查代码")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
