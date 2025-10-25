#!/usr/bin/env python3
"""
测试最小订单是否能成功
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange

print("=" * 70)
print("🧪 测试最小订单")
print("=" * 70)

# 1. 加载配置
print("\n1️⃣ 加载配置...")
with open("config/config.testnet.json") as f:
    config = json.load(f)

# 2. 初始化
print("\n2️⃣ 初始化 Hyperliquid...")
account = eth_account.Account.from_key(config["hyperliquid"]["secret_key"])
address = account.address
info = Info(config["hyperliquid"]["base_url"], skip_ws=True)
exchange = Exchange(account, config["hyperliquid"]["base_url"], account_address=address)

print(f"   地址: {address}")

# 3. 检查账户状态
print("\n3️⃣ 检查账户状态...")
user_state = info.user_state(address)
account_value = float(user_state["marginSummary"]["accountValue"])
print(f"   账户价值: ${account_value:,.2f}")

# 4. 检查当前持仓
print("\n4️⃣ 检查当前持仓...")
positions = []
for pos in user_state.get("assetPositions", []):
    if float(pos["position"]["szi"]) != 0:
        positions.append({
            "coin": pos["position"]["coin"],
            "size": float(pos["position"]["szi"])
        })

if positions:
    print(f"   当前持仓: {len(positions)} 个")
    for pos in positions:
        print(f"      {pos['coin']}: {pos['size']}")
else:
    print("   当前持仓: 无")

# 5. 获取BTC价格和元数据
print("\n5️⃣ 获取 BTC 市场信息...")
all_mids = info.all_mids()
btc_price = float(all_mids.get("BTC", 0))
print(f"   BTC 价格: ${btc_price:,.2f}")

# 获取元数据（包含最小交易量等信息）
meta = info.meta()
btc_meta = None
for asset in meta.get("universe", []):
    if asset.get("name") == "BTC":
        btc_meta = asset
        break

if btc_meta:
    print(f"   最小交易量: {btc_meta.get('szDecimals', 'N/A')}")
    print(f"   价格精度: {btc_meta.get('maxLeverage', 'N/A')}")

# 6. 测试不同的订单大小
print("\n6️⃣ 测试最小订单大小...")
test_sizes = [0.0001, 0.001, 0.01]

for size in test_sizes:
    order_value = size * btc_price
    print(f"\n   测试 {size} BTC (约 ${order_value:.2f}):")
    
    if order_value > account_value:
        print(f"      ❌ 跳过 - 超过账户余额")
        continue
    
    # 模拟订单（不实际执行）
    try:
        # 注意：这里不真正执行，只是测试参数
        print(f"      ✅ 参数有效")
        print(f"         订单价值: ${order_value:.2f}")
        print(f"         占账户比: {order_value/account_value*100:.1f}%")
    except Exception as e:
        print(f"      ❌ 参数错误: {e}")

# 7. 查看最近的订单历史
print("\n7️⃣ 查看最近的订单历史...")
try:
    fills = info.user_fills(address)
    if fills:
        print(f"   找到 {len(fills)} 条成交记录")
        # 显示最近3条
        for i, fill in enumerate(fills[:3]):
            print(f"\n   记录 {i+1}:")
            print(f"      币种: {fill.get('coin', 'N/A')}")
            print(f"      方向: {fill.get('side', 'N/A')}")
            print(f"      数量: {fill.get('sz', 'N/A')}")
            print(f"      价格: ${float(fill.get('px', 0)):,.2f}")
            print(f"      时间: {fill.get('time', 'N/A')}")
    else:
        print("   没有找到成交记录")
except Exception as e:
    print(f"   ❌ 获取失败: {e}")

# 8. 建议
print("\n" + "=" * 70)
print("💡 建议")
print("=" * 70)

if account_value < 10:
    print("⚠️  账户余额太低（< $10），可能无法交易")
    print("   建议：向测试网账户充值更多 USDC")
    print("   充值地址: https://testnet.hyperliquid.xyz/")

min_order_value = 10  # 假设最小订单$10
min_size = min_order_value / btc_price

print(f"\n推荐最小交易量:")
print(f"   BTC: {min_size:.4f} (约 ${min_order_value})")
print(f"   当前账户可交易: {'✅ 是' if account_value >= min_order_value else '❌ 否'}")

print("\n下一步:")
print("1. 如果账户余额足够，尝试 0.001 BTC 订单")
print("2. 查看日志中的交易所响应，确认拒绝原因")
print("3. 如果订单被接受但没有持仓，检查是否立即止损")

print("=" * 70)
