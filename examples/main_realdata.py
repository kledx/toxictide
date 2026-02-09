#!/usr/bin/env python3
"""
TOXICTIDE - 真实市场数据版本

使用币安合约（Futures）的实时市场数据
Paper Mode（模拟交易，安全）
"""

import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from toxictide.market.collector_real import BinanceMarketCollectorSync
from toxictide.config_loader import load_config, get_config_dict
from toxictide.models import Trade
from toxictide.app import Orchestrator
from toxictide.ui.cli import CLI


def main():
    """主函数"""

    print("=" * 70)
    print("🚀 TOXICTIDE - 真实市场数据模式")
    print("=" * 70)
    print()
    print("📊 数据源：币安 ETH-USDT 永续合约（主网）")
    print("💰 交易模式：Paper Mode（模拟交易，安全）")
    print("🛡️ 风控系统：完整 7 层风控检查")
    print("📝 审计日志：完整决策记录")
    print()
    print("=" * 70)
    print()

    # 启动市场数据采集器
    print("📡 正在连接到币安合约 WebSocket...")
    symbol = "ETHUSDT"

    collector = BinanceMarketCollectorSync(symbol=symbol, testnet=False)
    collector.start()

    if not collector.is_connected():
        print("❌ 无法连接到币安 WebSocket")
        print()
        print("可能的原因：")
        print("  - 网络连接问题")
        print("  - 防火墙阻止 WebSocket 连接")
        print()
        print("💡 建议：")
        print("  - 重新运行 python test_binance_simple.py 验证连接")
        print("  - 检查防火墙设置")
        sys.exit(1)

    print(f"✅ 已连接到币安合约 - {symbol}")
    print()

    # 测试获取数据
    print("📊 获取初始市场数据...")
    time.sleep(2)

    book = collector.get_orderbook_snapshot()
    if book:
        print(f"  当前价格: ${book.mid:.2f}")
        print(f"  价差: ${book.spread:.4f} ({book.spread / book.mid * 10000:.2f} bps)")
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

    # 创建 Orchestrator（传入真实数据采集器）
    print("🔧 启动 TOXICTIDE 系统...")
    print()
    print("💡 系统说明：")
    print("  ✅ 使用币安真实市场数据（ETH-USDT 永续合约）")
    print("  ✅ Paper Mode 模拟交易（不会真实下单）")
    print("  ✅ 所有决策基于真实市场条件计算")
    print("  ✅ 完整的风控系统运作（7 层检查）")
    print("  ✅ 审计日志记录所有决策过程")
    print()
    print("⚠️  重要说明：")
    print("  - 当前仍为 Paper Mode，不会发送真实订单")
    print("  - 所有交易决策仅用于学习和测试")
    print("  - 审计日志可用于回放和分析")
    print()

    # 关键修改：传入真实数据采集器
    orch = Orchestrator(config, real_collector=collector)

    # 启动 CLI
    cli = CLI(orch)
    cli.start()

    print("✅ 系统已启动！")
    print()
    print("━" * 70)
    print("📖 可用命令：")
    print("━" * 70)
    print("  /status  - 查看系统状态（显示真实市场价格）")
    print("  /why     - 查看最后决策解释")
    print("  /pause   - 暂停交易决策")
    print("  /resume  - 恢复交易决策")
    print("  /quit    - 退出系统")
    print("━" * 70)
    print()
    print("💡 使用建议：")
    print("  1. 每隔几分钟输入 /status 查看市场状态")
    print("  2. 输入 /why 查看为什么交易被拒绝")
    print("  3. 观察系统如何基于真实市场数据做决策")
    print("  4. 查看 logs/ 目录下的审计日志")
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
