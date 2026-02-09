#!/usr/bin/env python3
"""
止损系统测试脚本

快速验证止损/止盈功能
"""

import time
from toxictide.models import TradeCandidate, Fill, Position
from toxictide.position.manager import PositionManager
from toxictide.position.monitor import PositionMonitor


def test_stop_loss_system():
    """测试止损系统"""

    print("=" * 70)
    print("🧪 止损系统功能测试")
    print("=" * 70)
    print()

    # 初始化
    pm = PositionManager()
    monitor = PositionMonitor(pm, max_hold_time_sec=300)  # 5 分钟 TTL

    print("✅ 持仓管理器和监控器已初始化")
    print()

    # ========== 测试 1：多头止损触发 ==========
    print("━" * 70)
    print("测试 1：多头止损触发")
    print("━" * 70)

    # 模拟开仓
    candidate = TradeCandidate(
        ts=time.time(),
        side="long",
        entry_price=2100.00,
        stop_price=2094.95,  # 止损 -0.5%
        tp_price=2121.00,    # 止盈 +1.0%
        confidence=0.7,
        ttl_sec=300,
        strategy="trend_breakout",
    )

    fill = Fill(
        ts=time.time(),
        order_id="test_001",
        price=2100.00,
        size=0.5,
        fee=0.05,
        side="buy",
    )

    position = pm.open_position(candidate, [fill], size_usd=1000.0)

    print(f"✅ 开仓成功：")
    print(f"   持仓 ID: {position.position_id}")
    print(f"   方向: {position.side}")
    print(f"   入场价: ${position.entry_price:.2f}")
    print(f"   止损价: ${position.stop_price:.2f}")
    print(f"   止盈价: ${position.tp_price:.2f}")
    print()

    # 模拟价格下跌触发止损
    print("📉 模拟价格下跌...")
    current_price = 2094.50  # 低于止损价 2094.95

    print(f"   当前价格: ${current_price:.2f}")
    print(f"   未实现盈亏: ${position.unrealized_pnl(current_price):.2f}")
    print()

    # 检查止损
    to_close = monitor.check_positions(current_price, time.time())

    if to_close:
        position_id, reason, close_price = to_close[0]
        print(f"🛑 止损触发！")
        print(f"   平仓原因: {reason}")
        print(f"   平仓价格: ${close_price:.2f}")

        # 执行平仓
        closed = pm.close_position(position_id, close_price, time.time(), reason)
        print(f"   已实现盈亏: ${closed.pnl:.2f}")
        print()
        print("✅ 测试 1 通过：止损正常触发")
    else:
        print("❌ 测试 1 失败：止损未触发")

    print()

    # ========== 测试 2：多头止盈触发 ==========
    print("━" * 70)
    print("测试 2：多头止盈触发")
    print("━" * 70)

    # 模拟开仓
    candidate2 = TradeCandidate(
        ts=time.time(),
        side="long",
        entry_price=2100.00,
        stop_price=2094.95,
        tp_price=2121.00,
        confidence=0.7,
        ttl_sec=300,
        strategy="trend_breakout",
    )

    position2 = pm.open_position(candidate2, [fill], size_usd=1000.0)

    print(f"✅ 开仓成功：{position2.position_id}")
    print()

    # 模拟价格上涨触发止盈
    print("📈 模拟价格上涨...")
    current_price = 2122.00  # 高于止盈价 2121.00

    print(f"   当前价格: ${current_price:.2f}")
    print(f"   未实现盈亏: ${position2.unrealized_pnl(current_price):.2f}")
    print()

    # 检查止盈
    to_close = monitor.check_positions(current_price, time.time())

    if to_close:
        position_id, reason, close_price = to_close[0]
        print(f"🎯 止盈触发！")
        print(f"   平仓原因: {reason}")
        print(f"   平仓价格: ${close_price:.2f}")

        # 执行平仓
        closed = pm.close_position(position_id, close_price, time.time(), reason)
        print(f"   已实现盈亏: ${closed.pnl:.2f}")
        print()
        print("✅ 测试 2 通过：止盈正常触发")
    else:
        print("❌ 测试 2 失败：止盈未触发")

    print()

    # ========== 测试 3：空头止损触发 ==========
    print("━" * 70)
    print("测试 3：空头止损触发")
    print("━" * 70)

    # 模拟开空仓
    candidate3 = TradeCandidate(
        ts=time.time(),
        side="short",
        entry_price=2100.00,
        stop_price=2110.50,  # 止损 +0.5%
        tp_price=2079.00,    # 止盈 -1.0%
        confidence=0.7,
        ttl_sec=300,
        strategy="trend_breakout",
    )

    position3 = pm.open_position(candidate3, [fill], size_usd=1000.0)

    print(f"✅ 开空仓成功：{position3.position_id}")
    print(f"   入场价: ${position3.entry_price:.2f}")
    print(f"   止损价: ${position3.stop_price:.2f}（价格上涨触发）")
    print()

    # 模拟价格上涨触发止损
    print("📈 模拟价格上涨...")
    current_price = 2111.00  # 高于止损价 2110.50

    print(f"   当前价格: ${current_price:.2f}")
    print(f"   未实现盈亏: ${position3.unrealized_pnl(current_price):.2f}")
    print()

    # 检查止损
    to_close = monitor.check_positions(current_price, time.time())

    if to_close:
        position_id, reason, close_price = to_close[0]
        print(f"🛑 止损触发！")
        print(f"   平仓原因: {reason}")
        print(f"   平仓价格: ${close_price:.2f}")

        # 执行平仓
        closed = pm.close_position(position_id, close_price, time.time(), reason)
        print(f"   已实现盈亏: ${closed.pnl:.2f}")
        print()
        print("✅ 测试 3 通过：空头止损正常触发")
    else:
        print("❌ 测试 3 失败：空头止损未触发")

    print()

    # ========== 统计汇总 ==========
    print("━" * 70)
    print("📊 持仓统计")
    print("━" * 70)

    stats = pm.get_statistics()

    print(f"总持仓数: {stats['total_positions']}")
    print(f"活跃持仓: {stats['active_positions']}")
    print(f"已平仓: {stats['closed_positions']}")
    print(f"总盈亏: ${stats['total_pnl']:.2f}")
    print(f"胜率: {stats['win_rate_pct']:.1f}%")
    print()

    print("=" * 70)
    print("🎉 所有测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    test_stop_loss_system()
