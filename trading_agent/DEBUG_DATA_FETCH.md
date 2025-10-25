# 🔍 数据获取调试指南

## 问题：没有打印出市场数据

### 快速诊断步骤

#### 1️⃣ 运行独立测试脚本

这个脚本会单独测试数据获取功能，不涉及LLM和复杂流程：

```bash
cd "/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent"

# 运行测试
python test_data_fetch.py
```

**预期输出**：
```
======================================================================
🔍 测试数据获取功能
======================================================================

1️⃣ 加载配置...
   ✅ 配置加载成功

2️⃣ 初始化 Hyperliquid SDK...
   ✅ 初始化成功
   账户地址: 0xf4FECF31D8F576A30ECC31D5d32D16cf46e2b8f4

3️⃣ 测试获取价格数据...
   → 调用 info.all_mids()...
   ✅ 成功获取 145 个币种价格

   主要币种价格:
      BTC: $112,586.50
      ETH: $4,234.18
      SOL: $198.45

4️⃣ 测试获取账户状态...
   → 调用 info.user_state()...
   ✅ 账户价值: $999.00
   
   ...
```

---

#### 2️⃣ 查看检查点输出

运行主程序时，现在会显示详细的检查点：

```bash
python main_advanced.py --mode once
```

**关键检查点**：

1. **初始化阶段**：
```
🔧 初始化组件...
   ✅ Hyperliquid 初始化完成 (地址: 0xf4FECF3...)
   ✅ LLM 客户端初始化完成
   ✅ 高级交易工具创建完成
   ✅ 风险管理器创建完成
```

2. **数据获取阶段**：
```
🔍 开始获取市场数据...
   → 正在获取价格数据...
   ✅ 成功获取 145 个币种价格
   → 开始获取技术指标...
   → 分析 BTC...
      ✅ 获取到 24 根K线
      ✅ 技术指标计算完成
      ✅ 市场状况分析完成
```

3. **账户状态阶段**：
```
🔍 开始获取账户状态...
   → 正在获取账户信息...
   ✅ 账户信息获取成功
   → 正在获取持仓信息...
   ✅ 持仓信息获取成功 (共 0 个)
```

---

### 可能的问题和解决方案

#### ❌ 问题 1：没有看到任何检查点输出

**原因**：程序可能在初始化阶段就失败了

**检查**：
```bash
# 查看完整错误
python main_advanced.py --mode once 2>&1 | tee output.log
cat output.log
```

**可能的错误**：
- API key 无效
- 网络连接问题
- 配置文件错误

---

#### ❌ 问题 2：初始化成功，但获取数据失败

**症状**：
```
🔍 开始获取市场数据...
   → 正在获取价格数据...
   ❌ 获取价格数据失败: XXX
```

**可能原因**：
1. **网络问题**：无法连接到 Hyperliquid API
2. **API限制**：请求频率过高
3. **账户问题**：账户地址无效

**解决**：
```bash
# 测试 API 连接
curl https://api.hyperliquid-testnet.xyz/info -X POST \
  -H "Content-Type: application/json" \
  -d '{"type":"metaAndAssetCtxs"}'

# 如果返回数据，说明 API 正常
```

---

#### ❌ 问题 3：数据获取成功，但没有打印市场数据表格

**症状**：
```
🔍 开始获取市场数据...
   ✅ 成功获取 145 个币种价格

(但没有看到下面的市场数据表格)
```

**可能原因**：代码在打印之前就出错了

**检查**：
```bash
# 查看详细日志
cat logs/advanced_trading.log | grep -A 20 "获取市场数据"
```

**调试**：在 `src/advanced_nodes.py` 中查找打印语句

---

#### ❌ 问题 4：打印输出被重定向或缓冲

**症状**：运行时没有输出，但日志文件有内容

**解决**：
```bash
# 强制刷新输出
python -u main_advanced.py --mode once

# 或者实时查看日志
tail -f logs/advanced_trading.log
```

---

### 详细调试步骤

#### Step 1: 验证配置

