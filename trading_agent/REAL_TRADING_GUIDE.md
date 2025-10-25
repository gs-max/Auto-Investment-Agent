# 真实交易启用指南

## ⚠️ 重要提醒

虽然是测试网，但请像对待真实资金一样谨慎！这将帮助你建立良好的交易习惯。

---

## 🔄 已完成的改进

### 1. LLM Function Calling

LLM 现在使用 **Function Calling** 返回结构化决策：

```json
{
  "decision": "buy",
  "coin": "BTC",
  "size": 0.001,
  "reasoning": "BTC 显示上涨趋势...",
  "confidence": 0.75
}
```

**优势**：
- ✅ 精确提取交易参数（coin, size）
- ✅ 避免文本解析错误
- ✅ 支持置信度评估

### 2. 改进的交易执行

- ✅ 正确调用 Hyperliquid SDK
- ✅ 详细的执行日志
- ✅ 错误处理和反馈

### 3. 更新的策略提示词

- ✅ 强调保守策略
- ✅ 小额交易（BTC < 0.01, ETH < 0.1）
- ✅ 明确的决策规则

---

## 📝 启用真实交易步骤

### 步骤 1: 准备配置文件

已为你创建 `config/config.testnet.json`：

```json
{
  "hyperliquid": {
    "account_address": "你的测试网地址",
    "secret_key": "你的测试网私钥",
    "base_url": "https://api.hyperliquid-testnet.xyz"
  },
  "llm": {
    "api_key": "你的DeepSeek API Key",
    "model": "deepseek-chat"
  },
  "risk": {
    "max_usable_capital": 100,
    "max_single_trade_value": 50,
    "allowed_coins": ["BTC", "ETH"],
    "enable_execution": true  // ← 关键：开启真实交易
  }
}
```

### 步骤 2: 填写配置

```bash
# 编辑配置文件
vim config/config.testnet.json
```

**必填项**：
1. `account_address`: 你的 Hyperliquid 测试网钱包地址
2. `secret_key`: 你的测试网私钥（**永远不要用主网私钥！**）
3. `api_key`: DeepSeek API Key

### 步骤 3: 检查测试网余额

```bash
# 访问测试网
https://app.hyperliquid-testnet.xyz/

# 确保你有 100+ USDC 测试币
```

### 步骤 4: 运行（真实交易模式）

```bash
# 使用真实交易配置
python main.py --config config/config.testnet.json --interval 300
```

---

## 🔍 运行日志示例

### 启动日志

```
🚀 LangGraph 自动交易 Agent 启动
============================================================
📍 账户地址: 0xYourAddress
🤖 LLM: deepseek - deepseek-chat
============================================================
💰 账户实际余额: $999.00 USDC
🔒 Agent可用资金: $100.00 USDC (受限)
📊 资金使用率: 10.0%
============================================================
🔴 真实交易模式：请谨慎！  ← 注意这个提示
🔄 持续运行模式，检查间隔: 300 秒
按 Ctrl+C 可随时停止
```

### 交易决策日志

```
【第 1 轮检查】
==================================================
🚀 开始新的交易周期
==================================================
📊 获取市场数据...
获取到 50 个币种价格

💼 获取账户状态...
账户价值: $100.00

🤖 LLM 分析市场...
决策: buy, 币种: BTC, 数量: 0.001  ← Function Calling 输出

⚠️  风险检查...
✅ 风险检查通过

💰 执行交易...
[真实交易] 买入 0.001 BTC  ← 真实交易标记
✅ 交易成功: [{'oid': 123456, 'size': '0.001', 'price': '65432.10'}]

==================================================
📋 交易周期总结
==================================================
💰 账户总价值: $999.00
🔒 可用资金: $100.00 (受限)
📊 当前持仓: 1 个

🤔 决策: BUY
✅ 风险检查: ✅ 通过

🔍 LLM 分析:
BTC 显示明确上涨趋势，24小时涨幅3.2%，建议小量买入捕捉行情...

💼 执行结果: {'success': True, 'dry_run': False, 'coin': 'BTC', ...}
==================================================
```

---

## 🎯 LLM 决策流程

### 完整流程

```
1. 获取市场数据
   ├─ BTC: $65,432.10
   ├─ ETH: $3,456.78
   └─ 其他币种...

2. 获取账户状态
   ├─ 可用资金: $100
   └─ 当前持仓: []

3. LLM 分析（使用 Function Calling）
   ├─ 输入: 价格 + 持仓 + 策略
   └─ 输出: {
         "decision": "buy",
         "coin": "BTC",
         "size": 0.001,
         "reasoning": "上涨趋势明确...",
         "confidence": 0.75
       }

4. 风险检查
   ├─ ✅ 币种在白名单 (BTC)
   ├─ ✅ 交易金额 $65 < $50限制... ❌ 拒绝！
   └─ 或调整 size 为 0.0007 → 通过

5. 执行交易
   ├─ 调用 exchange.market_open("BTC", True, 0.0007)
   └─ 等待成交反馈

6. 记录结果
   └─ 持仓更新: BTC 0.0007 @ $65,432
```

