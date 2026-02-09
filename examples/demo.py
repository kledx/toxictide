#!/usr/bin/env python3
"""
TOXICTIDE Demo - 基础演示

运行 10 个 tick 并打印关键状态
"""

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def main():
    """基础演示"""
    print("=" * 60)
    print("TOXICTIDE 基础演示")
    print("=" * 60)
    print()

    # 加载配置（返回 Pydantic 模型）
    config_obj = load_config()

    # 转换为字典（兼容现有代码）
    config = get_config_dict(config_obj)

    # 初始化 Orchestrator
    orch = Orchestrator(config)

    print("运行 10 个 tick...\n")

    # 统计
    allow_count = 0
    reduction_count = 0
    deny_count = 0

    # 运行 10 个 tick
    for i in range(10):
        orch._tick()

        # 打印状态
        if orch.state.last_features and orch.state.last_decision:
            fv = orch.state.last_features
            stress = orch.state.last_stress
            regime = orch.state.last_regime
            decision = orch.state.last_decision

            print(f"Tick {i+1}:")
            print(f"  价格: ${fv.mid:.2f}")
            print(f"  压力: {stress.level if stress else 'N/A'}")
            print(f"  状态: {regime.price_regime}/{regime.flow_regime if regime else 'N/A'}")
            print(f"  决策: {decision.action}")
            print()

            # 统计
            if decision.action == "ALLOW":
                allow_count += 1
            elif decision.action == "ALLOW_WITH_REDUCTIONS":
                reduction_count += 1
            else:
                deny_count += 1

    # 关闭
    orch._shutdown()

    # 打印统计
    print("=" * 60)
    print("📊 演示统计")
    print("=" * 60)
    print(f"总 Tick 数: 10")
    print(f"允许: {allow_count}")
    print(f"减仓: {reduction_count}")
    print(f"拒绝: {deny_count}")
    print()
    print(f"审计日志: {orch._ledger.log_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
