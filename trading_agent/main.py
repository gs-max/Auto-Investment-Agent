"""
LangGraph 自动交易 Agent 主入口
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

from src.agent import TradingAgent
from src.tools import HyperliquidTools
from src.risk_manager import RiskManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent/logs/trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent/config/config.example.json") -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return json.load(f)


def load_strategy_prompt(prompt_path: str = "config/strategy_prompt.txt") -> str:
    """加载策略提示词"""
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def setup_hyperliquid(config: dict):
    """初始化 Hyperliquid SDK"""
    hl_config = config["hyperliquid"]
    
    # 创建账户
    account = eth_account.Account.from_key(hl_config["secret_key"])
    address = hl_config.get("account_address") or account.address
    
    logger.info(f"📍 账户地址: {address}")
    
    # 初始化 Info 和 Exchange
    base_url = hl_config.get("base_url", constants.TESTNET_API_URL)
    info = Info(base_url, skip_ws=True)
    exchange = Exchange(account, base_url, account_address=address)
    
    return address, info, exchange


def setup_llm(config: dict):
    """初始化 LLM 客户端"""
    llm_config = config["llm"]
    
    # 使用 OpenAI SDK（兼容 DeepSeek）
    client = OpenAI(
        api_key=llm_config["api_key"],
        base_url=llm_config.get("base_url", "https://api.openai.com/v1")
    )
    
    logger.info(f"🤖 LLM: {llm_config['provider']} - {llm_config['model']}")
    return client


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LangGraph 自动交易 Agent")
    parser.add_argument("--config", default="/Users/gaoshuo/Desktop/Fintech_Project/Auto Investment Agent/trading_agent/config/config.example.json", help="配置文件路径")
    parser.add_argument("--mode", choices=["once", "loop"], default="loop",
                       help="运行模式: once=单次, loop=持续循环（默认）")
    parser.add_argument("--interval", type=int, default=300, help="循环间隔（秒）")
    args = parser.parse_args()
    
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("🚀 LangGraph 自动交易 Agent 启动")
    logger.info("=" * 60)
    
    # 1. 加载配置
    config = load_config(args.config)
    strategy_prompt = load_strategy_prompt()
    
    # 2. 初始化组件
    address, info, exchange = setup_hyperliquid(config)
    llm_client = setup_llm(config)
    
    # 3. 创建工具和风险管理器
    tools = HyperliquidTools(info, exchange, address)
    risk_manager = RiskManager(config["risk"])
    
    # 显示资金限制信息
    user_state = info.user_state(address)
    actual_balance = float(user_state["marginSummary"]["accountValue"])
    max_usable = config["risk"].get("max_usable_capital")
    
    logger.info("=" * 60)
    logger.info(f"💰 账户实际余额: ${actual_balance:.2f} USDC")
    if max_usable:
        logger.info(f"🔒 Agent可用资金: ${max_usable:.2f} USDC (受限)")
        logger.info(f"📊 资金使用率: {(max_usable/actual_balance*100):.1f}%")
    else:
        logger.info(f"🔒 Agent可用资金: ${actual_balance:.2f} USDC (无限制)")
    logger.info("=" * 60)
    
    # 4. 创建 Agent
    dry_run = not config["risk"].get("enable_execution", False)
    if dry_run:
        logger.warning("⚠️  模拟模式：不会执行真实交易")
    else:
        logger.warning("🔴 真实交易模式：请谨慎！")
    
    agent = TradingAgent(
        tools=tools,
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
                logger.info(f"【第 {iteration} 轮检查】")
                result = agent.run_once()
                logger.info(f"⏱️  等待 {args.interval} 秒后进行下一轮检查...\n")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info(f"👋 用户手动停止 (共运行 {iteration} 轮)")
            logger.info("=" * 60)
    
    logger.info("=" * 60)
    logger.info("🏁 Agent 已停止")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
