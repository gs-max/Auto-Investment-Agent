#!/usr/bin/env python3
"""
多资产组合交易 Agent
支持同时管理多个持仓，无币种限制
"""
import json
import logging
import argparse
import time
from datetime import datetime
from typing import Dict
import eth_account
from openai import OpenAI
from langgraph.graph import StateGraph, END

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

from src.state import TradingState
from src.advanced_tools import AdvancedTradingTools
from src.risk_manager import RiskManager
from src.advanced_nodes import fetch_advanced_market_data_node
from src.nodes import get_account_status_node
from src.portfolio_nodes import enhanced_portfolio_analysis_node, execute_portfolio_trades_node

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/portfolio_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.testnet.json") -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return json.load(f)


def load_strategy_prompt(prompt_path: str) -> str:
    """加载策略提示"""
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


class PortfolioTradingAgent:
    """多资产组合交易Agent"""
    
    def __init__(
        self,
        config: Dict,
        strategy_prompt: str,
        dry_run: bool = True
    ):
        self.config = config
        self.strategy_prompt = strategy_prompt
        self.dry_run = dry_run
        
        # 初始化组件
        self.address, self.info, self.exchange = setup_hyperliquid(config)
        self.llm_client = setup_llm(config)
        self.advanced_tools = AdvancedTradingTools(self.info, self.exchange, self.address)
        self.risk_manager = RiskManager(config["risk"])
        
        # 构建工作流
        self.graph = self.build_graph()
    
    def build_graph(self):
        """构建 LangGraph 工作流"""
        workflow = StateGraph(TradingState)
        
        # 定义节点
        workflow.add_node("fetch_market",
                         lambda s: fetch_advanced_market_data_node(s, self.advanced_tools))
        workflow.add_node("get_account",
                         lambda s: get_account_status_node(s, self.advanced_tools))
        workflow.add_node("portfolio_analysis",
                         lambda s: enhanced_portfolio_analysis_node(
                             s, self.llm_client, self.strategy_prompt, self.advanced_tools))
        workflow.add_node("execute_portfolio",
                         lambda s: execute_portfolio_trades_node(
                             s, self.advanced_tools, self.dry_run))
        
        # 定义流程
        workflow.set_entry_point("fetch_market")
        workflow.add_edge("fetch_market", "get_account")
        workflow.add_edge("get_account", "portfolio_analysis")
        
        # 条件分支：如果有交易决策就执行
        def should_execute(s):
            trades = s.get("portfolio_trades", [])
            logger.info(f"🔍 条件判断: portfolio_trades 有 {len(trades)} 个交易")
            if len(trades) > 0:
                logger.info(f"   → 将执行交易")
                return "execute"
            else:
                logger.info(f"   → 跳过执行")
                return "end"
        
        workflow.add_conditional_edges(
            "portfolio_analysis",
            should_execute,
            {
                "execute": "execute_portfolio",
                "end": END
            }
        )
        workflow.add_edge("execute_portfolio", END)
        
        return workflow.compile()
    
    def run_once(self) -> Dict:
        """运行一次分析和交易"""
        initial_state = {
            "messages": [],
            "current_prices": {},
            "market_data": {},
            "account_value": 0,
            "available_balance": 0,
            "positions": [],
            "market_analysis": {},
            "trading_decision": "hold",
            "target_coin": "",
            "target_size": 0.0,
            "confidence": 0.0,
            "reasoning": "",
            "risk_assessment": {},
            "risk_passed": False,
            "risk_message": "",
            "execution_result": {},
            "success": False,
            "portfolio_trades": [],
            "portfolio_analysis": "",
            "execution_results": [],
            "timestamp": "",
            "iteration": 0
        }
        
        result = self.graph.invoke(initial_state)
        return result
    
    def run_loop(self, interval: int = 60):
        """持续运行"""
        round_num = 0
        
        try:
            while True:
                round_num += 1
                logger.info(f"【第 {round_num} 轮组合分析】")
                logger.info("=" * 60)
                logger.info("🚀 开始新的组合管理周期")
                logger.info("=" * 60)
                
                result = self.run_once()
                
                # 打印总结
                logger.info("")
                logger.info("=" * 60)
                logger.info("📋 组合管理周期总结")
                logger.info("=" * 60)
                logger.info(f"💰 账户总价值: ${result['account_value']:.2f}")
                logger.info(f"📊 当前持仓: {len(result['positions'])} 个")
                
                if result.get('portfolio_analysis'):
                    logger.info(f"\n📝 组合分析:\n{result['portfolio_analysis']}")
                
                trades = result.get('portfolio_trades', [])
                if trades:
                    logger.info(f"\n📋 执行了 {len(trades)} 个交易决策")
                    
                    execution_results = result.get('execution_results', [])
                    success_count = sum(1 for r in execution_results if r["result"].get("success"))
                    logger.info(f"✅ 成功: {success_count}/{len(trades)}")
                    logger.info(f"❌ 失败: {len(trades) - success_count}/{len(trades)}")
                
                logger.info("=" * 60)
                logger.info("")
                logger.info(f"⏱️  等待 {interval} 秒后进行下一轮检查...")
                logger.info("")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("")
            logger.info("=" * 60)
            logger.info("⚠️  接收到中断信号，正在安全退出...")
            logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="多资产组合交易 Agent")
    parser.add_argument(
        '--config',
        default='config/config.testnet.json',
        help='配置文件路径'
    )
    parser.add_argument(
        '--strategy',
        default='config/portfolio_strategy_prompt.txt',
        help='策略提示文件路径'
    )
    parser.add_argument(
        '--mode',
        choices=['once', 'loop'],
        default='loop',
        help='运行模式：once=单次, loop=持续'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模拟交易模式（不实际下单）'
    )
    
    args = parser.parse_args()
    
    # 启动信息
    logger.info("=" * 70)
    logger.info("🎯 多资产组合交易 Agent 启动")
    logger.info("=" * 70)
    logger.info("📌 特性: 多持仓 | 无限制 | 智能分散 | 主动调仓")
    logger.info("⚡ 模式: 组合管理 | 2-4个同时决策 | 风险对冲")
    logger.info("=" * 70)
    
    # 加载配置和策略
    config = load_config(args.config)
    strategy_prompt = load_strategy_prompt(args.strategy)
    
    # 初始化组件
    print("\n🔧 初始化组件...")
    address, info, exchange = setup_hyperliquid(config)
    print(f"   ✅ Hyperliquid 初始化完成 (地址: {address[:10]}...)")
    logger.info(f"📍 账户地址: {address}")
    
    llm_client = setup_llm(config)
    print(f"   ✅ LLM 客户端初始化完成")
    logger.info(f"🤖 LLM: {config['llm']['provider']} - {config['llm']['model']}")
    
    print(f"   ✅ 组合管理工具创建完成")
    print(f"   ✅ 风险管理器创建完成")
    
    # 显示账户信息
    user_state = info.user_state(address)
    actual_balance = float(user_state["marginSummary"]["accountValue"])
    max_usable = config["risk"].get("max_usable_capital", actual_balance)
    max_positions = config["risk"].get("max_positions", 8)
    max_leverage = config["risk"].get("max_leverage", 10)
    
    logger.info("=" * 70)
    logger.info(f"💰 账户余额: ${actual_balance:.2f} USDC")
    logger.info(f"💵 可用资金: ${max_usable:.2f} USDC")
    logger.info(f"🎯 最大持仓数: {max_positions} 个")
    logger.info(f"🎯 最大杠杆: {max_leverage}x")
    logger.info(f"🪙 币种限制: 无（可交易任何币种）")
    logger.info(f"⏱️  检查间隔: {config['agent']['check_interval']} 秒")
    logger.info("=" * 70)
    
    if args.dry_run:
        logger.info("🧪 模拟交易模式：不会实际下单")
    else:
        logger.warning("🔴 真实交易模式：请谨慎！")
    
    # 创建Agent
    agent = PortfolioTradingAgent(
        config=config,
        strategy_prompt=strategy_prompt,
        dry_run=args.dry_run
    )
    
    # 运行
    if args.mode == 'once':
        logger.info("📌 单次运行模式")
        logger.info("=" * 60)
        logger.info("🚀 开始组合管理周期")
        logger.info("=" * 60)
        
        result = agent.run_once()
        
        # 打印总结
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 组合管理总结")
        logger.info("=" * 60)
        logger.info(f"💰 账户总价值: ${result['account_value']:.2f}")
        logger.info(f"📊 当前持仓: {len(result['positions'])} 个")
        
        if result.get('portfolio_analysis'):
            logger.info(f"\n📝 组合分析:\n{result['portfolio_analysis']}")
        
        trades = result.get('portfolio_trades', [])
        if trades:
            logger.info(f"\n📋 执行了 {len(trades)} 个交易决策")
        
        logger.info("=" * 60)
        
    else:
        interval = config['agent'].get('check_interval', 60)
        logger.info(f"🔄 持续运行模式，检查间隔: {interval} 秒")
        logger.info("按 Ctrl+C 可随时停止")
        logger.info("")
        
        agent.run_loop(interval)


if __name__ == "__main__":
    main()
