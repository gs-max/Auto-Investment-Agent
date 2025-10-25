"""LangGraph 节点实现"""
import logging
from datetime import datetime
from src.state import TradingState
from src.tools import HyperliquidTools
from src.risk_manager import RiskManager

logger = logging.getLogger(__name__)


def fetch_market_data_node(state: TradingState, tools: HyperliquidTools) -> TradingState:
    """获取市场数据"""
    logger.info("📊 获取市场数据...")
    
    state["current_prices"] = tools.get_all_prices()
    state["timestamp"] = datetime.now().isoformat()
    state["messages"].append(f"获取到 {len(state['current_prices'])} 个币种价格")
    
    return state


def get_account_status_node(state: TradingState, tools) -> TradingState:
    """获取账户状态 - 兼容 HyperliquidTools 和 AdvancedTradingTools"""
    logger.info("💼 获取账户状态...")
    print("\n🔍 开始获取账户状态...")
    
    try:
        print("   → 正在获取账户信息...")
        
        # 检查是否是 AdvancedTradingTools
        if hasattr(tools, 'info') and hasattr(tools, 'address'):
            # 使用 AdvancedTradingTools
            user_state = tools.info.user_state(tools.address)
            account_value = float(user_state["marginSummary"]["accountValue"])
            # 计算可用余额（总价值减去仓位价值）
            total_ntl_pos = float(user_state["marginSummary"]["totalNtlPos"])
            available_balance = account_value - abs(total_ntl_pos)
            
            account = {
                "account_value": account_value,
                "available_balance": max(available_balance, 0)
            }
            
            # 获取持仓
            positions = []
            for pos in user_state.get("assetPositions", []):
                if float(pos["position"]["szi"]) != 0:
                    positions.append({
                        "coin": pos["position"]["coin"],
                        "size": float(pos["position"]["szi"]),
                        "entry_price": float(pos["position"]["entryPx"]),
                        "current_price": float(pos["position"]["positionValue"]) / abs(float(pos["position"]["szi"])) if float(pos["position"]["szi"]) != 0 else 0,
                        "unrealized_pnl": float(pos["position"]["unrealizedPnl"]),
                        "leverage": float(pos["position"]["leverage"]["value"]) if "leverage" in pos["position"] else 1
                    })
            state["positions"] = positions
        else:
            # 使用 HyperliquidTools
            account = tools.get_account_state()
            state["positions"] = tools.get_positions()
        
        print(f"   ✅ 账户信息获取成功")
        
        state["account_value"] = account["account_value"]
        state["available_balance"] = account["available_balance"]
        
        print(f"   ✅ 持仓信息获取成功 (共 {len(state['positions'])} 个)")
        
        state["messages"].append(f"账户价值: ${account['account_value']:.2f}")
    except Exception as e:
        print(f"   ❌ 获取账户状态失败: {e}")
        logger.error(f"获取账户状态失败: {e}")
        import traceback
        print(f"      详细错误: {traceback.format_exc()}")
        state["account_value"] = 0
        state["available_balance"] = 0
        state["positions"] = []
        return state
    
    # 打印账户状态
    print("\n" + "=" * 70)
    print("💼 账户状态")
    print("=" * 70)
    print(f"账户总价值:   ${account['account_value']:>12,.2f} USDC")
    print(f"可用余额:     ${account['available_balance']:>12,.2f} USDC")
    print(f"已用余额:     ${account['account_value'] - account['available_balance']:>12,.2f} USDC")
    
    # 打印持仓
    if state["positions"]:
        print(f"\n当前持仓: {len(state['positions'])} 个")
        print("-" * 70)
        for pos in state["positions"]:
            pnl_symbol = "📈" if pos['unrealized_pnl'] >= 0 else "📉"
            print(f"{pnl_symbol} {pos['coin']:8s}:")
            print(f"   数量:         {pos['size']:>12,.4f}")
            print(f"   入场价:       ${pos['entry_price']:>12,.2f}")
            print(f"   当前价:       ${pos.get('current_price', 0):>12,.2f}")
            print(f"   未实现盈亏:   ${pos['unrealized_pnl']:>12,.2f}")
            if 'leverage' in pos:
                print(f"   杠杆:         {pos['leverage']:>12.0f}x")
            print()
    else:
        print("\n当前持仓: 无")
    
    print("=" * 70 + "\n")
    
    return state


