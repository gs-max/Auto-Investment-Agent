"""
高级 LangGraph 自动交易 Agent
支持：杠杆、止盈止损、技术分析、历史数据
"""
import json
import logging
import argparse
import time
from pathlib import Path
import eth_account
from openai import OpenAI

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

from langgraph.graph import StateGraph, END
from src.state import TradingState, create_initial_state
from src.advanced_tools import AdvancedTradingTools
from src.advanced_nodes import (
    fetch_advanced_market_data_node,
    enhanced_llm_analysis_node,
    execute_advanced_trade_node
)
from src.nodes import get_account_status_node, risk_check_node
from src.risk_manager import RiskManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent/logs/advanced_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.testnet.json") -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return json.load(f)


def load_strategy_prompt(prompt_path: str = "config/aggressive_strategy_prompt.txt") -> str:
    """加载策略提示词"""
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def setup_hyperliquid(config: dict):
    """初始化 Hyperliquid SDK"""
    hl_config = config["hyperliquid"]
    
    account = eth_account.Account.from_key(hl_config["secret_key"])
    address = hl_config.get("account_address") or account.address
    
    logger.info(f"📍 账户地址: {address}")
    
    base_url = hl_config.get("base_url", constants.TESTNET_API_URL)
    info = Info(base_url, skip_ws=True)
    exchange = Exchange(account, base_url, account_address=address)
    
    return address, info, exchange


def setup_llm(config: dict):
    """初始化 LLM 客户端"""
    llm_config = config["llm"]
    
    client = OpenAI(
        api_key=llm_config["api_key"],
        base_url=llm_config.get("base_url", "https://api.openai.com/v1")
    )
    
    logger.info(f"🤖 LLM: {llm_config['provider']} - {llm_config['model']}")
    return client


