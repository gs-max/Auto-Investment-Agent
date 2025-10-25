#!/usr/bin/env python3
"""
测试数据获取功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

print("=" * 70)
print("🔍 测试数据获取功能")
print("=" * 70)

# 1. 加载配置
print("\n1️⃣ 加载配置...")
try:
    with open("config/config.testnet.json") as f:
        config = json.load(f)
    print("   ✅ 配置加载成功")
except Exception as e:
    print(f"   ❌ 配置加载失败: {e}")
    sys.exit(1)

# 2. 初始化 Hyperliquid
print("\n2️⃣ 初始化 Hyperliquid SDK...")
try:
    account = eth_account.Account.from_key(config["hyperliquid"]["secret_key"])
    address = account.address
    
    info = Info(config["hyperliquid"]["base_url"], skip_ws=True)
    exchange = Exchange(
        account,
        config["hyperliquid"]["base_url"],
        account_address=address
    )
    print(f"   ✅ 初始化成功")
    print(f"   账户地址: {address}")
except Exception as e:
    print(f"   ❌ 初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 测试获取价格数据
print("\n3️⃣ 测试获取价格数据...")
try:
    print("   → 调用 info.all_mids()...")
    prices = info.all_mids()
    print(f"   ✅ 成功获取 {len(prices)} 个币种价格")
    
    # 显示部分数据
    print("\n   主要币种价格:")
    for coin in ["BTC", "ETH", "SOL"]:
        if coin in prices:
            print(f"      {coin}: ${prices[coin]:,.2f}")
        else:
            print(f"      {coin}: 未找到")
    
except Exception as e:
    print(f"   ❌ 获取价格失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 测试获取账户状态
print("\n4️⃣ 测试获取账户状态...")
try:
    print("   → 调用 info.user_state()...")
    user_state = info.user_state(address)
    
    account_value = float(user_state["marginSummary"]["accountValue"])
    print(f"   ✅ 账户价值: ${account_value:,.2f}")
    
    # 显示详细信息
    margin = user_state["marginSummary"]
    print(f"\n   账户详情:")
    print(f"      总价值: ${float(margin['accountValue']):,.2f}")
    print(f"      总仓位: ${float(margin['totalNtlPos']):,.2f}")
    print(f"      总盈亏: ${float(margin['totalRawUsd']):,.2f}")
    
except Exception as e:
    print(f"   ❌ 获取账户状态失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试获取持仓
print("\n5️⃣ 测试获取持仓...")
try:
    print("   → 调用 info.user_state() 获取持仓...")
    positions = user_state.get("assetPositions", [])
    print(f"   ✅ 持仓数量: {len(positions)}")
    
    if positions:
        print("\n   持仓详情:")
        for pos in positions:
            coin = pos["position"]["coin"]
            size = float(pos["position"]["szi"])
            entry_px = float(pos["position"]["entryPx"])
            pnl = float(pos["position"]["unrealizedPnl"])
            print(f"      {coin}: 数量={size}, 入场价=${entry_px:,.2f}, 盈亏=${pnl:,.2f}")
    else:
        print("   无持仓")
    
except Exception as e:
    print(f"   ❌ 获取持仓失败: {e}")
    import traceback
    traceback.print_exc()

# 6. 测试获取K线数据
print("\n6️⃣ 测试获取K线数据...")
try:
    coin = "BTC"
    print(f"   → 调用 info.candles_snapshot() 获取 {coin} K线...")
    candles = info.candles_snapshot(coin, "1h", 24)
    print(f"   ✅ 成功获取 {len(candles)} 根K线")
    
    if candles:
        last_candle = candles[-1]
        print(f"\n   最新K线 ({coin}):")
        print(f"      时间: {last_candle['t']}")
        print(f"      开盘: ${float(last_candle['o']):,.2f}")
        print(f"      收盘: ${float(last_candle['c']):,.2f}")
        print(f"      最高: ${float(last_candle['h']):,.2f}")
        print(f"      最低: ${float(last_candle['l']):,.2f}")
        print(f"      成交量: {float(last_candle['v']):,.2f}")
    
except Exception as e:
    print(f"   ❌ 获取K线失败: {e}")
    import traceback
    traceback.print_exc()

# 7. 总结
print("\n" + "=" * 70)
print("📊 测试总结")
print("=" * 70)
print("✅ 配置加载: 成功")
print(f"✅ SDK初始化: 成功")
print(f"{'✅' if 'prices' in locals() and prices else '❌'} 价格数据: {'成功' if 'prices' in locals() and prices else '失败'}")
print(f"{'✅' if 'account_value' in locals() else '❌'} 账户状态: {'成功' if 'account_value' in locals() else '失败'}")
print(f"{'✅' if 'positions' in locals() else '❌'} 持仓数据: {'成功' if 'positions' in locals() else '失败'}")
print(f"{'✅' if 'candles' in locals() and candles else '❌'} K线数据: {'成功' if 'candles' in locals() and candles else '失败'}")
print("=" * 70)

print("\n💡 如果所有测试都通过，说明数据获取功能正常")
print("   如果 main_advanced.py 不显示数据，可能是流程或打印问题")
