# 🚀 高级交易功能说明

## 📋 新增功能概览

你的交易 Agent 现在是一个**专业级交易系统**，具备以下能力：

### ✅ 已实现的高级功能

| 功能 | 说明 | SDK 支持 |
|------|------|---------|
| **杠杆交易** | 1-50x 杠杆，全仓/逐仓 | `exchange.update_leverage()` |
| **止盈止损 (TP/SL)** | 自动风险控制 | `exchange.order()` with trigger |
| **K线历史数据** | 多周期技术分析 | `info.candles_snapshot()` |
| **交易历史** | 查看过往交易记录 | `info.user_fills()` |
| **技术指标** | RSI, SMA, EMA, 波动率 | 本地计算 |
| **市场趋势分析** | 综合判断市场状况 | 基于多指标 |
| **保证金管理** | 调整逐仓保证金 | `exchange.update_isolated_margin()` |

---

## 🎯 核心文件说明

### 1. **src/advanced_tools.py** - 高级工具类

```python
class AdvancedTradingTools:
    # 历史数据
    get_candles()                    # 获取K线数据
    get_trading_history()            # 获取交易历史
    calculate_technical_indicators()  # 计算技术指标
    
    # 杠杆管理
    adjust_leverage()                # 调整杠杆倍数
    adjust_isolated_margin()         # 调整保证金
    
    # 止盈止损
    place_order_with_tpsl()          # 带TP/SL的订单
    calculate_tpsl_prices()          # 计算TP/SL价格
    
    # 市场分析
    analyze_market_condition()       # 综合市场分析
```

### 2. **src/advanced_nodes.py** - 增强的 LangGraph 节点

```python
fetch_advanced_market_data_node()  # 获取增强市场数据
enhanced_llm_analysis_node()       # LLM 高级分析（含技术指标）
execute_advanced_trade_node()      # 执行高级交易（含杠杆/TP/SL）
```

### 3. **config/advanced_strategy_prompt.txt** - 专业策略提示词

- 📊 技术指标使用指南
- 🎯 杠杆使用规则
- 🛡️ 止盈止损策略
- 💡 实战决策示例

### 4. **main_advanced.py** - 高级交易主程序

完整的专业级交易系统。

---

## 📊 技术指标详解

### 1. RSI (相对强弱指标)

```
RSI = 100 - (100 / (1 + RS))
其中 RS = 平均涨幅 / 平均跌幅

解读：
- RSI < 30: 超卖，可能反弹
- RSI > 70: 超买，可能回调
- RSI 50: 中性
```

**交易信号**：
- ✅ RSI < 30 + 价格上涨 → 买入信号
- ❌ RSI > 70 + 价格下跌 → 卖出信号

### 2. SMA/EMA (移动平均线)

```
SMA = 最近N天收盘价的平均值
EMA = 指数加权移动平均（更敏感）

使用：
- EMA(12) > SMA(20): 短期向上
- EMA(12) < SMA(20): 短期向下
```

### 3. 波动率

```
波动率 = 标准差 / 均值

解读：
- > 0.02: 高波动（风险大）
- 0.01-0.02: 中等波动
- < 0.01: 低波动（适合交易）
```

---

## 💰 杠杆交易详解

### 工作原理

```
无杠杆：投入 $100，赚 5% = $5
2x杠杆：投入 $100，等于 $200 仓位，赚 5% = $10
5x杠杆：投入 $100，等于 $500 仓位，赚 5% = $25

但是！亏损也会放大：
5x杠杆：亏 5% = -$25（亏掉 1/4 本金）
```

### 使用示例

```python
# LLM 决策
{
  "decision": "buy",
  "coin": "BTC",
  "size": 0.001,
  "leverage": 3,  // 使用 3x 杠杆
  "use_tpsl": true,
  "take_profit_pct": 8.0,
  "stop_loss_pct": 3.0,
  "reasoning": "明确上涨趋势 + RSI确认，使用3x杠杆"
}
```

### 实际执行流程

```
1. Agent 调用: advanced_tools.adjust_leverage("BTC", 3)
   → SDK: exchange.update_leverage(3, "BTC", is_cross=True)
   
2. 杠杆设置成功
   
3. 执行交易: market_open("BTC", True, 0.001)
   → 仓位价值 = 当前价 × 0.001 × 3 倍
   
4. 设置 TP/SL 保护
```

### 安全建议

