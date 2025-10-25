"""
测试 Hyperliquid 连接和 LLM 配置
运行此脚本验证配置是否正确
"""
import json
import sys
from pathlib import Path

def test_config():
    """测试配置文件"""
    print("=" * 60)
    print("📝 测试配置文件")
    print("=" * 60)
    
    config_path = "config/config.testnet.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✅ 配置文件加载成功: {config_path}")
        
        # 检查必填项
        required = {
            "hyperliquid.account_address": config["hyperliquid"].get("account_address"),
            "hyperliquid.secret_key": config["hyperliquid"].get("secret_key"),
            "hyperliquid.base_url": config["hyperliquid"].get("base_url"),
            "llm.api_key": config["llm"].get("api_key"),
        }
        
        missing = [k for k, v in required.items() if not v]
        
        if missing:
            print(f"❌ 缺少必填项: {', '.join(missing)}")
            return False
        
        print("✅ 所有必填项已填写")
        print(f"   - 钱包地址: {config['hyperliquid']['account_address'][:10]}...")
        print(f"   - API URL: {config['hyperliquid']['base_url']}")
        print(f"   - 真实交易: {'✅ 启用' if config['risk']['enable_execution'] else '❌ 禁用'}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_path}")
        print(f"   请先创建配置文件")
        return False
    except Exception as e:
        print(f"❌ 配置文件错误: {e}")
        return False


def test_hyperliquid():
    """测试 Hyperliquid 连接"""
    print("\n" + "=" * 60)
    print("🔗 测试 Hyperliquid 连接")
    print("=" * 60)
    
    try:
        import eth_account
        from hyperliquid.info import Info
        from hyperliquid.exchange import Exchange
        
        with open("config/config.testnet.json", 'r') as f:
            config = json.load(f)
        
        # 初始化
        account = eth_account.Account.from_key(config["hyperliquid"]["secret_key"])
        address = config["hyperliquid"].get("account_address") or account.address
        base_url = config["hyperliquid"]["base_url"]
        
        print(f"📍 连接地址: {address}")
        print(f"🌐 API URL: {base_url}")
        
        # 测试 Info API
        info = Info(base_url, skip_ws=True)
        user_state = info.user_state(address)
        
        account_value = float(user_state["marginSummary"]["accountValue"])
        withdrawable = float(user_state.get("withdrawable", 0))
        
        print(f"✅ 连接成功")
        print(f"💰 账户余额: ${account_value:.2f} USDC")
        print(f"💵 可提现: ${withdrawable:.2f} USDC")
        
        # 获取价格
        prices = info.all_mids()
        btc_price = float(prices.get("BTC", 0))
        eth_price = float(prices.get("ETH", 0))
        
        print(f"📊 BTC 价格: ${btc_price:,.2f}")
        print(f"📊 ETH 价格: ${eth_price:,.2f}")
        
        # 获取持仓
        positions = []
        for asset_position in user_state["assetPositions"]:
            pos = asset_position["position"]
            if abs(float(pos["szi"])) > 0.0001:
                positions.append(pos)
        
        if positions:
            print(f"📈 当前持仓: {len(positions)} 个")
            for pos in positions:
                print(f"   - {pos['coin']}: {float(pos['szi']):.4f}, "
                      f"盈亏: ${float(pos['unrealizedPnl']):.2f}")
        else:
            print(f"📈 当前持仓: 无")
        
        return True
        
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print(f"   请运行: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


def test_llm():
    """测试 LLM 连接"""
    print("\n" + "=" * 60)
    print("🤖 测试 LLM 连接")
    print("=" * 60)
    
    try:
        from openai import OpenAI
        
        with open("config/config.testnet.json", 'r') as f:
            config = json.load(f)
        
        llm_config = config["llm"]
        
        client = OpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config.get("base_url", "https://api.deepseek.com")
        )
        
        print(f"🔗 测试 {llm_config['provider']} API...")
        
        # 简单测试
        response = client.chat.completions.create(
            model=llm_config["model"],
            messages=[
                {"role": "user", "content": "请回复：OK"}
            ],
            max_tokens=10
        )
        
        reply = response.choices[0].message.content
        print(f"✅ LLM 响应: {reply}")
        
        # 测试 Function Calling
        print(f"🔧 测试 Function Calling...")
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "测试函数",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"}
                        },
                        "required": ["message"]
                    }
                }
            }
        ]
        
        response = client.chat.completions.create(
            model=llm_config["model"],
            messages=[
                {"role": "user", "content": "请调用test_function，参数message设为'success'"}
            ],
            tools=tools,
            tool_choice="auto"
        )
        
        if response.choices[0].message.tool_calls:
            print(f"✅ Function Calling 支持")
        else:
            print(f"⚠️  Function Calling 可能不支持，将使用备用方案")
        
        return True
        
    except ImportError:
        print(f"❌ 缺少 openai 库")
        print(f"   请运行: pip install openai")
        return False
    except Exception as e:
        print(f"❌ LLM 连接失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n🚀 开始测试配置...\n")
    
    results = []
    
    # 测试配置
    results.append(("配置文件", test_config()))
    
    if results[0][1]:  # 只有配置正确才继续
        results.append(("Hyperliquid", test_hyperliquid()))
        results.append(("LLM", test_llm()))
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name:.<30} {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！可以运行 Agent 了。")
        print("\n运行命令:")
        print("  python main.py --config config/config.testnet.json")
    else:
        print("\n⚠️  部分测试失败，请检查配置后重试。")
        sys.exit(1)


if __name__ == "__main__":
    main()