```bash
# 检查配置文件
cat config/config.testnet.json

# 确认以下内容：
# - secret_key 存在且非空
# - base_url 正确
# - api_key (LLM) 存在
```

#### Step 2: 测试网络连接

```bash
# 测试 Hyperliquid API
curl https://api.hyperliquid-testnet.xyz/info -X POST \
  -H "Content-Type: application/json" \
  -d '{"type":"metaAndAssetCtxs"}'

# 测试 DeepSeek API
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

#### Step 3: 逐步测试

```python
# 1. 测试最基础的功能
python test_data_fetch.py

# 2. 如果通过，运行主程序一次
python main_advanced.py --mode once

# 3. 查看完整输出
python main_advanced.py --mode once 2>&1 | tee full_output.txt
```

#### Step 4: 检查代码修改

```bash
# 确认检查代码已添加
grep -n "开始获取市场数据" src/advanced_nodes.py
grep -n "开始获取账户状态" src/nodes.py

# 应该能找到打印语句
```

---

### 预期的完整输出流程

```
# 启动
🚀 高频交易 Agent 启动 - 激进模式
================================================================================

# 初始化
🔧 初始化组件...
   ✅ Hyperliquid 初始化完成
   ✅ LLM 客户端初始化完成
   ✅ 高级交易工具创建完成
   ✅ 风险管理器创建完成

# 资金信息
💰 账户余额: $999.00 USDC
💵 可用资金: $999.00 USDC (100.0%)
...

# 开始交易周期
============================================================
🚀 开始新的高级交易周期
============================================================

# 获取市场数据
🔍 开始获取市场数据...
   → 正在获取价格数据...
   ✅ 成功获取 145 个币种价格

======================================================================
📊 市场数据概况
======================================================================
总币种数: 145

主要币种价格:
  BTC     :  $   112,586.50
  ETH     :  $     4,234.18
  ...

BTC 技术指标:
  RSI(14):         48.25
  ...
======================================================================

# 获取账户状态
🔍 开始获取账户状态...
   → 正在获取账户信息...
   ✅ 账户信息获取成功
   → 正在获取持仓信息...
   ✅ 持仓信息获取成功 (共 0 个)

======================================================================
💼 账户状态
======================================================================
账户总价值:   $       999.00 USDC
...
======================================================================

# LLM 分析和决策
...

# 执行结果
...
```

---

### 终极调试命令

复制粘贴运行这个一键诊断：

```bash
#!/bin/bash
cd "/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent"

echo "🔍 开始完整诊断..."
echo ""

# 1. 检查文件
echo "1️⃣ 检查关键文件..."
ls -lh config/config.testnet.json src/advanced_nodes.py src/nodes.py main_advanced.py
echo ""

# 2. 检查配置
echo "2️⃣ 检查配置..."
echo "API Key: $(grep 'secret_key' config/config.testnet.json | cut -c1-50)..."
echo ""

# 3. 运行独立测试
echo "3️⃣ 运行独立数据获取测试..."
python test_data_fetch.py
echo ""

# 4. 运行主程序（单次）
echo "4️⃣ 运行主程序（单次）..."
python main_advanced.py --mode once 2>&1 | head -100
echo ""

echo "✅ 诊断完成"
echo ""
echo "如果独立测试成功但主程序失败，请检查:"
echo "1. src/advanced_nodes.py 是否有 print 语句"
echo "2. src/nodes.py 是否有 print 语句"
echo "3. 查看 logs/advanced_trading.log 的完整日志"
```

保存为 `full_diagnose.sh`，然后：

```bash
chmod +x full_diagnose.sh
./full_diagnose.sh
```

---

### 获取帮助

如果以上步骤都无法解决，请提供：

1. `test_data_fetch.py` 的输出
2. `main_advanced.py --mode once` 的前100行输出
3. `logs/advanced_trading.log` 的最后100行
4. 任何错误信息截图

---

**提示**：最常见的问题是网络连接或 API key 配置错误。先运行 `test_data_fetch.py` 来排除这些基础问题。
