"""
多资产组合管理节点
支持同时管理多个持仓和执行多个交易
"""
import logging
import json
from typing import Dict, List
from src.state import TradingState
from src.advanced_tools import AdvancedTradingTools

logger = logging.getLogger(__name__)


def enhanced_portfolio_analysis_node(
    state: TradingState,
    llm_client,
    strategy_prompt: str,
    advanced_tools: AdvancedTradingTools
) -> TradingState:
    """
    增强的组合分析节点 - 支持多资产决策
    """
    logger.info("🤖 组合分析...")
    
    # 构建市场数据
    market_data_str = ""
    for coin, data in state.get("market_analysis", {}).items():
        indicators = data.get("indicators", {})
        condition = data.get("condition", {})
        
        market_data_str += f"\n{coin}:\n"
        market_data_str += f"  价格: ${indicators.get('current_price', 0):.2f}\n"
        market_data_str += f"  RSI(14): {indicators.get('rsi_14', 0):.2f}\n"
        market_data_str += f"  24h涨跌: {indicators.get('price_change_24h', 0):+.2f}%\n"
        market_data_str += f"  趋势: {condition.get('trend', 'unknown')}\n"
    
    # 构建持仓信息
    positions_str = ""
    total_position_value = 0
    for pos in state['positions']:
        pos_value = abs(pos['size'] * pos['current_price'])
        total_position_value += pos_value
        positions_str += f"\n  {pos['coin']}: "
        positions_str += f"{'多' if pos['size'] > 0 else '空'} {abs(pos['size']):.4f}, "
        positions_str += f"价值${pos_value:.2f}, "
        positions_str += f"盈亏${pos['unrealized_pnl']:+.2f}, "
        positions_str += f"杠杆{pos['leverage']}x"
    
    if not positions_str:
        positions_str = "\n  无持仓"
    
    # 计算可用资金
    available_for_new_positions = state['available_balance']
    
    context = f"""
=== 市场数据 ===
{market_data_str}

=== 账户状态 ===
总价值: ${state['account_value']:.2f}
可用余额: ${state['available_balance']:.2f}
持仓总数: {len(state['positions'])}
持仓总价值: ${total_position_value:.2f}
可用于新仓: ${available_for_new_positions:.2f}

=== 当前持仓 ===
{positions_str}

作为多资产组合管理者，请分析当前情况并做出2-4个交易决策：
1. 检查现有持仓是否需要调整（止盈/止损/加仓）
2. 扫描市场寻找新机会
3. 考虑资金分散和风险对冲
4. 返回具体的交易列表

记住：你是自由的交易专家，可以交易任何币种，同时管理多个持仓。
"""
    
    # 定义多交易决策工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "make_portfolio_decisions",
                "description": "做出多个交易决策，管理投资组合",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trades": {
                            "type": "array",
                            "description": "交易列表（1-4个交易决策）",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "decision": {
                                        "type": "string",
                                        "enum": ["buy", "sell", "close"],
                                        "description": "交易类型"
                                    },
                                    "coin": {
                                        "type": "string",
                                        "description": "币种代码"
                                    },
                                    "size": {
                                        "type": "number",
                                        "description": "交易数量"
                                    },
                                    "leverage": {
                                        "type": "integer",
                                        "description": "杠杆倍数(1-10)"
                                    },
                                    "use_tpsl": {
                                        "type": "boolean",
                                        "description": "是否使用止盈止损"
                                    },
                                    "take_profit_pct": {
                                        "type": "number",
                                        "description": "止盈百分比"
                                    },
                                    "stop_loss_pct": {
                                        "type": "number",
                                        "description": "止损百分比"
                                    },
                                    "reasoning": {
                                        "type": "string",
                                        "description": "交易理由"
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "description": "置信度(0-1)"
                                    }
                                },
                                "required": ["decision", "coin", "reasoning", "confidence"]
                            },
                            "minItems": 1,
                            "maxItems": 4
                        },
                        "portfolio_analysis": {
                            "type": "string",
                            "description": "整体组合分析和策略说明"
                        }
                    },
                    "required": ["trades", "portfolio_analysis"]
                }
            }
        }
    ]
    
    try:
        # 调用LLM（使用OpenAI接口）
        messages = [
            {"role": "system", "content": strategy_prompt},
            {"role": "user", "content": context}
        ]
        
        response = llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "make_portfolio_decisions"}}
        )
        
        # 解析响应
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            trades = function_args.get("trades", [])
            portfolio_analysis = function_args.get("portfolio_analysis", "")
            
            # 存储所有交易决策
            state["portfolio_trades"] = trades
            state["portfolio_analysis"] = portfolio_analysis
            
            # 调试：确认设置成功
            logger.info(f"🔍 已设置 portfolio_trades: {len(trades)} 个交易")
            logger.info(f"🔍 State keys after setting: {list(state.keys())}")
            
            # 打印组合分析
            print("\n" + "=" * 70)
            print("🎯 投资组合决策")
            print("=" * 70)
            print(f"\n📊 组合分析：\n{portfolio_analysis}\n")
            print(f"📋 计划执行 {len(trades)} 个交易：\n")
            
            for i, trade in enumerate(trades, 1):
                decision_icon = {"buy": "📈 买入", "sell": "📉 卖出", "close": "❌ 平仓"}
                print(f"{i}. {decision_icon.get(trade['decision'], trade['decision'])}")
                print(f"   币种: {trade['coin']}")
                if trade['decision'] != 'close':
                    print(f"   数量: {trade.get('size', 0)}")
                    print(f"   杠杆: {trade.get('leverage', 1)}x")
                    if trade.get('use_tpsl'):
                        print(f"   止盈: {trade.get('take_profit_pct', 0)}% / 止损: {trade.get('stop_loss_pct', 0)}%")
                print(f"   理由: {trade['reasoning']}")
                print(f"   置信度: {trade['confidence']*100:.0f}%")
                print()
            
            print("=" * 70 + "\n")
            
            logger.info(f"✅ 组合决策完成：{len(trades)} 个交易")
            
        else:
            # 备用方案
            logger.warning("LLM未使用Function Calling，创建保守组合")
            state["portfolio_trades"] = [
                {
                    "decision": "buy",
                    "coin": "ETH",
                    "size": 0.03,
                    "leverage": 1,
                    "use_tpsl": True,
                    "take_profit_pct": 3.0,
                    "stop_loss_pct": 1.5,
                    "reasoning": "默认保守策略：ETH低杠杆持仓",
                    "confidence": 0.5
                }
            ]
            state["portfolio_analysis"] = "LLM未正常响应，使用默认保守策略"
    
    except Exception as e:
        logger.error(f"组合分析失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 失败时返回空列表
        state["portfolio_trades"] = []
        state["portfolio_analysis"] = f"分析失败：{e}"
    
    return state


def execute_portfolio_trades_node(
    state: TradingState,
    advanced_tools: AdvancedTradingTools,
    dry_run: bool = True
) -> TradingState:
    """
    执行多个交易决策
    """
    logger.info("💰 执行组合交易...")
    
    # 调试：打印state的所有键
    logger.info(f"🔍 State 包含的键: {list(state.keys())}")
    logger.info(f"🔍 portfolio_trades 值: {state.get('portfolio_trades', '未找到')}")
    
    trades = state.get("portfolio_trades", [])
    if not trades:
        logger.warning(f"没有交易需要执行（trades长度: {len(trades)}）")
        state["execution_results"] = []
        return state
    
    results = []
    
    print("\n" + "=" * 70)
    print("🔄 开始执行组合交易")
    print("=" * 70)
    
    for i, trade in enumerate(trades, 1):
        decision = trade["decision"]
        coin = trade["coin"]
        
        print(f"\n[{i}/{len(trades)}] 执行: {decision.upper()} {coin}")
        
        try:
            if decision == "close":
                # 平仓
                if dry_run:
                    result = {"success": True, "dry_run": True, "coin": coin, "action": "close"}
                    logger.info(f"[模拟] 平仓 {coin}")
                else:
                    logger.warning(f"[真实] 平仓 {coin}")
                    # 实际平仓逻辑
                    close_result = advanced_tools.exchange.market_close(coin)
                    result = {
                        "success": close_result.get("status") == "ok",
                        "coin": coin,
                        "action": "close",
                        "result": close_result
                    }
            
            elif decision in ["buy", "sell"]:
                # 开仓
                size = trade.get("size", 0.001)
                leverage = trade.get("leverage", 1)
                use_tpsl = trade.get("use_tpsl", False)
                is_buy = (decision == "buy")
                
                # 设置杠杆
                if leverage > 1 and not dry_run:
                    advanced_tools.adjust_leverage(coin, leverage, is_cross=True, dry_run=dry_run)
                
                if use_tpsl:
                    # 带止盈止损
                    current_price = state["current_prices"].get(coin, 0)
                    if isinstance(current_price, str):
                        current_price = float(current_price)
                    
                    tp_pct = trade.get("take_profit_pct", 3.0)
                    sl_pct = trade.get("stop_loss_pct", 1.5)
                    
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
                    # 普通市价单
                    if dry_run:
                        result = {"success": True, "dry_run": True, "coin": coin, "action": decision}
                    else:
                        order_result = advanced_tools.exchange.market_open(coin, is_buy, size, None, 0.05)
                        
                        # 检查错误
                        statuses = order_result.get("response", {}).get("data", {}).get("statuses", [])
                        if statuses and any("error" in s for s in statuses):
                            error_msg = statuses[0].get("error", "未知错误")
                            result = {
                                "success": False,
                                "coin": coin,
                                "action": decision,
                                "error": error_msg
                            }
                        else:
                            result = {
                                "success": True,
                                "coin": coin,
                                "action": decision,
                                "result": order_result
                            }
            
            # 打印结果
            if result.get("success"):
                print(f"   ✅ 成功")
            else:
                print(f"   ❌ 失败: {result.get('error', '未知错误')}")
            
            results.append({
                "trade": trade,
                "result": result
            })
            
        except Exception as e:
            logger.error(f"执行 {coin} {decision} 失败: {e}")
            print(f"   ❌ 异常: {e}")
            results.append({
                "trade": trade,
                "result": {"success": False, "error": str(e)}
            })
    
    print("\n" + "=" * 70)
    print("📊 执行汇总")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r["result"].get("success"))
    print(f"成功: {success_count}/{len(results)}")
    print(f"失败: {len(results) - success_count}/{len(results)}")
    print("=" * 70 + "\n")
    
    state["execution_results"] = results
    state["success"] = all(r["result"].get("success") for r in results)
    
    logger.info(f"组合交易完成：{success_count}/{len(results)} 成功")
    
    return state
