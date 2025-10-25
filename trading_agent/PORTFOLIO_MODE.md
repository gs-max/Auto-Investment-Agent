# 🎯 多资产组合管理模式

## 概述

将交易Agent从**单币种交易员**升级为**多资产组合管理者**。

### 核心特性

✅ **无币种限制** - 可以交易任何加密货币  
✅ **多持仓管理** - 同时持有3-8个不同资产  
✅ **多决策执行** - 每次分析返回2-4个交易动作  
✅ **智能分散** - 自动分散风险到不同资产  
✅ **主动调仓** - 根据市场变化动态调整组合  

---

## 🆚 新旧模式对比

| 特性 | 旧模式（单币种） | 新模式（组合管理） |
|------|------------------|-------------------|
| **币种限制** | 通常BTC/ETH | **无限制，任何币种** |
| **每次决策** | 1个交易 | **2-4个交易** |
| **持仓数量** | 通常1-2个 | **3-8个** |
| **风险管理** | 单一止损 | **分散+对冲** |
| **策略** | 趋势跟随 | **组合优化** |
| **AI角色** | 交易员 | **组合管理者** |

---

## 📁 新增文件

### 1. `config/portfolio_strategy_prompt.txt`
**新的策略提示** - 教LLM成为组合管理者

核心理念：
- 你是自由的专业交易员
- 同时管理多个持仓
- 每次做2-4个决策
- 分散风险，主动调仓

### 2. `src/portfolio_nodes.py`
**新的节点实现** - 支持多交易决策

- `enhanced_portfolio_analysis_node()` - 多资产分析
- `execute_portfolio_trades_node()` - 批量执行交易

### 3. `main_portfolio.py`
**新的主程序** - 使用组合管理模式

---

## 🚀 使用方法

### 方式1：单次测试（推荐）

```bash
# 模拟交易模式（安全测试）
python main_portfolio.py --mode once --dry-run

# 真实交易模式
python main_portfolio.py --mode once
```

### 方式2：持续运行

```bash
# 每60秒执行一次组合调整
python main_portfolio.py --mode loop

# 自定义间隔（在config中设置）
python main_portfolio.py --mode loop --config config/config.testnet.json
```

### 命令行参数

```bash
python main_portfolio.py \
    --config config/config.testnet.json \     # 配置文件
    --strategy config/portfolio_strategy_prompt.txt \  # 策略文件
    --mode once \                              # 运行模式：once/loop
    --dry-run                                  # 模拟模式（可选）
```

---

## 📊 配置调整

### `config/config.testnet.json`

新增配置项：

```json
{
  "risk": {
    "max_positions": 8,        // ← 新增：最多持仓数
    "min_position_value": 20,  // ← 新增：最小持仓价值
    "max_position_size": 0.25, // 修改：单仓位降到25%
    "max_total_exposure": 0.95,// 修改：总仓位提高到95%
    "allowed_coins": []         // 空=无限制
  }
}
```

---

## 🎯 实际运行示例

### 场景1：空仓启动

**LLM分析**：
```
账户$999，无持仓
扫描市场：ETH稳定，SOL波动高，DOGE上涨
```

**决策**：
```json
[
  {"decision": "buy", "coin": "ETH", "size": 0.04, "leverage": 2},
  {"decision": "buy", "coin": "SOL", "size": 0.6, "leverage": 3},
  {"decision": "buy", "coin": "DOGE", "size": 150, "leverage": 5}
]
```

**结果**：
```
✅ ETH  做多 $160 (2x杠杆)
✅ SOL  做多 $120 (3x杠杆)
✅ DOGE 做多 $50  (5x杠杆)

组合：3个持仓，$330投入，分散风险
```

### 场景2：已有持仓，需要调整

**当前持仓**：
```
ETH  +5% 盈利
SOL  -2% 亏损
AVAX 持平
```

**LLM分析**：
```
ETH达到止盈 → 平仓
SOL趋势转差 → 止损
发现UNI机会 → 开仓
发现BTC下跌 → 做空对冲
```

**决策**：
```json
[
  {"decision": "close", "coin": "ETH"},
  {"decision": "close", "coin": "SOL"},
  {"decision": "buy", "coin": "UNI", "size": 8.0, "leverage": 3},
  {"decision": "sell", "coin": "BTC", "size": 0.001, "leverage": 2}
]
```

**结果**：
```
✅ ETH  平仓 → 锁定+5%利润
✅ SOL  止损 → 控制-2%损失
✅ UNI  做多 $100 → 新机会
✅ BTC  做空 $60  → 对冲风险

组合：AVAX + UNI(多) + BTC(空)，风险对冲
```

---

## 💡 AI决策逻辑

### 1. 评估现有持仓
```python
for position in current_positions:
    if profit > take_profit:
        决策: 平仓锁定利润
    elif loss > stop_loss:
        决策: 止损离场
    elif trend_changed:
        决策: 加仓或减仓
```

### 2. 扫描市场机会
```python
扫描顺序:
1. 主流币（ETH, SOL, AVAX...）
2. 高波动币（DOGE, SHIB...）
3. DeFi币（UNI, AAVE...）
4. 其他有技术指标的币种

选择标准:
- RSI 在机会区间
- 24h涨跌幅显示趋势
- 波动率适中
```

### 3. 组合构建
```python
资金分配:
- 核心持仓（40%）: 稳定币如ETH
- 机会持仓（40%）: 高波动币如SOL, DOGE
- 对冲持仓（20%）: 反向持仓如BTC空单

风险控制:
- 单仓位 ≤ 25%
- 总仓位 ≤ 95%
- 持仓数 3-8 个
```

---

## 📋 输出格式