def llm_analysis_node(state: TradingState, llm_client, strategy_prompt: str) -> TradingState:
    """LLM 分析决策"""
    logger.info("🤖 LLM 分析市场...")
    
    # 构建详细的市场数据
    prices_str = "\n".join([f"  {coin}: ${price:.2f}" for coin, price in state['current_prices'].items()])
    positions_str = "\n".join([
        f"  {pos['coin']}: 数量={pos['size']:.4f}, 入场价=${pos['entry_price']:.2f}, 盈亏=${pos['unrealized_pnl']:.2f}"
        for pos in state['positions']
    ]) if state['positions'] else "  无持仓"
    
    context = f"""
当前市场价格:
{prices_str}

账户价值: ${state['account_value']:.2f}

当前持仓:
{positions_str}

请分析市场并给出交易决策。
"""
    
    # 定义 Function Calling 工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "make_trading_decision",
                "description": "根据市场分析做出交易决策",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "enum": ["buy", "sell", "hold", "close"],
                            "description": "交易决策：buy=买入, sell=卖出, hold=持有, close=平仓"
                        },
                        "coin": {
                            "type": "string",
                            "description": "目标币种，如 BTC 或 ETH"
                        },
                        "size": {
                            "type": "number",
                            "description": "交易数量"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "决策理由，详细解释为什么做出这个决策"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "决策置信度，0-1之间的数值"
                        }
                    },
                    "required": ["decision", "reasoning", "confidence"]
                }
            }
        }
    ]
    
    messages = [
        {"role": "system", "content": strategy_prompt},
        {"role": "user", "content": context}
    ]
    
    try:
        response = llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.3
        )
        
        message = response.choices[0].message
        
        # 检查是否有 tool_calls
        if message.tool_calls:
            import json
            tool_call = message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            state["trading_decision"] = function_args.get("decision", "hold")
            state["target_coin"] = function_args.get("coin", "BTC")
            state["target_size"] = function_args.get("size", 0.0)
            state["reasoning"] = function_args.get("reasoning", "")
            state["confidence"] = function_args.get("confidence", 0.0)
            state["market_analysis"] = function_args.get("reasoning", "")
            
            logger.info(f"决策: {state['trading_decision']}, 币种: {state['target_coin']}, 数量: {state['target_size']}")
            
        else:
            # 备用方案：如果没有使用 tool_calls，解析文本内容
            analysis = message.content or ""
            state["market_analysis"] = analysis
            
            # 简单文本解析（备用）
            if "买入" in analysis or "BUY" in analysis.upper():
                state["trading_decision"] = "buy"
                state["target_coin"] = "BTC" if "BTC" in analysis else "ETH"
                state["target_size"] = 0.001  # 默认小数量
            elif "卖出" in analysis or "SELL" in analysis.upper():
                state["trading_decision"] = "sell"
                state["target_coin"] = "BTC" if "BTC" in analysis else "ETH"
                state["target_size"] = 0.001
            else:
                state["trading_decision"] = "hold"
                state["target_coin"] = ""
                state["target_size"] = 0.0
            
            state["reasoning"] = analysis
            state["confidence"] = 0.5
            
            logger.warning("LLM 未使用 Function Calling，使用备用文本解析")
        
        state["messages"].append("LLM 分析完成")
            
    except Exception as e:
        logger.error(f"LLM 分析失败: {e}")
        state["trading_decision"] = "hold"
        state["target_coin"] = ""
        state["target_size"] = 0.0
        state["market_analysis"] = f"分析失败: {e}"
        state["reasoning"] = f"错误: {e}"
        state["confidence"] = 0.0
    
    return state


def risk_check_node(state: TradingState, risk_manager: RiskManager) -> TradingState:
    """风险检查"""
    logger.info("⚠️  风险检查...")
    
    # 确保价格是浮点数
    current_price = state["current_prices"].get(state["target_coin"], 0)
    if isinstance(current_price, str):
        current_price = float(current_price)
    
    result = risk_manager.check_trading_decision(
        decision=state["trading_decision"],
        coin=state["target_coin"],
        size=state["target_size"],
        account_value=state["account_value"],
        positions=state["positions"],
        current_price=current_price
    )
    
    state["risk_assessment"] = result
    state["risk_passed"] = result["passed"]
    state["risk_message"] = result["message"]
    
    if result["passed"]:
        logger.info(f"✅ 风险检查通过: {result['message']}")
    else:
        logger.warning(f"❌ 风险检查失败: {result.get('blocked_reason', '未知原因')}")
        logger.warning(f"   决策: {state['trading_decision']}, 币种: {state['target_coin']}, 数量: {state['target_size']}")
    
    return state


def execute_trade_node(state: TradingState, tools: HyperliquidTools, dry_run: bool = True) -> TradingState:
    """执行交易"""
    logger.info("💰 执行交易...")
    
    if not state["risk_passed"]:
        state["execution_result"] = {"success": False, "message": "未通过风险检查"}
        return state
    
    decision = state["trading_decision"]
    
    if decision == "hold":
        state["execution_result"] = {"success": True, "message": "持有，无需操作"}
    elif decision == "buy":
        state["execution_result"] = tools.place_market_order(
            state["target_coin"], True, state["target_size"], dry_run=dry_run
        )
    elif decision == "sell":
        state["execution_result"] = tools.place_market_order(
            state["target_coin"], False, state["target_size"], dry_run=dry_run
        )
    elif decision == "close":
        state["execution_result"] = tools.close_position(state["target_coin"], dry_run=dry_run)
    
    state["success"] = state["execution_result"].get("success", False)
    return state
