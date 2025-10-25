# 🔧 故障排查指南

## 问题：LLM 不进行交易

### 已完成的修复

#### 1. **条件分支修复** ✅
**文件**: `main_advanced.py` 第122-130行

```python
# 修改前（有问题）
lambda s: "execute" if s["risk_passed"] or s["trading_decision"] == "hold" else "end"

# 修改后（强制交易）
lambda s: "execute" if s["trading_decision"] in ["buy", "sell", "close"] else "end"
```

**效果**: 只要LLM做出决策（buy/sell/close），就会执行，不会因为风险检查失败而跳过。

---

#### 2. **风险检查失败自动降级** ✅
**文件**: `src/advanced_nodes.py` 第257-271行

```python
# 如果风险检查不通过，自动降级为最小风险参数
if not state["risk_passed"]:
    logger.warning("🔧 强制交易模式：自动调整为最小风险参数")
    state["target_size"] = 0.001
    state["target_leverage"] = 1
    state["use_tpsl"] = True
    state["take_profit_pct"] = 2.0
    state["stop_loss_pct"] = 1.0
```

**效果**: 即使LLM选择的参数过于激进导致风险检查失败，系统会自动降级为最安全的参数后执行。

---

#### 3. **增强日志输出** ✅

**LLM 决策日志**:
```
✅ LLM 决策成功
   决策: buy
   币种: BTC
   数量: 0.01
   杠杆: 3x
   止盈止损: True
   理由: RSI 48接近中性...
   置信度: 0.6
```

**风险检查日志**:
```
✅ 风险检查通过: 通过所有风险检查
或
❌ 风险检查失败: 交易金额超过限制
   决策: buy, 币种: BTC, 数量: 0.01
```

**执行前日志**:
```
🎯 准备执行: buy 0.001 BTC, 杠杆: 1x, TP/SL: True
```

---

### 如何测试

#### **方法 1: 单次测试**

```bash
cd "/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent"

# 运行单次测试
python test_forced_trading.py

# 或直接运行
python main_advanced.py --mode once
```

#### **方法 2: 查看详细日志**

```bash
# 运行并实时查看日志
python main_advanced.py --mode once 2>&1 | tee test_output.log

# 或者先运行，再查看日志
python main_advanced.py --mode once
cat logs/advanced_trading.log
```

---

### 关键日志检查点

运行后，检查日志中是否出现以下内容：

#### ✅ **正常流程（应该看到）**

```
🚀 开始新的高级交易周期
📊 获取高级市场数据...
  获取 K线数据: BTC
  计算技术指标...
  RSI: 48.5
  
👤 获取账户状态...
💰 账户价值: $999.00

🤖 LLM 高级分析...
✅ LLM 决策成功
   决策: buy
   币种: BTC
   数量: 0.01
   杠杆: 3x

⚠️ 风险检查...
✅ 风险检查通过

💰 执行高级交易...
🎯 准备执行: buy 0.01 BTC, 杠杆: 3x, TP/SL: True
[模拟] 买入 0.01 BTC
✅ 执行成功
```

#### ❌ **问题流程（如果看到这些）**

**问题 1: LLM 未返回决策**
```
LLM 未使用 Function Calling，强制执行买入
→ 检查 LLM API 是否正常
→ 检查 strategy prompt 是否加载
```

**问题 2: 风险检查失败但没有自动降级**
```
❌ 风险检查失败: XXX
(然后没有看到 "🔧 强制交易模式：自动调整...")
→ 说明自动降级代码未生效
```

**问题 3: 决策是 hold**
```
决策: hold
→ 应该被拦截并转换为 buy
→ 检查是否有 "强制改为 buy" 的日志
```

---

### 常见问题诊断

#### Q1: 运行后完全没有交易

**检查步骤**:

1. **确认配置**:
```bash
cat config/config.testnet.json | grep enable_execution
# 应该显示: "enable_execution": true
```

2. **检查LLM决策**:
```bash
grep "LLM 决策" logs/advanced_trading.log
# 应该看到决策内容
```

