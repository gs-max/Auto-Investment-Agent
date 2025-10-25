"""
风险管理模块
对 LLM 的决策进行风险检查和限制
"""
import logging
from typing import Dict, List, Literal

logger = logging.getLogger(__name__)


class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: Dict):
        """
        初始化风险管理器
        
        Args:
            config: 风险配置
                {
                    "max_usable_capital": 100,  # Agent最多可使用的资金（USDC）
                    "max_position_size": 0.1,  # 单币种最大仓位（占可用资金比例）
                    "max_total_exposure": 0.5,  # 总持仓占比
                    "max_single_trade_value": 1000,  # 单笔交易最大金额
                    "min_account_value": 100,  # 最小账户价值
                    "allowed_coins": ["BTC", "ETH"],  # 允许交易的币种
                    "max_leverage": 3,  # 最大杠杆
                    "enable_execution": False  # 是否允许真实交易
                }
        """
        self.config = config
        self.max_usable_capital = config.get("max_usable_capital", None)  # None表示使用全部资金
        self.max_position_size = config.get("max_position_size", 0.1)
        self.max_total_exposure = config.get("max_total_exposure", 0.5)
        self.max_single_trade_value = config.get("max_single_trade_value", 1000)
        self.min_account_value = config.get("min_account_value", 100)
        self.allowed_coins = config.get("allowed_coins", ["BTC", "ETH"])
        self.max_leverage = config.get("max_leverage", 3)
        self.enable_execution = config.get("enable_execution", False)
    
    def get_effective_capital(self, actual_account_value: float) -> float:
        """
        获取有效可用资金（考虑max_usable_capital限制）
        
        Args:
            actual_account_value: 实际账户价值
            
        Returns:
            有效可用资金
        """
        if self.max_usable_capital is None:
            return actual_account_value
        return min(actual_account_value, self.max_usable_capital)
    
    def check_trading_decision(
        self,
        decision: Literal["buy", "sell", "hold", "close"],
        coin: str,
        size: float,
        account_value: float,
        positions: List[Dict],
        current_price: float
    ) -> Dict:
        """
        检查交易决策是否符合风险要求
        
        Args:
            decision: 交易决策
            coin: 币种
            size: 交易数量
            account_value: 账户总价值
            positions: 当前持仓
            current_price: 当前价格
            
        Returns:
            {
                "passed": True/False,
                "message": "检查结果说明",
                "warnings": ["警告1", "警告2"],
                "blocked_reason": "拒绝原因（如果不通过）"
            }
        """
        warnings = []
        
        # 计算有效可用资金（考虑max_usable_capital限制）
        effective_capital = self.get_effective_capital(account_value)
        
        if self.max_usable_capital and account_value > self.max_usable_capital:
            warnings.append(f"账户有${account_value:.2f}，但仅使用${self.max_usable_capital:.2f}")
        
        # 1. 如果是 hold，直接通过
        if decision == "hold":
            return {
                "passed": True,
                "message": "持有决策，无需风险检查",
                "warnings": warnings,
                "blocked_reason": None
            }
        
        # 2. 检查是否启用真实交易
        if not self.enable_execution:
            warnings.append("真实交易未启用，将仅执行模拟")
        
        # 3. 检查账户价值（使用有效资金）
        if effective_capital < self.min_account_value:
            return {
                "passed": False,
                "message": "账户价值过低",
                "warnings": warnings,
                "blocked_reason": f"账户价值 ${account_value:.2f} 低于最小要求 ${self.min_account_value}"
            }
        
        # 4. 检查币种白名单（空数组表示不限制）
        if self.allowed_coins and coin not in self.allowed_coins:
            return {
                "passed": False,
                "message": "币种不在白名单中",
                "warnings": warnings,
                "blocked_reason": f"{coin} 不在允许交易的币种列表中: {self.allowed_coins}"
            }
        
        # 5. 检查交易金额
        trade_value = size * current_price
        if trade_value > self.max_single_trade_value:
            return {
                "passed": False,
                "message": "单笔交易金额过大",
                "warnings": warnings,
                "blocked_reason": f"交易金额 ${trade_value:.2f} 超过限制 ${self.max_single_trade_value}"
            }
        
        # 6. 检查仓位大小（买入时）- 使用有效资金计算
        if decision == "buy":
            position_value = trade_value
            position_ratio = position_value / effective_capital
            
            if position_ratio > self.max_position_size:
                return {
                    "passed": False,
                    "message": "单币种仓位过大",
                    "warnings": warnings,
                    "blocked_reason": f"仓位占比 {position_ratio:.2%} 超过限制 {self.max_position_size:.2%}（基于可用资金${effective_capital:.2f}）"
                }
        
        # 7. 检查总持仓占比 - 使用有效资金计算
        total_position_value = sum(abs(pos["size"]) * pos["current_price"] for pos in positions)
        if decision == "buy":
            total_position_value += trade_value
        
        total_exposure = total_position_value / effective_capital if effective_capital > 0 else 0
        if total_exposure > self.max_total_exposure:
            warnings.append(f"总持仓占比 {total_exposure:.2%} 接近或超过限制 {self.max_total_exposure:.2%}（基于可用资金${effective_capital:.2f}）")
        
        # 8. 检查杠杆
        for pos in positions:
            if pos["leverage"] > self.max_leverage:
                warnings.append(f"{pos['coin']} 杠杆 {pos['leverage']}x 超过建议值 {self.max_leverage}x")
        
        # 9. 检查平仓逻辑
        if decision == "close":
            has_position = any(pos["coin"] == coin for pos in positions)
            if not has_position:
                return {
                    "passed": False,
                    "message": "没有持仓无法平仓",
                    "warnings": warnings,
                    "blocked_reason": f"当前没有 {coin} 的持仓"
                }
        
        # 10. 检查卖出逻辑
        if decision == "sell":
            existing_position = next((pos for pos in positions if pos["coin"] == coin), None)
            if not existing_position:
                warnings.append(f"当前没有 {coin} 持仓，卖出将开空仓")
            elif abs(existing_position["size"]) < size:
                warnings.append(f"卖出数量 {size} 大于当前持仓 {abs(existing_position['size'])}")
        
        # 所有检查通过
        return {
            "passed": True,
            "message": "风险检查通过",
            "warnings": warnings,
            "blocked_reason": None
        }
    
    def get_safe_position_size(self, coin: str, account_value: float, current_price: float) -> float:
        """
        计算安全的仓位大小（基于有效可用资金）
        
        Args:
            coin: 币种
            account_value: 账户价值
            current_price: 当前价格
            
        Returns:
            建议的交易数量
        """
        effective_capital = self.get_effective_capital(account_value)
        max_value = effective_capital * self.max_position_size
        safe_size = max_value / current_price
        
        # 保留合理的小数位数
        if safe_size < 0.01:
            return round(safe_size, 4)
        elif safe_size < 1:
            return round(safe_size, 2)
        else:
            return round(safe_size, 1)
    
    def assess_market_risk(self, market_data: Dict) -> Dict:
        """
        评估市场风险
        
        Args:
            market_data: 市场数据
            
        Returns:
            风险评估结果
        """
        # 简化版本：后续可以加入更复杂的风险指标
        # 如波动率、成交量、资金费率等
        
        return {
            "risk_level": "medium",
            "volatility": "unknown",
            "recommendation": "谨慎交易"
        }