### 终端输出

```
🎯 投资组合决策
======================================================================

📊 组合分析：
当前市场处于中性偏多状态，ETH和SOL显示上涨信号，DOGE动量强劲。
采用多元化组合策略，分散投资到3个不同资产，总投资$330，留$670应急。

📋 计划执行 3 个交易：

1. 📈 买入
   币种: ETH
   数量: 0.04
   杠杆: 2x
   止盈: 3.0% / 止损: 1.5%
   理由: ETH作为核心持仓，稳定可靠，2x杠杆控制风险
   置信度: 65%

2. 📈 买入
   币种: SOL
   数量: 0.6
   杠杆: 3x
   止盈: 4.0% / 止损: 2.0%
   理由: SOL RSI偏低且上升，高波动适合3x杠杆
   置信度: 70%

3. 📈 买入
   币种: DOGE
   数量: 150
   杠杆: 5x
   止盈: 5.0% / 止损: 2.5%
   理由: DOGE 24h上涨5%，动量强劲，小仓位高杠杆
   置信度: 60%

======================================================================
```

### 执行过程

```
🔄 开始执行组合交易
======================================================================

[1/3] 执行: BUY ETH
2025-10-25 09:47:12,345 - src.advanced_tools - INFO - 📤 发送市价单: 买入 0.04 ETH
2025-10-25 09:47:13,456 - src.advanced_tools - INFO - 📥 交易所响应: {...}
2025-10-25 09:47:14,567 - src.advanced_tools - INFO - ✅ 止盈设置: $4100.00
2025-10-25 09:47:15,678 - src.advanced_tools - INFO - ✅ 止损设置: $3900.00
   ✅ 成功

[2/3] 执行: BUY SOL
   ✅ 成功

[3/3] 执行: BUY DOGE
   ✅ 成功

======================================================================
📊 执行汇总
======================================================================
成功: 3/3
失败: 0/3
======================================================================
```

---

## ⚙️ 技术实现

### Function Calling Schema

```python
{
    "name": "make_portfolio_decisions",
    "parameters": {
        "trades": [
            {
                "decision": "buy" | "sell" | "close",
                "coin": "币种",
                "size": 数量,
                "leverage": 杠杆,
                "use_tpsl": true/false,
                "take_profit_pct": 止盈%,
                "stop_loss_pct": 止损%,
                "reasoning": "理由",
                "confidence": 0-1
            }
        ],
        "portfolio_analysis": "整体分析"
    }
}
```

### LangGraph Workflow

```
fetch_market_data (获取市场数据)
    ↓
get_account_status (获取账户状态)
    ↓
portfolio_analysis (组合分析 - 返回2-4个交易)
    ↓
execute_portfolio (批量执行所有交易)
    ↓
END
```

---

## 🔍 故障排查

### 问题1：LLM只返回1个交易

**原因**：策略提示没有生效

**解决**：
```bash
# 确认使用了正确的策略文件
python main_portfolio.py --strategy config/portfolio_strategy_prompt.txt
```

### 问题2：某些币种无法交易

**原因**：持仓量达到上限（Open Interest Cap）

**解决**：
- LLM会自动尝试其他币种
- 日志会显示具体错误
- 选择流动性更好的币种

### 问题3：风险检查拦截

**原因**：单笔交易超过限制

**解决**：
- LLM会自动调整仓位大小
- 或分散到更多小仓位

---

## 📈 性能对比

### 旧模式（单币种）
```
持仓: BTC做多 $500
风险: 集中于单一资产
收益: 依赖BTC涨跌
```

### 新模式（组合）
```
持仓:
- ETH  做多 $150
- SOL  做多 $120
- DOGE 做多 $80
- UNI  做多 $70
- BTC  做空 $60

风险: 分散到5个资产+对冲
收益: 多个机会，降低单一风险
```

**优势**：
- ✅ 单一资产暴跌不会导致全盘失败
- ✅ 捕捉多个市场机会
- ✅ 对冲策略降低整体波动
- ✅ 更符合专业交易员做法

---

## 🎓 最佳实践

### 1. 资金分配
```
核心持仓（40%）：ETH, SOL, AVAX
机会持仓（40%）：DOGE, UNI, MATIC
对冲持仓（20%）：BTC空单, ETH空单
```

### 2. 杠杆使用
```
低风险：1-2x（核心持仓）
中风险：2-5x（机会持仓）
高风险：5-10x（小仓位试探）
```

### 3. 止盈止损
```
每个持仓都设置：
- 止盈：2-5%
- 止损：1-2%

组合整体：
- 单日亏损不超过5%
- 及时调整表现差的持仓
```

---

## 🚀 下一步

### 1. 测试运行
```bash
# 先用模拟模式测试
python main_portfolio.py --mode once --dry-run

# 确认无误后真实交易
python main_portfolio.py --mode once
```

### 2. 观察结果
- 查看LLM是否选择多个币种
- 检查资金是否分散
- 确认止盈止损设置

### 3. 调整策略
- 修改 `portfolio_strategy_prompt.txt`
- 调整风险参数
- 优化币种选择逻辑

---

## ✅ 总结

**核心改变**：
1. ✅ LLM从单币种交易员 → 多资产组合管理者
2. ✅ 每次1个决策 → 每次2-4个决策
3. ✅ 有币种限制 → 无限制，自由选择
4. ✅ 单一持仓 → 3-8个分散持仓
5. ✅ 被动交易 → 主动调仓

**预期效果**：
- 风险更分散
- 机会更多
- 收益更稳定
- 更像真正的交易专家

**开始使用**：
```bash
python main_portfolio.py --mode once --dry-run
```

**祝交易成功！** 🎯📈