3. **检查是否到达执行节点**:
```bash
grep "准备执行" logs/advanced_trading.log
# 应该看到准备执行的日志
```

4. **检查是否有错误**:
```bash
grep "ERROR\|Exception\|Traceback" logs/advanced_trading.log
```

---

#### Q2: LLM 总是返回 hold

**原因**: Function Calling 的 enum 中还包含 hold

**检查**:
```bash
grep -A 5 '"enum"' src/advanced_nodes.py | head -20
# 应该只看到: ["buy", "sell", "close"]
```

**如果还有 hold，修复**:
```python
"enum": ["buy", "sell", "close"]  # 不能有 "hold"
```

---

#### Q3: 风险检查失败导致不交易

**检查**:
```bash
grep "风险检查失败" logs/advanced_trading.log
```

**如果有，检查是否有自动降级**:
```bash
grep "强制交易模式：自动调整" logs/advanced_trading.log
```

**如果没有自动降级日志**:
- 确认你使用的是 `main_advanced.py`（不是 `main.py`）
- 确认代码已更新

---

#### Q4: API 错误

**检查 LLM API**:
```bash
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

**检查 Hyperliquid API**:
```bash
curl https://api.hyperliquid-testnet.xyz/info -X POST \
  -H "Content-Type: application/json" \
  -d '{"type":"metaAndAssetCtxs"}'
```

---

### 强制交易验证清单

运行测试后，确认以下内容：

- [ ] LLM 做出了决策（buy/sell/close）
- [ ] 决策不是 hold（或被拦截转换）
- [ ] 到达了"准备执行"阶段
- [ ] 看到了执行日志（[模拟] 或 [真实]）
- [ ] 没有因为风险检查而中断
- [ ] 如果风险检查失败，有自动降级日志

---

### 调试命令

```bash
# 1. 清理旧日志
rm logs/advanced_trading.log

# 2. 运行单次测试
python main_advanced.py --mode once

# 3. 查看完整日志
cat logs/advanced_trading.log

# 4. 查看关键部分
echo "=== LLM 决策 ==="
grep -A 8 "LLM 决策成功" logs/advanced_trading.log

echo "=== 风险检查 ==="
grep "风险检查" logs/advanced_trading.log

echo "=== 执行情况 ==="
grep "准备执行\|买入\|卖出\|平仓" logs/advanced_trading.log

# 5. 检查是否有错误
echo "=== 错误信息 ==="
grep -i "error\|exception\|fail" logs/advanced_trading.log
```

---

### 如果还是不工作

1. **备份当前代码**:
```bash
cp main_advanced.py main_advanced.py.backup
cp src/advanced_nodes.py src/advanced_nodes.py.backup
```

2. **运行诊断脚本**:
```bash
python test_forced_trading.py > test_result.txt 2>&1
```

3. **查看完整输出**:
```bash
cat test_result.txt
```

4. **提供以下信息**:
   - `test_result.txt` 的内容
   - `logs/advanced_trading.log` 的最后50行
   - 是否看到 "✅ LLM 决策成功"
   - 是否看到 "🎯 准备执行"
   - 是否看到 "[模拟] 买入" 或类似信息

---

### 立即测试命令（复制粘贴运行）

```bash
cd "/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent" && \
rm -f logs/advanced_trading.log && \
echo "🧪 开始测试强制交易模式..." && \
python main_advanced.py --mode once && \
echo "" && \
echo "📊 测试完成，查看结果：" && \
echo "" && \
echo "=== LLM 决策 ===" && \
grep -A 8 "LLM 决策成功" logs/advanced_trading.log && \
echo "" && \
echo "=== 风险检查 ===" && \
grep "风险检查" logs/advanced_trading.log && \
echo "" && \
echo "=== 执行情况 ===" && \
grep "准备执行\|买入\|卖出\|平仓" logs/advanced_trading.log
```

---

**如果执行后看到交易日志，说明强制交易模式已生效！** ✅
