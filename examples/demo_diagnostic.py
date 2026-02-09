#!/usr/bin/env python3
"""
TOXICTIDE Demo - 详细诊断版本

展示每个 Tick 的详细决策过程
"""

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def main():
    """详细诊断演示"""
    print("=" * 60)
    print("TOXICTIDE 详细诊断演示")
    print("=" * 60)
    print()

    # 加载配置
    config_obj = load_config()
    config = get_config_dict(config_obj)

    # 初始化 Orchestrator
    orch = Orchestrator(config)

    print("运行 20 个 tick（积累更多历史数据）...\n")

    # 统计
    allow_count = 0
    reduction_count = 0
    deny_count = 0

    # 运行 20 个 tick
    for i in range(20):
        orch._tick()

        # 获取最新状态（只使用存在的属性）
        fv = orch.state.last_features
        stress = orch.state.last_stress
        regime = orch.state.last_regime
        decision = orch.state.last_decision

        # 每 5 个 Tick 打印一次详细信息（避免输出过多）
        if (i + 1) % 5 == 0 or i == 0:
            print(f"\n{'='*60}")
            print(f"Tick {i+1}")
            print(f"{'='*60}")

            if fv:
                print(f"📊 市场特征:")
                print(f"  价格: ${fv.mid:.2f}")
                print(f"  价差: {fv.spread_bps:.2f} bps")
                print(f"  买方冲击: {fv.impact_buy_bps:.2f} bps")
                print(f"  卖方冲击: {fv.impact_sell_bps:.2f} bps")
                print(f"  成交量: {fv.vol:.2f}")
                print(f"  毒性流: {fv.toxic:.2f}")

            if stress:
                print(f"\n🚨 市场压力:")
                print(f"  级别: {stress.level}")
                print(f"  分数: {stress.score:.2f}")

            if regime:
                print(f"\n🌍 市场状态:")
                print(f"  价格状态: {regime.price_regime}")
                print(f"  波动率状态: {regime.vol_regime}")
                print(f"  流动性状态: {regime.flow_regime}")

            if decision:
                print(f"\n🛡️ 风控决策:")
                print(f"  决策: {decision.action}")
                print(f"  仓位: ${decision.size_usd:.2f}")
                if decision.reasons:
                    print(f"  原因: {', '.join(decision.reasons)}")

        # 统计决策
        if decision:
            if decision.action == "ALLOW":
                allow_count += 1
            elif decision.action == "ALLOW_WITH_REDUCTIONS":
                reduction_count += 1
            else:
                deny_count += 1

    # 关闭
    orch._shutdown()

    # 打印统计
    print("\n" + "=" * 60)
    print("📊 演示完成")
    print("=" * 60)
    print(f"审计日志: {orch._ledger.log_path}")
    print()
    print("提示: 查看上面的详细输出，了解为什么没有生成交易信号")
    print("=" * 60)


if __name__ == "__main__":
    main()