```
✅ 推荐做法：
  - 明确趋势下使用 2-3x
  - 必须设置止损
  - 小仓位测试

❌ 危险做法：
  - 超过 5x 杠杆
  - 不设止损
  - 逆势加杠杆
```

---

## 🛡️ 止盈止损 (TP/SL)

### 为什么需要 TP/SL？

```
场景 1：没有止损
买入 BTC @ $65,000
跌到 $60,000（-7.7%）
你想"等它涨回来"
继续跌到 $55,000（-15.4%）
💔 巨额亏损

场景 2：有止损
买入 BTC @ $65,000
设置止损 @ $63,050（-3%）
跌到 $63,050 自动平仓
✅ 小损失，保住本金
```

### 使用方式

```python
# SDK 层面
advanced_tools.place_order_with_tpsl(
    coin="BTC",
    is_buy=True,
    size=0.001,
    entry_price=None,  # 市价
    take_profit_price=68250,  # +5%
    stop_loss_price=63050     # -3%
)

# LLM 决策层面
{
  "decision": "buy",
  "use_tpsl": true,
  "take_profit_pct": 5.0,
  "stop_loss_pct": 3.0
}
```

### TP/SL 策略

| 风险等级 | 止盈 | 止损 | 适用场景 |
|---------|------|------|---------|
| 保守 | 3-5% | 2-3% | 低杠杆，稳健交易 |
| 适中 | 5-8% | 3-4% | 中等信号 |
| 激进 | 8-15% | 2-3% | 高杠杆（止损要严！）|

---

## 📈 历史数据分析

### K线数据

```python
# 获取 1小时 K线，回看 24小时
candles = advanced_tools.get_candles("BTC", "1h", 24)

# 返回格式
[
  {
    "time": 1234567890000,
    "open": 65000.0,
    "high": 65500.0,
    "low": 64800.0,
    "close": 65200.0,
    "volume": 1234.5
  },
  ...
]

# 支持的周期
"1m", "5m", "15m", "1h", "4h", "1d"
```

### 交易历史

```python
history = advanced_tools.get_trading_history(limit=50)

# 返回最近50笔交易
[
  {
    "time": "2024-01-01 12:00:00",
    "coin": "BTC",
    "side": "buy",
    "size": 0.001,
    "price": 65000.0,
    "fee": 0.05,
    "closed_pnl": 5.2  # 已实现盈亏
  },
  ...
]
```

### LLM 如何使用这些数据

```
Agent 流程：
1. 获取 BTC 24小时 K线
2. 计算 RSI, SMA, EMA
3. 分析趋势（bullish/bearish/neutral）
4. 结合交易历史（之前是否盈利？）
5. 综合决策

LLM 会收到：
"BTC 分析:
  当前价格: $65,432.10
  24h涨跌: +3.2%
  RSI(14): 62.3
  SMA(20): $64,800.00
  波动率: 1.5%
  市场趋势: bullish
  建议: buy
  原因: RSI超卖且价格上涨，24h涨幅超过3%"
```

---

## 🚀 如何使用高级功能

### 方式 1: 使用高级主程序

```bash
# 启动高级 Agent
python main_advanced.py --config config/config.testnet.json

# 单次运行测试
python main_advanced.py --mode once

# 快速检查（每1分钟）
python main_advanced.py --interval 60
```

### 方式 2: 集成到现有程序

```python
from src.advanced_tools import AdvancedTradingTools
from src.advanced_nodes import enhanced_llm_analysis_node

# 创建高级工具
advanced_tools = AdvancedTradingTools(info, exchange, address)

# 获取市场分析
analysis = advanced_tools.analyze_market_condition("BTC")
# {'trend': 'bullish', 'strength': 65, ...}

# 调整杠杆
advanced_tools.adjust_leverage("BTC", 3, dry_run=False)

# 带 TP/SL 下单
advanced_tools.place_order_with_tpsl(
    coin="BTC",
    is_buy=True,
    size=0.001,
    take_profit_price=68000,
    stop_loss_price=63000,
    dry_run=False
)
```

---

## 📊 实际运行示例

### 启动日志

```
🚀 高级 LangGraph 自动交易 Agent 启动
====================================================================
📌 功能: 杠杆 | 止盈止损 | 技术分析 | 历史数据
====================================================================
📍 账户地址: 0xYourAddress
🤖 LLM: deepseek - deepseek-chat
====================================================================
💰 账户实际余额: $999.00 USDC
🔒 Agent可用资金: $100.00 USDC (受限)
📊 资金使用率: 10.0%
====================================================================
🔴 真实交易模式：请谨慎！
```

