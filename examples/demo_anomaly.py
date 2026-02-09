#!/usr/bin/env python3
"""
TOXICTIDE Demo - 异常场景演示

展示系统如何响应市场异常
"""

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def main():
    """异常场景演示"""
    print("=" * 60)
    print("TOXICTIDE 异常场景演示")
    print("=" * 60)
    print()

    # 加载配置（返回 Pydantic 模型）
    config_obj = load_config()

    # 转换为字典（兼容现有代码）
    config = get_config_dict(config_obj)

    # 初始化 Orchestrator
    orch = Orchestrator(config)

    print("场景 1: 正常市场")
    print("-" * 60)

    for i in range(3):
        orch._tick()
        if orch.state.last_stress:
            print(f"  Tick {i+1}: 压力={orch.state.last_stress.level}")

    print()
    print("场景 2: 模拟价差飙升（Spread Spike）")
    print("-" * 60)

    # 模拟异常
    snapshot, trades = orch._collector.simulate_anomaly("spread_spike")
    orch._orderbook.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)

    for trade in trades:
        orch._tape.add(trade)

    # 运行 tick
    orch._tick()

    if orch.state.last_features:
        print(f"  价差: {orch.state.last_features.spread_bps:.2f} bps (正常: ~5 bps)")

    if orch.state.last_stress:
        print(f"  压力: {orch.state.last_stress.level}")

    print()
    print("场景 3: 模拟成交量爆发（Volume Burst）")
    print("-" * 60)

    # 模拟异常
    snapshot, trades = orch._collector.simulate_anomaly("volume_burst")
    orch._orderbook.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)

    for trade in trades:
        orch._tape.add(trade)

    # 运行 tick
    orch._tick()

    if orch.state.last_features:
        print(f"  成交量: {orch.state.last_features.vol:.2f} (正常: ~100)")

    if orch.state.last_stress:
        print(f"  压力: {orch.state.last_stress.level}")

    print()
    print("场景 4: 模拟流动性断层（Liquidity Gap）")
    print("-" * 60)

    # 模拟异常
    snapshot, trades = orch._collector.simulate_anomaly("liquidity_gap")
    orch._orderbook.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)

    for trade in trades:
        orch._tape.add(trade)

    # 运行 tick
    orch._tick()

    if orch.state.last_features:
        print(f"  买方深度: ${orch.state.last_features.depth_bid_k:.0f}")
        print(f"  卖方深度: ${orch.state.last_features.depth_ask_k:.0f}")

    if orch.state.last_stress:
        print(f"  压力: {orch.state.last_stress.level}")

    # 关闭
    orch._shutdown()

    print()
    print("=" * 60)
    print("演示完成！")
    print(f"审计日志: {orch._ledger.log_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
