"""
Hyperliquid SDK 工具函数封装
提供简单易用的接口给 LangGraph Agent
"""
import logging
from typing import Dict, List, Optional
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange

logger = logging.getLogger(__name__)


class HyperliquidTools:
    """Hyperliquid 交易工具类"""
    
    def __init__(self, info: Info, exchange: Exchange, address: str):
        """
        初始化工具类
        
        Args:
            info: Hyperliquid Info API 实例
            exchange: Hyperliquid Exchange API 实例
            address: 账户地址
        """
        self.info = info
        self.exchange = exchange
        self.address = address
    
    # ===== 市场数据获取 =====
    
    def get_all_prices(self) -> Dict[str, float]:
        """
        获取所有币种的当前价格
        
        Returns:
            {"BTC": 50000.0, "ETH": 3000.0, ...}
        """
        try:
            mids = self.info.all_mids()
            return {coin: float(price) for coin, price in mids.items()}
        except Exception as e:
            logger.error(f"获取价格失败: {e}")
            return {}
    
    def get_price(self, coin: str) -> Optional[float]:
        """
        获取单个币种的价格
        
        Args:
            coin: 币种名称，如 "BTC", "ETH"
            
        Returns:
            价格或 None
        """
        try:
            prices = self.get_all_prices()
            return prices.get(coin)
        except Exception as e:
            logger.error(f"获取 {coin} 价格失败: {e}")
            return None
    
    def get_orderbook(self, coin: str) -> Optional[dict]:
        """
        获取订单簿（L2 数据）
        
        Args:
            coin: 币种名称
            
        Returns:
            订单簿数据
        """
        try:
            return self.info.l2_snapshot(coin)
        except Exception as e:
            logger.error(f"获取 {coin} 订单簿失败: {e}")
            return None
    
    def get_candles(self, coin: str, interval: str = "1h", lookback_hours: int = 24) -> Optional[list]:
        """
        获取K线数据
        
        Args:
            coin: 币种名称
            interval: 时间间隔 ("1m", "5m", "15m", "1h", "4h", "1d")
            lookback_hours: 回看小时数
            
        Returns:
            K线数据列表
        """
        try:
            import time
            end_time = int(time.time() * 1000)
            start_time = end_time - (lookback_hours * 3600 * 1000)
            return self.info.candles_snapshot(coin, interval, start_time, end_time)
        except Exception as e:
            logger.error(f"获取 {coin} K线数据失败: {e}")
            return None
    
    # ===== 账户信息查询 =====
    
    def get_account_state(self) -> Dict:
        """
        获取账户状态
        
        Returns:
            {
                "account_value": 1000.0,
                "available_balance": 500.0,
                "total_margin_used": 200.0,
                "positions": [...]
            }
        """
        try:
            user_state = self.info.user_state(self.address)
            margin = user_state["marginSummary"]
            
            return {
                "account_value": float(margin["accountValue"]),
                "available_balance": float(user_state.get("withdrawable", 0)),
                "total_margin_used": float(margin["totalMarginUsed"]),
                "total_position_value": float(margin["totalNtlPos"]),
                "raw_state": user_state
            }
        except Exception as e:
            logger.error(f"获取账户状态失败: {e}")
            return {
                "account_value": 0.0,
                "available_balance": 0.0,
                "total_margin_used": 0.0,
                "total_position_value": 0.0,
                "error": str(e)
            }
    
    def get_positions(self) -> List[Dict]:
        """
        获取当前持仓
        
        Returns:
            [
                {
                    "coin": "BTC",
                    "size": 0.5,
                    "entry_price": 50000.0,
                    "current_price": 51000.0,
                    "unrealized_pnl": 500.0,
                    "leverage": 5
                },
                ...
            ]
        """
        try:
            user_state = self.info.user_state(self.address)
            positions = []
            prices = self.get_all_prices()
            
            for asset_position in user_state["assetPositions"]:
                pos = asset_position["position"]
                coin = pos["coin"]
                size = float(pos["szi"])
                
                if abs(size) < 0.0001:  # 忽略极小持仓
                    continue
                
                positions.append({
                    "coin": coin,
                    "size": size,
                    "entry_price": float(pos.get("entryPx", 0)),
                    "current_price": prices.get(coin, 0.0),
                    "unrealized_pnl": float(pos["unrealizedPnl"]),
                    "leverage": pos["leverage"]["value"],
                    "margin_used": float(pos["marginUsed"]),
                    "liquidation_price": float(pos.get("liquidationPx", 0)) if pos.get("liquidationPx") else None
                })
            
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    def get_open_orders(self) -> List[Dict]:
        """
        获取未成交订单
        
        Returns:
            订单列表
        """
        try:
            orders = self.info.open_orders(self.address)
            return [
                {
                    "coin": order["coin"],
                    "side": "buy" if order["side"] == "B" else "sell",
                    "size": float(order["sz"]),
                    "price": float(order["limitPx"]),
                    "oid": order["oid"]
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"获取未成交订单失败: {e}")
            return []
    
    # ===== 交易执行（谨慎使用） =====
    
    def place_market_order(
        self, 
        coin: str, 
        is_buy: bool, 
        size: float, 
        slippage: float = 0.05,
        dry_run: bool = True
    ) -> Dict:
        """
        下市价单
        
        Args:
            coin: 币种
            is_buy: True=买入, False=卖出
            size: 数量
            slippage: 滑点容忍度
            dry_run: 是否仅模拟（不实际执行）
            
        Returns:
            执行结果
        """
        action = "买入" if is_buy else "卖出"
        
        if dry_run:
            logger.info(f"[模拟] {action} {size} {coin}")
            return {
                "success": True,
                "dry_run": True,
                "action": action,
                "coin": coin,
                "size": size,
                "message": f"模拟{action}成功"
            }
        
        try:
            logger.warning(f"[真实交易] {action} {size} {coin}")
            # market_open(coin, is_buy, sz, px=None, slippage=0.05)
            result = self.exchange.market_open(coin, is_buy, size, None, slippage)
            
            success = result["status"] == "ok"
            
            # 解析执行结果
            if success and "response" in result and "data" in result["response"]:
                statuses = result["response"]["data"]["statuses"]
                filled_info = []
                for status in statuses:
                    if "filled" in status:
                        filled = status["filled"]
                        filled_info.append({
                            "oid": filled.get("oid"),
                            "size": filled.get("totalSz"),
                            "price": filled.get("avgPx")
                        })
                    elif "error" in status:
                        logger.error(f"订单错误: {status['error']}")
                
                logger.info(f"✅ 交易成功: {filled_info}")
            
            return {
                "success": success,
                "dry_run": False,
                "action": action,
                "coin": coin,
                "size": size,
                "result": result
            }
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action,
                "coin": coin
            }
    
    def place_limit_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        dry_run: bool = True
    ) -> Dict:
        """
        下限价单
        
        Args:
            coin: 币种
            is_buy: True=买入, False=卖出
            size: 数量
            price: 限价价格
            dry_run: 是否仅模拟
            
        Returns:
            执行结果
        """
        action = "买入" if is_buy else "卖出"
        
        if dry_run:
            logger.info(f"[模拟] 限价{action} {size} {coin} @ {price}")
            return {
                "success": True,
                "dry_run": True,
                "action": f"限价{action}",
                "coin": coin,
                "size": size,
                "price": price
            }
        
        try:
            logger.warning(f"[真实交易] 限价{action} {size} {coin} @ {price}")
            result = self.exchange.order(
                coin, is_buy, size, price,
                order_type={"limit": {"tif": "Gtc"}}
            )
            
            return {
                "success": result["status"] == "ok",
                "dry_run": False,
                "result": result
            }
        except Exception as e:
            logger.error(f"下限价单失败: {e}")
            return {"success": False, "error": str(e)}
    
    def close_position(self, coin: str, dry_run: bool = True) -> Dict:
        """
        平仓
        
        Args:
            coin: 币种
            dry_run: 是否仅模拟
            
        Returns:
            执行结果
        """
        if dry_run:
            logger.info(f"[模拟] 平仓 {coin}")
            return {
                "success": True,
                "dry_run": True,
                "action": "平仓",
                "coin": coin
            }
        
        try:
            logger.warning(f"[真实交易] 平仓 {coin}")
            result = self.exchange.market_close(coin)
            
            return {
                "success": result["status"] == "ok",
                "dry_run": False,
                "result": result
            }
        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_order(self, coin: str, oid: int, dry_run: bool = True) -> Dict:
        """
        取消订单
        
        Args:
            coin: 币种
            oid: 订单ID
            dry_run: 是否仅模拟
            
        Returns:
            执行结果
        """
        if dry_run:
            logger.info(f"[模拟] 取消订单 {coin} #{oid}")
            return {"success": True, "dry_run": True}
        
        try:
            result = self.exchange.cancel(coin, oid)
            return {"success": result["status"] == "ok", "result": result}
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {"success": False, "error": str(e)}