### 分析周期日志

```
【第 1 轮高级分析】
==================================================
🚀 开始新的高级交易周期
==================================================
📊 获取高级市场数据...
获取 BTC K线数据: 24 根，周期 1h
技术指标计算完成: RSI=58.3, 涨跌幅=+2.8%
市场分析: BTC 趋势=bullish, 强度=62

💼 获取账户状态...
账户价值: $100.00

🤖 LLM 高级分析...
决策: buy, 币种: BTC, 数量: 0.0008, 杠杆: 2x, TP/SL: true

⚠️  风险检查...
✅ 风险检查通过

💰 执行高级交易...
[真实] 调整 BTC 杠杆: 2x (全仓)
[真实] 买入 0.0008 BTC with TP/SL
✅ 止盈设置: $68,500.00 (+5%)
✅ 止损设置: $63,350.00 (-3%)
✅ 交易成功

==================================================
📋 高级交易周期总结
==================================================
💰 账户总价值: $999.00
🔒 可用资金: $100.00 (受限)
📊 当前持仓: 1 个
  📈 BTC: 0.0008, 入场$65000.00, 盈亏$+0.00, 2x杠杆

🤔 决策: BUY
   币种: BTC
   数量: 0.0008
   杠杆: 2x
   止盈: 5.0%
   止损: 3.0%
   置信度: 75%

✅ 风险检查: ✅ 通过

🔍 决策理由:
BTC 显示明确上涨趋势，RSI 58.3 处于健康区间，24小时涨幅2.8%，
市场趋势评分62（看涨）。使用2x杠杆放大收益，同时设置5%止盈
和3%止损严格控制风险。预期收益风险比 1.67:1。
==================================================
```

---

## ⚠️ 重要提醒

### 使用杠杆的风险

```
❌ 常见错误：
1. 新手就用高杠杆（5x+）
2. 亏损时加仓摊平成本
3. 不设止损"等回本"
4. 重仓单一币种

✅ 正确做法：
1. 从 1-2x 开始练习
2. 必须设置止损
3. 小仓位分散风险
4. 盈利后逐步提高
```

### 止损的重要性

```
真实案例：
- 本金 $1000
- 5x 杠杆买入 BTC
- 没有止损
- 跌 20% = 爆仓，本金归零

如果有止损：
- 止损 -3%
- 实际亏损: $1000 × 5 × 3% = $150
- 剩余: $850
- 还能继续交易
```

---

## 🎓 学习建议

### 第1周：理解工具

```bash
# 单次运行，观察输出
python main_advanced.py --mode once

# 重点学习：
- 技术指标如何计算？
- LLM 如何使用这些指标？
- 杠杆如何影响盈亏？
```

### 第2周：小额测试

```json
{
  "risk": {
    "max_usable_capital": 50,
    "max_single_trade_value": 20,
    "max_leverage": 2,  // 限制最大杠杆
    "enable_execution": true
  }
}
```

### 第3周：策略优化

- 调整 TP/SL 百分比
- 修改技术指标阈值
- 尝试不同杠杆组合
- 记录和分析结果

---

## 📚 SDK 功能对照表

| Agent 功能 | SDK 方法 | 文件位置 |
|-----------|----------|---------|
| 获取K线 | `info.candles_snapshot()` | hyperliquid/info.py:473 |
| 交易历史 | `info.user_fills()` | hyperliquid/info.py:199 |
| 调整杠杆 | `exchange.update_leverage()` | hyperliquid/exchange.py:357 |
| 调整保证金 | `exchange.update_isolated_margin()` | hyperliquid/exchange.py:379 |
| 止盈止损单 | `exchange.order()` with trigger | hyperliquid/exchange.py:111 |
| 市价开仓 | `exchange.market_open()` | hyperliquid/exchange.py:214 |
| 市价平仓 | `exchange.market_close()` | hyperliquid/exchange.py:231 |

---

## 🚦 快速开始

```bash
# 1. 安装依赖（如果还没有）
pip install -r requirements.txt

# 2. 测试连接
python test_connection.py

# 3. 启动高级 Agent
python main_advanced.py --config config/config.testnet.json

# 4. 观察日志
tail -f logs/advanced_trading.log
```

---

**现在你拥有了一个专业级的交易系统。请谨慎使用，持续学习，理性交易！** 📈🚀