class AdvancedTradingAgent:
    """高级交易 Agent"""
    
    def __init__(
        self,
        advanced_tools: AdvancedTradingTools,
        risk_manager: RiskManager,
        llm_client,
        strategy_prompt: str,
        dry_run: bool = True
    ):
        self.advanced_tools = advanced_tools
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
                         lambda s: fetch_advanced_market_data_node(s, self.advanced_tools))
        workflow.add_node("get_account", 
                         lambda s: get_account_status_node(s, self.advanced_tools))
        workflow.add_node("llm_analysis", 
                         lambda s: enhanced_llm_analysis_node(s, self.llm_client, 
                                                             self.strategy_prompt, self.advanced_tools))
        workflow.add_node("risk_check", 
                         lambda s: risk_check_node(s, self.risk_manager))
        workflow.add_node("execute", 
                         lambda s: execute_advanced_trade_node(s, self.advanced_tools, self.dry_run))
        
        # 定义流程
        workflow.set_entry_point("fetch_market")
        workflow.add_edge("fetch_market", "get_account")
        workflow.add_edge("get_account", "llm_analysis")
        workflow.add_edge("llm_analysis", "risk_check")
        
        # 条件分支（强制交易模式：只要有决策就执行，不管风险检查）
        workflow.add_conditional_edges(
            "risk_check",
            lambda s: "execute" if s["trading_decision"] in ["buy", "sell", "close"] else "end",
            {
                "execute": "execute",
                "end": END
            }
        )
        workflow.add_edge("execute", END)
        
        return workflow.compile()
    
    def run_once(self) -> TradingState:
        """运行一次完整的交易循环"""
        logger.info("=" * 60)
        logger.info("🚀 开始新的高级交易周期")
        logger.info("=" * 60)
        
        initial_state = create_initial_state()
        result = self.graph.invoke(initial_state)
        
        self._log_result(result)
        return result
    
    def _log_result(self, state: TradingState):
        """记录结果"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 高级交易周期总结")
        logger.info("=" * 60)
        
        # 账户信息
        actual_value = state['account_value']
        effective_value = self.risk_manager.get_effective_capital(actual_value)
        
        logger.info(f"💰 账户总价值: ${actual_value:.2f}")
        if effective_value < actual_value:
            logger.info(f"🔒 可用资金: ${effective_value:.2f} (受限)")
        
        # 持仓信息
        logger.info(f"📊 当前持仓: {len(state['positions'])} 个")
        for pos in state['positions']:
            pnl_emoji = "📈" if pos['unrealized_pnl'] > 0 else "📉"
            logger.info(f"  {pnl_emoji} {pos['coin']}: {pos['size']:.4f}, "
                       f"入场${pos['entry_price']:.2f}, "
                       f"盈亏${pos['unrealized_pnl']:+.2f}, "
                       f"{pos['leverage']}x杠杆")
        
        # 决策信息
        logger.info(f"\n🤔 决策: {state['trading_decision'].upper()}")
        if state.get('target_coin'):
            logger.info(f"   币种: {state['target_coin']}")
            logger.info(f"   数量: {state['target_size']}")
            logger.info(f"   杠杆: {state.get('target_leverage', 1)}x")
            if state.get('use_tpsl'):
                logger.info(f"   止盈: {state.get('take_profit_pct')}%")
                logger.info(f"   止损: {state.get('stop_loss_pct')}%")
        
        logger.info(f"   置信度: {state.get('confidence', 0):.0%}")
        logger.info(f"✅ 风险检查: {'✅ 通过' if state['risk_passed'] else '❌ 未通过'}")
        
        # 风险警告
        if state.get('risk_assessment') and state['risk_assessment'].get('warnings'):
            logger.info("\n⚠️  风险提示:")
            for warning in state['risk_assessment']['warnings']:
                logger.info(f"   - {warning}")
        
        # 市场分析
        if state.get('reasoning'):
            logger.info(f"\n🔍 决策理由:\n{state['reasoning']}")
        
        # 执行结果
        if state.get('execution_result'):
            result = state['execution_result']
            if result.get('success'):
                logger.info(f"\n✅ 执行成功")
            else:
                logger.info(f"\n❌ 执行失败: {result.get('message', result.get('error'))}")
        
        logger.info("=" * 60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="高频交易 Agent - 激进模式")
    parser.add_argument("--config", default="config/config.testnet.json", help="配置文件路径")
    parser.add_argument("--mode", choices=["once", "loop"], default="loop",
                       help="运行模式")
    parser.add_argument("--interval", type=int, default=60, help="循环间隔（秒），默认60秒高频模式")
    parser.add_argument("--strategy", default="config/aggressive_strategy_prompt.txt", help="策略提示词文件")
    args = parser.parse_args()
    
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    logger.info("=" * 70)
    logger.info("🚀 高频交易 Agent 启动 - 激进模式")
    logger.info("=" * 70)
    logger.info("📌 功能: 杠杆 | 止盈止损 | 技术分析 | 高频交易")
    logger.info("⚡ 模式: 激进策略 | 60秒检查 | 无币种限制")
    logger.info("=" * 70)
    
    # 1. 加载配置
    config = load_config(args.config)
    strategy_prompt = load_strategy_prompt(args.strategy)
    
    # 2. 初始化组件
    print("\n🔧 初始化组件...")
    address, info, exchange = setup_hyperliquid(config)
    print(f"   ✅ Hyperliquid 初始化完成 (地址: {address[:10]}...)")
    
    llm_client = setup_llm(config)
    print(f"   ✅ LLM 客户端初始化完成")
    
    # 3. 创建高级工具
    advanced_tools = AdvancedTradingTools(info, exchange, address)
    print(f"   ✅ 高级交易工具创建完成")
    
    risk_manager = RiskManager(config["risk"])
    print(f"   ✅ 风险管理器创建完成")
    
    # 显示资金和交易信息
    user_state = info.user_state(address)
    actual_balance = float(user_state["marginSummary"]["accountValue"])
    max_usable = config["risk"].get("max_usable_capital", actual_balance)
    allowed_coins = config["risk"].get("allowed_coins", [])
    max_leverage = config["risk"].get("max_leverage", 1)
    
    logger.info("=" * 70)
    logger.info(f"💰 账户余额: ${actual_balance:.2f} USDC")
    logger.info(f"💵 可用资金: ${max_usable:.2f} USDC ({(max_usable/actual_balance*100):.1f}%)")
    logger.info(f"🎯 最大杠杆: {max_leverage}x")
    logger.info(f"🪙 允许币种: {'所有币种' if not allowed_coins else ', '.join(allowed_coins)}")
    logger.info(f"⚡ 检查间隔: {args.interval}秒")
    logger.info("=" * 70)
    
    # 4. 创建 Agent
    dry_run = not config["risk"].get("enable_execution", False)
    if dry_run:
        logger.warning("⚠️  模拟模式：不会执行真实交易")
    else:
        logger.warning("🔴 真实交易模式：请谨慎！")
    
    agent = AdvancedTradingAgent(
        advanced_tools=advanced_tools,
        risk_manager=risk_manager,
        llm_client=llm_client,
        strategy_prompt=strategy_prompt,
        dry_run=dry_run
    )
    
    # 5. 运行
    if args.mode == "once":
        logger.info("📌 单次运行模式")
        result = agent.run_once()
        logger.info("✅ 完成")
        
    else:  # loop mode
        logger.info(f"🔄 持续运行模式，检查间隔: {args.interval} 秒")
        logger.info("按 Ctrl+C 可随时停止\n")
        
        iteration = 0
        try:
            while True:
                iteration += 1
                logger.info(f"【第 {iteration} 轮高级分析】")
                result = agent.run_once()
                logger.info(f"⏱️  等待 {args.interval} 秒后进行下一轮检查...\n")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 70)
            logger.info(f"👋 用户手动停止 (共运行 {iteration} 轮)")
            logger.info("=" * 70)
    
    logger.info("=" * 70)
    logger.info("🏁 高级 Agent 已停止")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
