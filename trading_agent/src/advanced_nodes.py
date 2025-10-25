"""增强的 LangGraph 节点 - 支持高级交易功能"""
import logging
from src.state import TradingState
from src.advanced_tools import AdvancedTradingTools
from src.risk_manager import RiskManager

logger = logging.getLogger(__name__)


def fetch_advanced_market_data_node(
    state: TradingState,
    advanced_tools: AdvancedTradingTools
) -> TradingState:
    """获取增强的市场数据（包括K线和技术指标）"""
    logger.info("📊 获取高级市场数据...")
    print("\n🔍 开始获取市场数据...")
    
    # 获取基础价格数据
    try:
        print("   → 正在获取价格数据...")
        state["current_prices"] = advanced_tools.info.all_mids()
        print(f"   ✅ 成功获取 {len(state['current_prices'])} 个币种价格")
    except Exception as e:
        print(f"   ❌ 获取价格数据失败: {e}")
        logger.error(f"获取价格失败: {e}")
        state["current_prices"] = {}
        return state
    
    # 打印市场概况
    print("\n" + "=" * 70)
    print("📊 市场数据概况")
    print("=" * 70)
    print(f"总币种数: {len(state['current_prices'])}")
    print("\n主要币种价格:")
    for coin in ["BTC", "ETH", "SOL", "AVAX", "MATIC"]:
        if coin in state["current_prices"]:
            try:
                price = float(state["current_prices"][coin])
                print(f"  {coin:8s}: ${price:>12,.2f}")
            except (ValueError, TypeError) as e:
                print(f"  {coin:8s}: {state['current_prices'][coin]}")
    
    # 为主要币种获取技术分析数据
    print("\n   → 开始获取技术指标...")
    market_analysis = {}
    for coin in ["BTC", "ETH"]:
        try:
            print(f"   → 分析 {coin}...")
            
            # 获取K线
            candles = advanced_tools.get_candles(coin, "1h", 24)
            print(f"      ✅ 获取到 {len(candles)} 根K线")
            
            # 计算技术指标
            indicators = advanced_tools.calculate_technical_indicators(candles)
            print(f"      ✅ 技术指标计算完成")
            
            # 市场状况分析
            condition = advanced_tools.analyze_market_condition(coin)
            print(f"      ✅ 市场状况分析完成")
            
            market_analysis[coin] = {
                "candles": candles[-5:],  # 最近5根K线
                "indicators": indicators,
                "condition": condition
            }
            
            # 打印技术指标（注意：键名是 rsi_14, sma_20, ema_12, price_change_24h）
            print(f"\n{coin} 技术指标:")
            print(f"  RSI(14):      {indicators.get('rsi_14', 0):>8.2f}")
            print(f"  SMA(20):      ${indicators.get('sma_20', 0):>12,.2f}")
            print(f"  EMA(12):      ${indicators.get('ema_12', 0):>12,.2f}")
            print(f"  24h 涨跌:     {indicators.get('price_change_24h', 0):>8.2f}%")
            print(f"  波动率:       {indicators.get('volatility', 0):>8.4f}")
            print(f"  趋势:         {condition.get('trend', 'unknown')}")
            print(f"  趋势强度:     {condition.get('strength', 0):>8.2f}")
            
        except Exception as e:
            logger.error(f"分析 {coin} 失败: {e}")
            print(f"\n   ❌ {coin} 技术分析失败: {e}")
            import traceback
            print(f"      详细错误: {traceback.format_exc()}")
    
    state["market_analysis_data"] = market_analysis
    state["messages"].append(f"获取到 {len(state['current_prices'])} 个币种价格和技术分析")
    print("=" * 70 + "\n")
    
    return state


