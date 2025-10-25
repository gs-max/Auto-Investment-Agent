#!/usr/bin/env python3
"""
测试State在节点间的传递
"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("🧪 测试State传递")
print("=" * 70)

# 模拟state
test_state = {
    "messages": [],
    "current_prices": {"BTC": 100000, "ETH": 3000},
    "account_value": 1000,
    "available_balance": 900,
    "positions": [],
    "market_analysis": {},
    "portfolio_trades": [],
    "portfolio_analysis": "",
    "execution_results": []
}

print("\n1️⃣ 初始 State:")
print(f"   Keys: {list(test_state.keys())}")
print(f"   portfolio_trades: {test_state.get('portfolio_trades')}")

# 模拟LLM节点设置trades
print("\n2️⃣ 模拟LLM节点设置trades...")
test_trades = [
    {"decision": "buy", "coin": "ETH", "size": 0.05, "reasoning": "test1"},
    {"decision": "buy", "coin": "SOL", "size": 0.5, "reasoning": "test2"}
]
test_state["portfolio_trades"] = test_trades
print(f"   已设置 portfolio_trades: {len(test_state['portfolio_trades'])} 个")

# 模拟条件判断
print("\n3️⃣ 模拟条件判断...")
trades = test_state.get("portfolio_trades", [])
print(f"   读取到 {len(trades)} 个交易")
if len(trades) > 0:
    print(f"   ✅ 条件满足，应该执行")
else:
    print(f"   ❌ 条件不满足，不应该执行")

# 模拟执行节点
print("\n4️⃣ 模拟执行节点...")
trades_in_execute = test_state.get("portfolio_trades", [])
print(f"   执行节点读取到 {len(trades_in_execute)} 个交易")
if trades_in_execute:
    print(f"   ✅ 成功读取trades")
    for i, trade in enumerate(trades_in_execute, 1):
        print(f"      {i}. {trade['decision'].upper()} {trade['coin']}")
else:
    print(f"   ❌ 未读取到trades")

print("\n" + "=" * 70)
print("💡 如果这个测试通过，说明State传递逻辑是正确的")
print("   问题可能在LangGraph的状态管理或节点调用上")
print("=" * 70)
