"""
交易Agent的状态定义
"""
from typing import TypedDict, Annotated, Literal
import operator


class TradingState(TypedDict):
    """
    LangGraph 状态机的状态定义
    """
    # ===== 市场数据 =====
    current_prices: dict  # {"BTC": 50000.0, "ETH": 3000.0}
    market_data: dict  # 详细市场数据
    
    # ===== 账户信息 =====
    account_value: float  # 账户总价值
    positions: list  # 当前持仓列表
    available_balance: float  # 可用余额
    
    # ===== LLM 分析结果 =====
    market_analysis: dict  # 市场技术分析（多币种）
    trading_decision: Literal["buy", "sell", "hold", "close"]  # 交易决策
    target_coin: str  # 目标币种
    target_size: float  # 目标数量
    confidence: float  # 决策置信度 (0-1)
    reasoning: str  # 决策理由
    
    # ===== 风险控制 =====
    risk_assessment: dict  # 风险评估结果
    risk_passed: bool  # 是否通过风险检查
    risk_message: str  # 风险检查消息
    
    # ===== 执行结果 =====
    execution_result: dict  # 交易执行结果
    success: bool  # 是否成功
    
    # ===== 组合管理（多资产） =====
    portfolio_trades: list  # 多个交易决策列表
    portfolio_analysis: str  # 组合分析说明
    execution_results: list  # 多个执行结果列表
    
    # ===== 日志和消息 =====
    messages: Annotated[list, operator.add]  # 累积消息列表
    timestamp: str  # 当前时间戳
    iteration: int  # 迭代次数


def create_initial_state() -> TradingState:
    """创建初始状态"""
    return TradingState(
        current_prices={},
        market_data={},
        account_value=0.0,
        positions=[],
        available_balance=0.0,
        market_analysis={},
        trading_decision="hold",
        target_coin="",
        target_size=0.0,
        confidence=0.0,
        reasoning="",
        risk_assessment={},
        risk_passed=False,
        risk_message="",
        execution_result={},
        success=False,
        portfolio_trades=[],
        portfolio_analysis="",
        execution_results=[],
        messages=[],
        timestamp="",
        iteration=0
    )
