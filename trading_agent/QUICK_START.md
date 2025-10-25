# 快速开始指南

## 🎯 5分钟上手

### 步骤 1: 安装依赖

```bash
cd trading_agent
pip install -r requirements.txt
```

### 步骤 2: 配置

```bash
# 复制配置模板
cp config/config.example.json config/config.json

# 编辑配置
vim config/config.json
```

**必填项**:
```json
{
  "hyperliquid": {
    "account_address": "你的钱包地址",
    "secret_key": "你的私钥",
    "base_url": "https://api.hyperliquid-testnet.xyz"  // 先用测试网！
  },
  "llm": {
    "api_key": "你的DeepSeek API Key",
    "base_url": "https://api.deepseek.com"
  },
  "risk": {
    "max_usable_capital": 100,    // 限制Agent只能使用100 USDC
    "enable_execution": false     // 第一次运行保持 false
  },
  "agent": {
    "check_interval": 300,        // 每5分钟检查一次
    "mode": "loop"                // 持续运行直到手动停止
  }
}
```

### 步骤 3: 运行

```bash
# 持续运行（默认，每5分钟检查一次）
python main.py

# 自定义检查间隔（每1分钟）
python main.py --interval 60

# 单次运行（测试用）
python main.py --mode once

# 停止Agent：按 Ctrl+C
```

---

## 📋 关键概念

### 运行模式

1. **loop** (默认): 持续运行，每隔一段时间检查市场，按 Ctrl+C 停止
2. **once**: 只运行一次就停止，用于测试

### 安全设置

```json
{
  "risk": {
    "max_usable_capital": 100,       // 🔒 限制Agent最多使用100 USDC（即使账户有更多）
    "max_position_size": 0.1,        // 单币种最多占可用资金10%
    "max_single_trade_value": 100,   // 单笔最多$100
    "allowed_coins": ["BTC", "ETH"], // 只交易BTC和ETH
    "enable_execution": false        // false=模拟, true=真实
  }
}
```

**重要**: 即使你的测试网账户有 999 USDC，设置 `max_usable_capital: 100` 后，Agent 只会使用其中的 100 USDC 进行计算和交易。

---

## 🔍 查看日志

```bash
# 实时查看日志
tail -f logs/trading.log

# 查看最近100行
tail -100 logs/trading.log
```

---

## ⚠️ 重要提示

### ❌ 不要做的事

1. ❌ 不要在主网上直接运行
2. ❌ 不要设置过高的 `max_single_trade_value`
3. ❌ 不要把 `config.json` 提交到 Git
4. ❌ 不要立即开启 `enable_execution: true`

### ✅ 应该做的事

1. ✅ 先在测试网运行几天
2. ✅ 观察 LLM 的决策是否合理
3. ✅ 小额测试真实交易
4. ✅ 定期检查日志

---

## 🎓 学习路径

### 第1周：观察模式
- 运行 Agent，不执行交易
- 观察 LLM 的分析和决策
- 理解市场数据和风险检查

### 第2周：模拟交易
- 记录每次决策
- 计算假设收益/亏损
- 调整策略提示词

### 第3周：小额实盘
- 设置 `max_single_trade_value: 10`
- 开启 `enable_execution: true`
- 密切监控

---

## 🛠️ 常见问题

### Q: 如何获取 Hyperliquid 测试网代币？
A: 访问 https://app.hyperliquid-testnet.xyz/ 并连接钱包

### Q: DeepSeek API 如何获取？
A: 访问 https://platform.deepseek.com/

### Q: 如何修改交易策略？
A: 编辑 `config/strategy_prompt.txt`

### Q: 出错了怎么办？
A: 检查 `logs/trading.log` 日志文件

---

## 📞 下一步

1. 阅读完整文档：`README.md`
2. 查看代码注释理解工作原理
3. 尝试修改策略提示词
4. 加入社区讨论（待建立）

---

**祝交易顺利！记住：保守和谨慎永远是对的。**
