"""
高级交易工具 - 充分利用 Hyperliquid SDK
包括：杠杆管理、止盈止损、历史数据分析等
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange

logger = logging.getLogger(__name__)


class AdvancedTradingTools:
    """高级交易工具类 - 像人类交易员一样操作"""
    
    def __init__(self, info: Info, exchange: Exchange, address: str):
        self.info = info
        self.exchange = exchange
        self.address = address
    
    # ===== 历史数据分析 =====
    
    def get_candles(
        self, 
        coin: str, 
        interval: str = "1h",
        lookback_hours: int = 24
    ) -> List[Dict]:
        """
        获取K线历史数据
        
        Args:
            coin: 币种名称
            interval: K线周期 - "1m", "5m", "15m", "1h", "4h", "1d"
            lookback_hours: 回看小时数
            
        Returns:
            [
                {
                    "time": 1234567890000,  # Unix时间戳(毫秒)
                    "open": 65000.0,
                    "high": 65500.0,
                    "low": 64800.0,
                    "close": 65200.0,
                    "volume": 1234.5
                },
                ...
            ]
        """
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(hours=lookback_hours)).timestamp() * 1000)
            
            candles = self.info.candles_snapshot(
                name=coin,
                interval=interval,
                startTime=start_time,
                endTime=end_time
            )
            
            formatted_candles = []
            for candle in candles:
                formatted_candles.append({
                    "time": candle["t"],
                    "open": float(candle["o"]),
                    "high": float(candle["h"]),
                    "low": float(candle["l"]),
                    "close": float(candle["c"]),
                    "volume": float(candle.get("v", 0))
                })
            
            logger.info(f"获取 {coin} K线数据: {len(formatted_candles)} 根，周期 {interval}")
            return formatted_candles
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []
    
    def get_trading_history(self, limit: int = 50) -> List[Dict]:
        """
        获取交易历史记录
        
        Args:
            limit: 返回最近N条记录
            
        Returns:
            [
                {
                    "time": "2024-01-01 12:00:00",
                    "coin": "BTC",
                    "side": "buy",
                    "size": 0.001,
                    "price": 65000.0,
                    "fee": 0.05
                },
                ...
            ]
        """
        try:
            fills = self.info.user_fills(self.address)
            
            history = []
            for fill in fills[:limit]:
                history.append({
                    "time": datetime.fromtimestamp(fill["time"] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                    "coin": fill["coin"],
                    "side": fill["side"],
                    "size": float(fill["sz"]),
                    "price": float(fill["px"]),
                    "fee": float(fill.get("fee", 0)),
                    "closed_pnl": float(fill.get("closedPnl", 0))
                })
            
            logger.info(f"获取交易历史: {len(history)} 条记录")
            return history
            
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []
    
    def calculate_technical_indicators(self, candles: List[Dict]) -> Dict:
        """
        计算技术指标
        
        Args:
            candles: K线数据
            
        Returns:
            {
                "sma_20": 65000.0,      # 20周期简单移动平均
                "ema_12": 65100.0,      # 12周期指数移动平均
                "rsi_14": 55.5,         # 14周期RSI
                "price_change_24h": 2.5, # 24小时涨跌幅(%)
                "volatility": 0.015      # 波动率
            }
        """
        if not candles or len(candles) < 20:
            return {}
        
        try:
            closes = [c["close"] for c in candles]
            
            # 简单移动平均 SMA
            sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
            
            # 指数移动平均 EMA
            def calculate_ema(prices, period):
                multiplier = 2 / (period + 1)
                ema = prices[0]
                for price in prices[1:]:
                    ema = (price - ema) * multiplier + ema
                return ema
            
            ema_12 = calculate_ema(closes, 12) if len(closes) >= 12 else None
            
            # RSI
            def calculate_rsi(prices, period=14):
                if len(prices) < period + 1:
                    return None
                
                gains = []
                losses = []
                for i in range(1, len(prices)):
                    change = prices[i] - prices[i-1]
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
                
                avg_gain = sum(gains[-period:]) / period
                avg_loss = sum(losses[-period:]) / period
                
                if avg_loss == 0:
                    return 100
                
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                return rsi
            
            rsi_14 = calculate_rsi(closes, 14)
            
            # 24小时涨跌幅
            if len(closes) >= 24:
                price_change_24h = ((closes[-1] - closes[-24]) / closes[-24]) * 100
            else:
                price_change_24h = ((closes[-1] - closes[0]) / closes[0]) * 100
            
            # 波动率（标准差 / 均值）
            import statistics
            volatility = statistics.stdev(closes[-20:]) / statistics.mean(closes[-20:]) if len(closes) >= 20 else 0
            
            indicators = {
                "sma_20": round(sma_20, 2) if sma_20 else None,
                "ema_12": round(ema_12, 2) if ema_12 else None,
                "rsi_14": round(rsi_14, 2) if rsi_14 else None,
                "price_change_24h": round(price_change_24h, 2),
                "volatility": round(volatility, 4),
                "current_price": closes[-1],
                "highest_24h": max(closes[-24:]) if len(closes) >= 24 else max(closes),
                "lowest_24h": min(closes[-24:]) if len(closes) >= 24 else min(closes)
            }
            
            logger.info(f"技术指标计算完成: RSI={rsi_14:.1f}, 涨跌幅={price_change_24h:.2f}%")
            return indicators
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return {}
    
    # ===== 杠杆管理 =====
    
    def adjust_leverage(
        self, 
        coin: str, 
        leverage: int,
        is_cross: bool = True,
        dry_run: bool = True
    ) -> Dict:
        """
        调整杠杆倍数
        
        Args:
            coin: 币种
            leverage: 杠杆倍数 (1-50)
            is_cross: True=全仓, False=逐仓
            dry_run: 是否模拟
            
        Returns:
            执行结果
        """
        mode = "全仓" if is_cross else "逐仓"
        
        if dry_run:
            logger.info(f"[模拟] 调整 {coin} 杠杆: {leverage}x ({mode})")
            return {
                "success": True,
                "dry_run": True,
                "coin": coin,
                "leverage": leverage,
                "mode": mode,
                "message": f"模拟调整杠杆成功"
            }
        
        try:
            logger.warning(f"[真实] 调整 {coin} 杠杆: {leverage}x ({mode})")
            result = self.exchange.update_leverage(leverage, coin, is_cross)
            
            return {
                "success": result.get("status") == "ok",
                "dry_run": False,
                "coin": coin,
                "leverage": leverage,
                "mode": mode,
                "result": result
            }
        except Exception as e:
            logger.error(f"调整杠杆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def adjust_isolated_margin(
        self,
        coin: str,
        amount: float,
        dry_run: bool = True
    ) -> Dict:
        """
        调整逐仓保证金
        
        Args:
            coin: 币种
            amount: 保证金变化量（正数=增加，负数=减少）
            dry_run: 是否模拟
            
        Returns:
            执行结果
        """
        action = "增加" if amount > 0 else "减少"
        
        if dry_run:
            logger.info(f"[模拟] {action} {coin} 保证金: ${abs(amount):.2f}")
            return {
                "success": True,
                "dry_run": True,
                "coin": coin,
                "amount": amount,
                "message": f"模拟{action}保证金成功"
            }
        
        try:
            logger.warning(f"[真实] {action} {coin} 保证金: ${abs(amount):.2f}")
            result = self.exchange.update_isolated_margin(amount, coin)
            
            return {
                "success": result.get("status") == "ok",
                "dry_run": False,
                "coin": coin,
                "amount": amount,
                "result": result
            }
        except Exception as e:
            logger.error(f"调整保证金失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ===== 止盈止损 (TP/SL) =====
    
    def place_order_with_tpsl(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        entry_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        dry_run: bool = True
    ) -> Dict:
        """
        下单并设置止盈止损
        
        Args:
            coin: 币种
            is_buy: True=买入做多, False=卖出做空
            size: 数量
            entry_price: 入场价格（None=市价）
            take_profit_price: 止盈价格
            stop_loss_price: 止损价格
            dry_run: 是否模拟
            
        Returns:
            执行结果
        """
        action = "买入" if is_buy else "卖出"
        
        if dry_run:
            logger.info(f"[模拟] {action} {size} {coin}")
            if take_profit_price:
                logger.info(f"  止盈: ${take_profit_price:.2f}")
            if stop_loss_price:
                logger.info(f"  止损: ${stop_loss_price:.2f}")
            
            return {
                "success": True,
                "dry_run": True,
                "coin": coin,
                "action": action,
                "size": size,
                "tp": take_profit_price,
                "sl": stop_loss_price,
                "message": "模拟下单成功"
            }
        
        try:
            logger.warning(f"[真实] {action} {size} {coin} with TP/SL")
            
            # 1. 开仓
            if entry_price is None:
                # 市价单
                logger.info(f"📤 发送市价单: {action} {size} {coin}")
                order_result = self.exchange.market_open(coin, is_buy, size)
                logger.info(f"📥 交易所响应: {order_result}")
            else:
                # 限价单
                logger.info(f"📤 发送限价单: {action} {size} {coin} @ ${entry_price}")
                order_result = self.exchange.order(
                    coin, is_buy, size, entry_price,
                    {"limit": {"tif": "Gtc"}}
                )
                logger.info(f"📥 交易所响应: {order_result}")
            
            # 检查订单状态（需要同时检查status和data.statuses）
            if order_result.get("status") != "ok":
                logger.error(f"❌ 开仓失败！响应: {order_result}")
                return {
                    "success": False,
                    "error": "开仓失败",
                    "result": order_result,
                    "message": f"交易所拒绝: {order_result}"
                }
            
            # 检查是否有错误信息（即使status=ok）
            statuses = order_result.get("response", {}).get("data", {}).get("statuses", [])
            if statuses and any("error" in s for s in statuses):
                error_msg = statuses[0].get("error", "未知错误")
                logger.error(f"❌ 开仓失败！错误: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "result": order_result,
                    "message": f"交易所错误: {error_msg}"
                }
            
            logger.info(f"✅ 开仓成功！订单响应: {order_result}")
            
            # 2. 设置止盈 (Take Profit)
            tp_result = None
            if take_profit_price:
                tp_order_type = {
                    "trigger": {
                        "triggerPx": take_profit_price,
                        "isMarket": True,
                        "tpsl": "tp"
                    }
                }
                tp_result = self.exchange.order(
                    coin, not is_buy, size, take_profit_price,
                    tp_order_type, reduce_only=True
                )
                logger.info(f"✅ 止盈设置: ${take_profit_price:.2f}")
            
            # 3. 设置止损 (Stop Loss)
            sl_result = None
            if stop_loss_price:
                sl_order_type = {
                    "trigger": {
                        "triggerPx": stop_loss_price,
                        "isMarket": True,
                        "tpsl": "sl"
                    }
                }
                sl_result = self.exchange.order(
                    coin, not is_buy, size, stop_loss_price,
                    sl_order_type, reduce_only=True
                )
                logger.info(f"✅ 止损设置: ${stop_loss_price:.2f}")
            
            return {
                "success": True,
                "dry_run": False,
                "coin": coin,
                "action": action,
                "size": size,
                "entry_result": order_result,
                "tp_result": tp_result,
                "sl_result": sl_result
            }
            
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def calculate_tpsl_prices(
        self,
        current_price: float,
        is_buy: bool,
        take_profit_pct: float = 5.0,
        stop_loss_pct: float = 3.0
    ) -> Tuple[float, float]:
        """
        计算止盈止损价格
        
        Args:
            current_price: 当前价格
            is_buy: 是否做多
            take_profit_pct: 止盈百分比
            stop_loss_pct: 止损百分比
            
        Returns:
            (止盈价格, 止损价格)
        """
        if is_buy:
            # 做多: TP在上方, SL在下方
            tp_price = current_price * (1 + take_profit_pct / 100)
            sl_price = current_price * (1 - stop_loss_pct / 100)
        else:
            # 做空: TP在下方, SL在上方
            tp_price = current_price * (1 - take_profit_pct / 100)
            sl_price = current_price * (1 + stop_loss_pct / 100)
        
        return (round(tp_price, 2), round(sl_price, 2))
    
    # ===== 智能分析 =====
    
    def analyze_market_condition(self, coin: str) -> Dict:
        """
        综合市场分析
        
        Returns:
            {
                "trend": "bullish" | "bearish" | "neutral",
                "strength": 0-100,
                "recommendation": "buy" | "sell" | "hold",
                "reasons": ["原因1", "原因2", ...]
            }
        """
        try:
            # 获取K线数据
            candles = self.get_candles(coin, "1h", 24)
            if not candles:
                return {"trend": "unknown", "recommendation": "hold"}
            
            # 计算技术指标
            indicators = self.calculate_technical_indicators(candles)
            
            reasons = []
            score = 50  # 中性分数
            
            # RSI 分析
            if indicators.get("rsi_14"):
                rsi = indicators["rsi_14"]
                if rsi < 30:
                    score += 15
                    reasons.append(f"RSI超卖({rsi:.1f})")
                elif rsi > 70:
                    score -= 15
                    reasons.append(f"RSI超买({rsi:.1f})")
            
            # 价格趋势分析
            if indicators.get("price_change_24h"):
                change = indicators["price_change_24h"]
                if change > 3:
                    score += 10
                    reasons.append(f"24h上涨{change:.1f}%")
                elif change < -3:
                    score -= 10
                    reasons.append(f"24h下跌{abs(change):.1f}%")
            
            # EMA vs SMA
            if indicators.get("ema_12") and indicators.get("sma_20"):
                if indicators["ema_12"] > indicators["sma_20"]:
                    score += 5
                    reasons.append("短期均线上穿长期均线")
                else:
                    score -= 5
                    reasons.append("短期均线下穿长期均线")
            
            # 判断趋势
            if score > 60:
                trend = "bullish"
                recommendation = "buy"
            elif score < 40:
                trend = "bearish"
                recommendation = "sell"
            else:
                trend = "neutral"
                recommendation = "hold"
            
            return {
                "trend": trend,
                "strength": score,
                "recommendation": recommendation,
                "reasons": reasons,
                "indicators": indicators
            }
            
        except Exception as e:
            logger.error(f"市场分析失败: {e}")
            return {
                "trend": "unknown",
                "recommendation": "hold",
                "error": str(e)
            }
