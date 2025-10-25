# LangGraph 加密货币自动交易 Agent (MVP)

## 📋 项目简介

这是一个基于 LangGraph 框架的加密货币自动交易助手，使用 Hyperliquid SDK 进行交易。
设计理念：**安全第一，循序渐进**

## 🎯 MVP 功能

### 阶段一：市场观察模式（当前）
- ✅ 实时价格监控
- ✅ 账户状态查询
- ✅ LLM 市场分析
- ✅ 交易建议生成（不执行）
- ✅ 风险评估

### 阶段二：模拟交易（未来）
- 虚拟账户回测
- 策略验证

### 阶段三：真实小额交易（未来）
- 严格风控
- 小额试验

## 🏗️ 架构

```
┌─────────────────────────────────────────┐
│         LangGraph State Machine         │
├─────────────────────────────────────────┤
│  fetch_market → get_account → analyze   │
│       ↓              ↓          ↓       │
│  risk_check → execute → log_result      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│       Hyperliquid Python SDK            │
├─────────────────────────────────────────┤
│  Info API  │  Exchange API              │
└─────────────────────────────────────────┘
```

## 📁 项目结构

```
trading_agent/
├── README.md                 # 本文件
├── requirements.txt          # 依赖
├── config/
│   ├── config.json          # API配置（需创建）
│   └── strategy_prompt.txt  # LLM策略提示词
├── src/
│   ├── __init__.py
│   ├── agent.py             # LangGraph Agent主类
│   ├── nodes.py             # 状态机节点
│   ├── tools.py             # Hyperliquid工具函数
│   ├── risk_manager.py      # 风险管理
│   └── state.py             # 状态定义
├── logs/                    # 交易日志
└── main.py                  # 启动入口
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd trading_agent
pip install -r requirements.txt
```

### 2. 配置

复制配置文件模板：
```bash
cp config/config.example.json config/config.json
```

编辑 `config/config.json`：
```json
{
  "hyperliquid": {
    "account_address": "0xYourAddress",
    "secret_key": "your_private_key",
    "base_url": "https://api.hyperliquid-testnet.xyz"
  },
  "llm": {
    "provider": "deepseek",
    "api_key": "your_deepseek_api_key",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat"
  },
  "risk": {
    "max_position_size": 0.1,
    "max_total_exposure": 1000,
    "enable_execution": false
  }
}
```

### 3. 运行（观察模式）

```bash
python main.py --mode observe
```

## ⚠️ 安全提示

1. **先在测试网运行**：使用 `https://api.hyperliquid-testnet.xyz`
2. **观察模式优先**：设置 `enable_execution: false`
3. **小额测试**：真实交易时设置严格的仓位限制
4. **保护私钥**：不要将 `config.json` 提交到 Git

## 📊 使用示例

### 观察模式
```bash
# 每5分钟分析一次市场
python main.py --mode observe --interval 300
```

### 单次分析
```bash
python main.py --mode single --coin BTC
```

## 🔧 开发路线图

- [x] 项目初始化
- [x] 市场数据获取
- [x] LangGraph 状态机
- [x] LLM 决策节点（Function Calling）
- [x] 风险管理系统
- [x] 真实交易支持（测试网）
- [ ] 回测框架
- [ ] Web 监控面板
- [ ] 多策略支持

## 🔴 真实交易（测试网）

### 快速启用

1. **创建配置**：`config/config.testnet.json` 已准备好
2. **填写信息**：测试网地址、私钥、LLM API Key
3. **测试连接**：`python test_connection.py`
4. **启动 Agent**：`python main.py --config config/config.testnet.json`

详细说明请查看 **[REAL_TRADING_GUIDE.md](REAL_TRADING_GUIDE.md)**

### 安全保障

- ✅ Function Calling 结构化决策
- ✅ 多层风险检查
- ✅ 资金使用限制（max_usable_capital）
- ✅ 小额交易强制（单笔 < $50）
- ✅ 测试网环境

### 运行示例

```bash
# 测试配置
python test_connection.py

# 启动真实交易（测试网）
python main.py --config config/config.testnet.json
```

## 📚 学习资源

- [Hyperliquid 文档](https://hyperliquid.gitbook.io/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [加密货币交易基础](待补充)

## 📝 License

MIT
