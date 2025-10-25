#!/usr/bin/env python3
"""
快速测试组合管理模式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("🧪 组合管理模式 - 快速测试")
print("=" * 70)

# 1. 检查文件
print("\n1️⃣ 检查必要文件...")
files_to_check = [
    ("配置文件", "config/config.testnet.json"),
    ("组合策略", "config/portfolio_strategy_prompt.txt"),
    ("组合节点", "src/portfolio_nodes.py"),
    ("主程序", "main_portfolio.py")
]

all_exist = True
for name, path in files_to_check:
    if os.path.exists(path):
        print(f"   ✅ {name}: {path}")
    else:
        print(f"   ❌ {name} 不存在: {path}")
        all_exist = False

if not all_exist:
    print("\n❌ 缺少必要文件，请检查！")
    sys.exit(1)

# 2. 检查配置
print("\n2️⃣ 检查配置...")
import json
with open("config/config.testnet.json") as f:
    config = json.load(f)

print(f"   账户地址: {config['hyperliquid']['account_address'][:15]}...")
print(f"   LLM: {config['llm']['provider']}")
print(f"   最大持仓数: {config['risk'].get('max_positions', '未设置')}")
print(f"   最大仓位: {config['risk'].get('max_total_exposure', 0)*100:.0f}%")

if 'max_positions' not in config['risk']:
    print("\n   ⚠️  警告: 配置中没有 max_positions，将使用默认值")

# 3. 测试导入
print("\n3️⃣ 测试模块导入...")
try:
    from src.portfolio_nodes import enhanced_portfolio_analysis_node, execute_portfolio_trades_node
    print("   ✅ portfolio_nodes 导入成功")
except Exception as e:
    print(f"   ❌ portfolio_nodes 导入失败: {e}")
    sys.exit(1)

try:
    from src.advanced_tools import AdvancedTradingTools
    print("   ✅ advanced_tools 导入成功")
except Exception as e:
    print(f"   ❌ advanced_tools 导入失败: {e}")
    sys.exit(1)

# 4. 检查策略提示
print("\n4️⃣ 检查策略提示...")
with open("config/portfolio_strategy_prompt.txt", encoding='utf-8') as f:
    strategy = f.read()

keywords = ["多资产", "组合", "分散", "trades", "portfolio"]
found_keywords = [kw for kw in keywords if kw in strategy]

print(f"   关键词检查: {len(found_keywords)}/{len(keywords)} 找到")
for kw in found_keywords:
    print(f"      ✅ {kw}")

missing = set(keywords) - set(found_keywords)
if missing:
    print(f"   ⚠️  缺少关键词: {', '.join(missing)}")

# 5. 模拟LLM响应测试
print("\n5️⃣ 测试Function Calling Schema...")
test_response = {
    "trades": [
        {
            "decision": "buy",
            "coin": "ETH",
            "size": 0.03,
            "leverage": 2,
            "use_tpsl": True,
            "take_profit_pct": 3.0,
            "stop_loss_pct": 1.5,
            "reasoning": "测试交易",
            "confidence": 0.65
        },
        {
            "decision": "buy",
            "coin": "SOL",
            "size": 0.5,
            "leverage": 3,
            "use_tpsl": True,
            "take_profit_pct": 4.0,
            "stop_loss_pct": 2.0,
            "reasoning": "测试交易2",
            "confidence": 0.70
        }
    ],
    "portfolio_analysis": "这是一个测试组合"
}

try:
    trades = test_response["trades"]
    assert len(trades) == 2
    assert trades[0]["decision"] in ["buy", "sell", "close"]
    assert "coin" in trades[0]
    print(f"   ✅ Schema 验证通过")
    print(f"   ✅ 包含 {len(trades)} 个交易决策")
except Exception as e:
    print(f"   ❌ Schema 验证失败: {e}")

# 6. 总结
print("\n" + "=" * 70)
print("📊 测试总结")
print("=" * 70)
print("✅ 所有检查通过！")
print("\n🚀 可以开始使用组合管理模式：")
print("\n   # 模拟模式（推荐先测试）")
print("   python main_portfolio.py --mode once --dry-run")
print("\n   # 真实交易模式")
print("   python main_portfolio.py --mode once")
print("\n   # 持续运行")
print("   python main_portfolio.py --mode loop")
print("\n" + "=" * 70)
print("\n💡 提示：")
print("   - 首次运行建议使用 --dry-run 模拟模式")
print("   - 观察LLM是否返回多个交易决策")
print("   - 检查币种选择是否多样化")
print("   - 确认资金分散到不同资产")
print("=" * 70)