def enhanced_llm_analysis_node(
    state: TradingState,
    llm_client,
    strategy_prompt: str,
    advanced_tools: AdvancedTradingTools
) -> TradingState:
    """增强的 LLM 分析节点 - 包含技术指标和市场分析"""
    logger.info("🤖 LLM 高级分析...")
    
    # 构建详细的市场数据（包含技术指标）
    market_data_str = ""
    for coin, analysis in state.get("market_analysis_data", {}).items():
        indicators = analysis.get("indicators", {})
        condition = analysis.get("condition", {})
        
        market_data_str += f"\n{coin} 分析:\n"
        market_data_str += f"  当前价格: ${indicators.get('current_price', 0):.2f}\n"
        market_data_str += f"  24h涨跌: {indicators.get('price_change_24h', 0):+.2f}%\n"
        market_data_str += f"  RSI(14): {indicators.get('rsi_14', 0):.1f}\n"
        market_data_str += f"  SMA(20): ${indicators.get('sma_20', 0):.2f}\n"
        market_data_str += f"  波动率: {indicators.get('volatility', 0):.2%}\n"
        market_data_str += f"  市场趋势: {condition.get('trend', 'unknown')}\n"
        market_data_str += f"  建议: {condition.get('recommendation', 'hold')}\n"
        market_data_str += f"  原因: {', '.join(condition.get('reasons', []))}\n"
    
    # 获取持仓信息
    positions_str = ""
    for pos in state['positions']:
        positions_str += f"\n  {pos['coin']}: "
        positions_str += f"数量={pos['size']:.4f}, "
        positions_str += f"入场价=${pos['entry_price']:.2f}, "
        positions_str += f"当前价=${pos['current_price']:.2f}, "
        positions_str += f"盈亏=${pos['unrealized_pnl']:+.2f}, "
        positions_str += f"杠杆={pos['leverage']}x"
    
    if not positions_str:
        positions_str = "\n  无持仓"
    
    # 获取交易历史（最近5笔）
    trading_history = advanced_tools.get_trading_history(limit=5)
    history_str = ""
    for trade in trading_history:
        history_str += f"\n  {trade['time']}: {trade['side'].upper()} {trade['size']} {trade['coin']} @ ${trade['price']:.2f}"
    
    if not history_str:
        history_str = "\n  暂无交易历史"
    
    context = f"""
=== 市场技术分析 ===
{market_data_str}

=== 账户状态 ===
账户价值: ${state['account_value']:.2f}
可用余额: ${state['available_balance']:.2f}

=== 当前持仓 ===
{positions_str}

=== 最近交易历史 ===
{history_str}

⚠️ 重要：你必须每次都做出交易决策！
- 禁止选择 hold 或观望
- 必须选择 buy（做多）或 sell（做空）或 close（平仓）
- 即使信号不明确，也要基于技术指标做出方向性选择
- 可以用小仓位 + 低杠杆来降低风险，但不能不交易

请基于以上数据立即做出交易决策。
"""
    
    # 定义增强的 Function Calling 工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "make_advanced_trading_decision",
                "description": "做出高级交易决策，包括杠杆和止盈止损设置",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "enum": ["buy", "sell", "close"],
                            "description": "交易决策：buy=开多仓, sell=开空仓, close=平仓。禁止选择hold，必须每次都交易！"
                        },
                        "coin": {
                            "type": "string",
                            "description": "目标币种"
                        },
                        "size": {
                            "type": "number",
                            "description": "交易数量"
                        },
                        "leverage": {
                            "type": "integer",
                            "description": "杠杆倍数(1-20)，默认1表示不使用杠杆"
                        },
                        "use_tpsl": {
                            "type": "boolean",
                            "description": "是否使用止盈止损"
                        },
                        "take_profit_pct": {
                            "type": "number",
                            "description": "止盈百分比，如5.0表示5%"
                        },
                        "stop_loss_pct": {
                            "type": "number",
                            "description": "止损百分比，如3.0表示3%"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "详细的决策理由"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "决策置信度(0-1)"
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
        
        if message.tool_calls:
            import json
            tool_call = message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            decision = function_args.get("decision", "buy")
            # 强制：如果LLM返回hold，自动转换为buy
            if decision == "hold" or decision == "adjust_position":
                logger.warning(f"LLM试图返回 {decision}，强制改为 buy")
                decision = "buy"
            state["trading_decision"] = decision
            state["target_coin"] = function_args.get("coin", "BTC")
            state["target_size"] = function_args.get("size", 0.0)
            state["target_leverage"] = function_args.get("leverage", 1)
            state["use_tpsl"] = function_args.get("use_tpsl", False)
            state["take_profit_pct"] = function_args.get("take_profit_pct", 5.0)
            state["stop_loss_pct"] = function_args.get("stop_loss_pct", 3.0)
            state["reasoning"] = function_args.get("reasoning", "")
            state["confidence"] = function_args.get("confidence", 0.0)
            state["market_analysis"] = function_args.get("reasoning", "")
            
            # 打印LLM决策
            print("\n" + "=" * 70)
            print("🤖 LLM 交易决策")
            print("=" * 70)
            
            decision_icon = {
                "buy": "📈 买入(做多)",
                "sell": "📉 卖出(做空)",
                "close": "🔄 平仓"
            }.get(state['trading_decision'], state['trading_decision'])
            
            print(f"决策:         {decision_icon}")
            print(f"币种:         {state['target_coin']}")
            print(f"数量:         {state['target_size']}")
            print(f"杠杆:         {state['target_leverage']}x")
            print(f"止盈止损:     {'✅ 是' if state['use_tpsl'] else '❌ 否'}")
            
            if state['use_tpsl']:
                print(f"止盈比例:     {state.get('take_profit_pct', 0):.1f}%")
                print(f"止损比例:     {state.get('stop_loss_pct', 0):.1f}%")
            
            print(f"置信度:       {state['confidence']:.0%}")
            print(f"\n决策理由:")
            # 分行打印理由
            reasoning = state['reasoning']
            if len(reasoning) > 200:
                print(f"  {reasoning[:200]}...")
            else:
                print(f"  {reasoning}")
            
            print("=" * 70 + "\n")
            
            logger.info(f"✅ LLM 决策: {state['trading_decision']} {state['target_size']} {state['target_coin']}")
            
        else:
            # 备用方案：强制买入
            analysis = message.content or ""
            state["market_analysis"] = analysis
            logger.warning("LLM 未使用 Function Calling，强制执行买入")
            
            # 选择第一个币种进行小额买入
            state["trading_decision"] = "buy"
            state["target_coin"] = "BTC"
            state["target_size"] = 0.001
            state["target_leverage"] = 1
            state["use_tpsl"] = True
            state["take_profit_pct"] = 3.0
            state["stop_loss_pct"] = 1.5
            state["reasoning"] = "LLM未正常返回，执行保守买入策略"
            state["confidence"] = 0.3
        
        state["messages"].append("LLM 高级分析完成")
        
    except Exception as e:
        logger.error(f"LLM 分析失败: {e}，强制执行买入")
        # 异常情况：强制小额买入
        state["trading_decision"] = "buy"
        state["target_coin"] = "BTC"
        state["target_size"] = 0.001
        state["target_leverage"] = 1
        state["use_tpsl"] = True
        state["take_profit_pct"] = 2.0
        state["stop_loss_pct"] = 1.0
        state["reasoning"] = f"分析失败，执行最小风险买入：{e}"
        state["confidence"] = 0.2
        state["market_analysis"] = f"分析失败: {e}"
    
    return state


def execute_advanced_trade_node(
    state: TradingState,
    advanced_tools: AdvancedTradingTools,
    dry_run: bool = True
) -> TradingState:
    """执行高级交易（包括杠杆和止盈止损）"""
    logger.info("💰 执行高级交易...")
    
    # 强制交易模式：如果风险检查不通过，自动降级参数后执行
    if not state["risk_passed"]:
        logger.warning(f"⚠️ 风险检查未通过: {state.get('risk_message', '未知原因')}")
        logger.warning("🔧 强制交易模式：自动调整为最小风险参数")
        
        # 自动降级为最小风险交易
        state["target_size"] = 0.001
        state["target_leverage"] = 1
        state["use_tpsl"] = True
        state["take_profit_pct"] = 2.0
        state["stop_loss_pct"] = 1.0
        
        # 如果决策是close，不需要调整
        if state["trading_decision"] != "close":
            logger.info(f"📉 已调整: size=0.001, leverage=1x, TP/SL=2%/1%")
    
    decision = state["trading_decision"]
    coin = state["target_coin"]
    size = state["target_size"]
    leverage = state.get("target_leverage", 1)
    use_tpsl = state.get("use_tpsl", False)
    
    # 调试：打印state中的值
    logger.info(f"📋 State值: use_tpsl={state.get('use_tpsl')}, leverage={state.get('target_leverage')}, size={state.get('target_size')}")
    logger.info(f"🎯 准备执行: {decision} {size} {coin}, 杠杆: {leverage}x, TP/SL: {use_tpsl}")
    
    # 强制交易模式：不再处理hold
    if decision == "hold":
        logger.warning("检测到 hold 决策，强制转换为小额买入")
        decision = "buy"
        size = 0.001
        leverage = 1
        use_tpsl = True
        state["trading_decision"] = decision
        state["target_size"] = size
    
    try:
        # 1. 调整杠杆（如果需要）
        if leverage > 1 and decision in ["buy", "sell"]:
            leverage_result = advanced_tools.adjust_leverage(
                coin, leverage, is_cross=True, dry_run=dry_run
            )
            logger.info(f"杠杆设置: {leverage}x")
        
        # 2. 执行交易
        if decision in ["buy", "sell"]:
            is_buy = (decision == "buy")
            
            # 如果使用止盈止损
            if use_tpsl:
                # 确保价格是浮点数
                current_price = state["current_prices"].get(coin, 0)
                if isinstance(current_price, str):
                    current_price = float(current_price)
                tp_pct = state.get("take_profit_pct", 5.0)
                sl_pct = state.get("stop_loss_pct", 3.0)
                
                tp_price, sl_price = advanced_tools.calculate_tpsl_prices(
                    current_price, is_buy, tp_pct, sl_pct
                )
                
                result = advanced_tools.place_order_with_tpsl(
                    coin=coin,
                    is_buy=is_buy,
                    size=size,
                    take_profit_price=tp_price,
                    stop_loss_price=sl_price,
                    dry_run=dry_run
                )
            else:
                # 普通市价单（无止盈止损）
                action = "买入" if is_buy else "卖出"
                if dry_run:
                    logger.info(f"[模拟] {action} {size} {coin}")
                    result = {
                        "success": True,
                        "dry_run": True,
                        "message": f"模拟{action}成功"
                    }
                else:
                    logger.warning(f"[真实] {action} {size} {coin} (无止盈止损)")
                    logger.info(f"📤 发送市价单: {action} {size} {coin}")
                    
                    order_result = advanced_tools.exchange.market_open(coin, is_buy, size, None, 0.05)
                    logger.info(f"📥 交易所响应: {order_result}")
                    
                    # 检查订单状态
                    if order_result.get("status") != "ok":
                        logger.error(f"❌ 订单失败！响应: {order_result}")
                        result = {
                            "success": False,
                            "result": order_result,
                            "error": f"交易所拒绝: {order_result}"
                        }
                    else:
                        # 检查是否有错误信息（即使status=ok）
                        statuses = order_result.get("response", {}).get("data", {}).get("statuses", [])
                        if statuses and any("error" in s for s in statuses):
                            error_msg = statuses[0].get("error", "未知错误")
                            logger.error(f"❌ 订单失败！错误: {error_msg}")
                            result = {
                                "success": False,
                                "result": order_result,
                                "error": error_msg,
                                "message": f"交易所错误: {error_msg}"
                            }
                        else:
                            logger.info(f"✅ 订单成功！")
                            result = {
                                "success": True,
                                "result": order_result
                            }
            
            state["execution_result"] = result
            
        elif decision == "close":
            # 平仓
            if dry_run:
                logger.info(f"[模拟] 平仓 {coin}")
                result = {"success": True, "dry_run": True, "message": "模拟平仓成功"}
            else:
                logger.warning(f"[真实] 平仓 {coin}")
                result = advanced_tools.exchange.market_close(coin)
                result = {
                    "success": result.get("status") == "ok",
                    "result": result
                }
            
            state["execution_result"] = result
        
        state["success"] = state["execution_result"].get("success", False)
        
        # 打印执行结果
        print("\n" + "=" * 70)
        print("💰 交易执行结果")
        print("=" * 70)
        
        if state["success"]:
            print("状态:         ✅ 成功")
            print(f"操作:         {decision}")
            print(f"币种:         {coin}")
            print(f"数量:         {size}")
            if leverage > 1:
                print(f"杠杆:         {leverage}x")
            if use_tpsl:
                print(f"止盈止损:     已设置")
            if dry_run:
                print(f"模式:         🧪 模拟交易")
            else:
                print(f"模式:         🔴 真实交易")
                
                # 真实交易后，等待并验证持仓
                if decision in ["buy", "sell"]:
                    print("\n📋 验证交易结果...")
                    import time
                    time.sleep(2)  # 等待2秒让订单处理
                    
                    try:
                        user_state = advanced_tools.info.user_state(advanced_tools.address)
                        positions = []
                        for pos in user_state.get("assetPositions", []):
                            if float(pos["position"]["szi"]) != 0:
                                positions.append({
                                    "coin": pos["position"]["coin"],
                                    "size": float(pos["position"]["szi"])
                                })
                        
                        coin_position = next((p for p in positions if p["coin"] == coin), None)
                        if coin_position:
                            print(f"   ✅ 确认持仓: {coin} {abs(coin_position['size']):.4f}")
                            print(f"   方向: {'做多' if coin_position['size'] > 0 else '做空'}")
                        else:
                            print(f"   ⚠️  警告: 未找到 {coin} 持仓")
                            print(f"   当前持仓数: {len(positions)}")
                            if positions:
                                print(f"   持仓列表: {[p['coin'] for p in positions]}")
                    except Exception as e:
                        print(f"   ❌ 验证失败: {e}")
        else:
            print("状态:         ❌ 失败")
            error_msg = state['execution_result'].get('message', state['execution_result'].get('error', '未知错误'))
            print(f"错误:         {error_msg}")
            
            # 如果有详细结果，打印
            if 'result' in state['execution_result']:
                print(f"详细响应:     {state['execution_result']['result']}")
        
        print("=" * 70 + "\n")
        
    except Exception as e:
        logger.error(f"执行交易失败: {e}")
        state["execution_result"] = {"success": False, "error": str(e)}
        state["success"] = False
        
        # 打印错误
        print("\n" + "=" * 70)
        print("💰 交易执行结果")
        print("=" * 70)
        print("状态:         ❌ 异常")
        print(f"错误:         {e}")
        print("=" * 70 + "\n")
    
    return state