---

## ⚙️ 风险控制参数

### 当前设置（推荐新手）

```json
{
  "risk": {
    "max_usable_capital": 100,      // 只用100 USDC
    "max_position_size": 0.1,       // 单币种最多10 USDC
    "max_total_exposure": 0.5,      // 总持仓最多50 USDC
    "max_single_trade_value": 50,   // 单笔最多50 USDC
    "min_account_value": 10,        // 最低保留10 USDC
    "allowed_coins": ["BTC", "ETH"],
    "max_leverage": 3,
    "enable_execution": true
  }
}
```

### 更保守设置

```json
{
  "risk": {
    "max_usable_capital": 50,       // 只用50 USDC
    "max_single_trade_value": 20,   // 单笔最多20 USDC
    "max_leverage": 1,              // 不使用杠杆
    "enable_execution": true
  }
}
```

---

## 🛡️ 安全检查清单

### 运行前检查

- [ ] 使用的是**测试网** URL (`https://api.hyperliquid-testnet.xyz`)
- [ ] 使用的是**测试网私钥**（不是主网）
- [ ] `max_usable_capital` 设置合理（≤ 100）
- [ ] `max_single_trade_value` 限制较小（≤ 50）
- [ ] 已阅读并理解策略提示词
- [ ] 知道如何停止 Agent（Ctrl+C）

### 运行中监控

- [ ] 每次检查日志中的决策
- [ ] 确认交易数量合理
- [ ] 观察风险检查是否生效
- [ ] 定期查看持仓和余额

### 异常情况

**如果出现问题，立即停止**：
```bash
# 按 Ctrl+C 停止 Agent

# 手动平仓（如有需要）
cd hyperliquid-python-sdk/examples
python basic_market_order.py  # 修改为平仓操作
```

---

## 📊 预期行为

### LLM 应该做什么

✅ **大部分时间选择 hold**
- 只在明确信号时才交易
- 默认保守观望

✅ **小额交易**
- BTC: 0.001 - 0.01（$65 - $650）
- ETH: 0.01 - 0.1（$35 - $350）

✅ **及时止损**
- 亏损超过 3% 立即平仓

✅ **适度获利**
- 盈利超过 5% 考虑平仓

### LLM 不应该做什么

❌ **频繁交易** - 每轮都操作
❌ **大额交易** - 单次超过 $50
❌ **追涨杀跌** - 情绪化决策
❌ **使用高杠杆** - 超过 3x

---

## 🔧 调试技巧

### 查看详细日志

```bash
# 实时查看
tail -f logs/trading.log

# 搜索关键信息
grep "真实交易" logs/trading.log
grep "决策:" logs/trading.log
grep "执行结果" logs/trading.log
```

### 测试 LLM 决策

```bash
# 单次运行测试
python main.py --config config/config.testnet.json --mode once

# 观察 LLM 的输出是否合理
```

### 如果 LLM 决策异常

1. 检查 `strategy_prompt.txt` 是否被修改
2. 查看 `confidence` 分数是否合理
3. 确认风险检查是否正常工作

---

## 📈 运行建议

### 第一天：观察模式

```bash
# 先观察 LLM 的决策，不执行
"enable_execution": false
```

运行一整天，查看日志：
- LLM 决策是否合理？
- 交易频率如何？
- 有没有异常决策？

### 第二天：小额真实交易

```bash
# 开启真实交易，严格限制
"enable_execution": true,
"max_usable_capital": 50,
"max_single_trade_value": 20
```

每2-4小时检查一次：
- 查看持仓情况
- 评估盈亏
- 调整参数

### 后续：逐步优化

根据表现调整：
- 策略参数（涨跌幅阈值）
- 风险限制（可用资金、单笔限额）
- 检查间隔（更频繁或更稀疏）

---

## 🚨 常见问题

### Q1: 如何确认是真实交易？

**A**: 查看日志中的标记：
```
[真实交易] 买入 0.001 BTC  ← 真实
[模拟] 买入 0.001 BTC      ← 模拟
```

### Q2: LLM 总是 hold，不交易？

**A**: 这是正常的！保守策略下，LLM 应该：
- 80% 时间 hold
- 只在明确信号时交易

### Q3: 交易失败了怎么办？

**A**: 查看错误日志：
```
订单错误: Insufficient balance
```
可能原因：
- 余额不足
- 数量太小（低于最小交易量）
- 网络问题

### Q4: 如何手动平仓？

**A**: 两种方式：
1. 等待 LLM 自动平仓（亏损>3% 或盈利>5%）
2. 修改策略提示词，强制平仓

### Q5: 可以在主网运行吗？

**A**: **不建议！** 除非你：
- 已在测试网运行数周
- 完全理解每个参数
- 接受可能的损失
- 使用极小金额测试

---

## 📞 获取帮助

如有问题：
1. 查看 `logs/trading.log`
2. 检查配置文件
3. 阅读策略提示词
4. 运行单次测试 `--mode once`

---

**祝测试顺利！记住：真实交易永远从小额开始。**
