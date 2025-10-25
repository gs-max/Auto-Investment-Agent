#!/usr/bin/env python3
"""
测试强制交易模式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from main_advanced import main
import logging

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 测试强制交易模式")
    print("=" * 70)
    print()
    print("预期行为：")
    print("1. LLM 必须做出 buy/sell/close 决策")
    print("2. 如果尝试 hold，会被自动转换为 buy")
    print("3. 如果风险检查失败，会自动降级参数后执行")
    print("4. 每次都会执行交易")
    print()
    print("=" * 70)
    
    # 运行一次
    sys.argv = ["test_forced_trading.py", "--mode", "once"]
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
