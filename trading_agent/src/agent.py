"""LangGraph 交易 Agent 主类"""
import logging
from langgraph.graph import StateGraph, END
from src.state import TradingState, create_initial_state
from src.nodes import (
    fetch_market_data_node,
    get_account_status_node,
    llm_analysis_node,
    risk_check_node,
    execute_trade_node
)
from src.tools import HyperliquidTools
from src.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class TradingAgent:
    """基于 LangGraph 的交易 Agent"""
    
    def __init__(
        self,
        tools: HyperliquidTools,
        risk_manager: RiskManager,
        llm_client,
        strategy_prompt: str,
        dry_run: bool = True
    ):
        self.tools = tools
        self.risk_manager = risk_manager
        self.llm_client = llm_client
        self.strategy_prompt = strategy_prompt
        self.dry_run = dry_run
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态机"""
        workflow = StateGraph(TradingState)
        
        # 添加节点
        workflow.add_node("fetch_market", 
                         lambda s: fetch_market_data_node(s, self.tools))
        workflow.add_node("get_account", 
                         lambda s: get_account_status_node(s, self.tools))
        workflow.add_node("llm_analysis", 
                         lambda s: llm_analysis_node(s, self.llm_client, self.strategy_prompt))
        workflow.add_node("risk_check", 
                         lambda s: risk_check_node(s, self.risk_manager))
        workflow.add_node("execute", 
                         lambda s: execute_trade_node(s, self.tools, self.dry_run))
        
        # 定义流程
        workflow.set_entry_point("fetch_market")
        workflow.add_edge("fetch_market", "get_account")
        workflow.add_edge("get_account", "llm_analysis")
        workflow.add_edge("llm_analysis", "risk_check")
        
        # 条件分支：风险检查通过才执行
        workflow.add_conditional_edges(
            "risk_check",
            lambda s: "execute" if s["risk_passed"] or s["trading_decision"] == "hold" else "end",
            {
                "execute": "execute",
                "end": END
            }
        )
        workflow.add_edge("execute", END)
        
        return workflow.compile()
    
    def run_once(self) -> TradingState:
        """运行一次完整的交易循环"""
        logger.info("=" * 50)
        logger.info("🚀 开始新的交易周期")
        logger.info("=" * 50)
        
        initial_state = create_initial_state()
        result = self.graph.invoke(initial_state)
        
        self._log_result(result)
        return result
    
    def _log_result(self, state: TradingState):
        """记录结果"""
        logger.info("\n" + "=" * 50)
        logger.info("📋 交易周期总结")
        logger.info("=" * 50)
        
        # 显示账户和资金信息
        actual_value = state['account_value']
        effective_value = self.risk_manager.get_effective_capital(actual_value)
        
        logger.info(f"💰 账户总价值: ${actual_value:.2f}")
        if effective_value < actual_value:
            logger.info(f"🔒 可用资金: ${effective_value:.2f} (受限)")
        logger.info(f"📊 当前持仓: {len(state['positions'])} 个")
        
        logger.info(f"\n🤔 决策: {state['trading_decision'].upper()}")
        logger.info(f"✅ 风险检查: {'✅ 通过' if state['risk_passed'] else '❌ 未通过'}")
        
        # 显示风险警告
        if state.get('risk_assessment') and state['risk_assessment'].get('warnings'):
            logger.info("\n⚠️  风险提示:")
            for warning in state['risk_assessment']['warnings']:
                logger.info(f"   - {warning}")
        
        if state.get('market_analysis'):
            logger.info(f"\n🔍 LLM 分析:\n{state['market_analysis']}")
        
        if state.get('execution_result'):
            logger.info(f"\n💼 执行结果: {state['execution_result']}")
        
        logger.info("=" * 50 + "\n")
