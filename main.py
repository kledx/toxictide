#!/usr/bin/env python3
"""
TOXICTIDE - 真实数据模式启动脚本

使用币安测试网的实时市场数据
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from toxictide.market.collector_real import BinanceMarketCollectorSync
from toxictide.config_loader import load_config, get_config_dict
from toxictide.app import Orchestrator
from toxictide.ui.cli import CLI


def main():
    """主函数"""

    print("=" * 70)
    print("🚀 TOXICTIDE - 真实数据模式")
    print("=" * 70)
    print()

    # 检查环境变量
    # 优先检查是否配置了 API Key（无论主网还是测试网，都需要配置）
    # 这里为了简单，我们假设如果用了 Mainnet，用户会配置 BINANCE_API_KEY / SECRET
    # 如果用了 Testnet，会配置 BINANCE_TESTNET_API_KEY / SECRET
    
    use_testnet = os.getenv("BINANCE_USE_TESTNET", "true").lower() == "true"
    
    if use_testnet:
        api_key = os.getenv("BINANCE_TESTNET_API_KEY")
        api_secret = os.getenv("BINANCE_TESTNET_API_SECRET")
        env_prefix = "BINANCE_TESTNET"
        network_name = "币安测试网"

        if not api_key or not api_secret:
            print(f"❌ 错误：未找到 {network_name} API 密钥配置")
            print()
            print("请按以下步骤设置：")
            print("1. 注册币安测试网账户: https://testnet.binance.vision/")
            print("2. 配置环境变量:")
            print(f"   {env_prefix}_API_KEY=你的API密钥")
            print(f"   {env_prefix}_API_SECRET=你的密钥Secret")
            print()
            sys.exit(1)
    else:
        # 主网模式：数据采集不需要 API Key（公开 WebSocket）
        # 只有在实盘执行时才需要（目前代码只支持 Paper 执行，所以 API Key 可选）
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        env_prefix = "BINANCE"
        network_name = "币安主网"

        if not api_key or not api_secret:
             print(f"⚠️  未检测到 {network_name} API 密钥")
             print("   (注意：仅数据采集和模拟交易不需要 Key，实盘执行将无法进行)")
             print()
        else:
             print(f"✅ {network_name} API 密钥已配置")

    print()

    # 启动市场数据采集器
    use_testnet = os.getenv("BINANCE_USE_TESTNET", "true").lower() == "true"
    network_name = "币安测试网" if use_testnet else "币安主网"
    
    print(f"📡 正在连接到 {network_name}...")
    symbol = os.getenv("BINANCE_SYMBOL", "ETHUSDT")

    collector = BinanceMarketCollectorSync(symbol=symbol, testnet=use_testnet)
    collector.start()

    if not collector.is_connected():
        print(f"❌ 无法连接到 {network_name}")
        print("   请检查网络连接")
        sys.exit(1)

    print(f"✅ 已连接到 {network_name} - {symbol}")
    print()

    # 测试获取数据
    print("📊 获取市场数据测试...")
    time.sleep(2)

    book = collector.get_orderbook_snapshot()
    if book:
        print(f"  价格: ${book.mid:.2f}")
        print(f"  价差: {book.spread:.2f} ({book.spread / book.mid * 10000:.2f} bps)")
        print(f"  最优买价: ${book.bids[0].price:.2f} x {book.bids[0].size:.4f}")
        print(f"  最优卖价: ${book.asks[0].price:.2f} x {book.asks[0].size:.4f}")
    else:
        print("  ⚠️  暂无盘口数据，继续等待...")

    trades = collector.get_recent_trades(max_count=5)
    if trades:
        print(f"  最近交易: {len(trades)} 笔")

    print()
    print("=" * 70)
    print()

    # 加载配置
    print("⚙️  加载配置...")
    config_obj = load_config()
    config = get_config_dict(config_obj)
    print("✅ 配置加载完成")
    print()

    # 启动系统（使用真实数据）
    print("🔧 启动 TOXICTIDE 系统...")
    print()
    print("💡 提示：")
    print("  - 系统将使用币安测试网的真实市场数据")
    print("  - 当前仍为 Paper Mode（模拟交易）")
    print("  - 所有交易决策会基于真实市场数据计算")
    print("  - 审计日志会记录完整的决策过程")
    print()

    # 创建 Orchestrator 并注入真实数据采集器
    # 注入 main_real.py 中已经创建和启动的 collector
    orch = Orchestrator(config, real_collector=collector)

    # 启动 WebUI
    try:
        from toxictide.ui.web import WebUIv2
        port = int(os.getenv("WEB_UI_PORT", 8000))
        web_ui = WebUIv2(port=port)
        web_ui.start()
        print(f"✅ Web Dashboard已启动: http://localhost:{port}")
    except ImportError:
        print("⚠️  WebUI 模块未找到，跳过启动")
    except Exception as e:
        print(f"⚠️  WebUI 启动失败: {e}")

    # 启动 CLI
    cli = CLI(orch)
    cli.start()

    print("✅ 系统已启动！")
    print()
    print("━" * 70)
    print("📖 可用命令：")
    print("━" * 70)
    print("  /status  - 查看系统状态")
    print("  /why     - 查看最后决策解释")
    print("  /pause   - 暂停交易")
    print("  /resume  - 恢复交易")
    print("  /quit    - 退出系统")
    print("━" * 70)
    print()

    try:
        orch.run()
    except KeyboardInterrupt:
        print("\n正在关闭系统...")
    finally:
        collector.stop()
        print("已停止")


if __name__ == "__main__":
    main()
