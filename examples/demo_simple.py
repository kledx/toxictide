#!/usr/bin/env python3
"""
TOXICTIDE Demo - 简化版诊断

最小化的诊断版本，避免格式化错误
"""

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def safe_format(value, format_spec=".2f", default="N/A"):
    """安全的格式化函数，避免类型错误"""
    try:
        if value is None:
            return default
        # 尝试转换为 float
        num_value = float(value)
        return f"{num_value:{format_spec}}"
    except (ValueError, TypeError):
        return str(value)


def main():
    """简化诊断演示"""
    print("=" * 60)
    print("TOXICTIDE 简化诊断演示")
    print("=" * 60)
    print()

    # 加载配置
    config_obj = load_config()
    config = get_config_dict(config_obj)

    # 初始化 Orchestrator
    orch = Orchestrator(config)

    print("运行 30 个 tick（积累足够历史数据）...\n")

    # 统计
    allow_count = 0
    reduction_count = 0
    deny_count = 0

    signal_count = 0

    # 运行 30 个 tick
    for i in range(30):
        try:
            orch._tick()

            # 获取最新状态
            fv = orch.state.last_features
            stress = orch.state.last_stress
            regime = orch.state.last_regime
            decision = orch.state.last_decision

            # 每 10 个 Tick 打印一次
            if (i + 1) % 10 == 0:
                print(f"\n{'='*60}")
                print(f"Tick {i+1}")
                print(f"{'='*60}")

                if fv:
                    print(f"📊 市场特征:")
                    print(f"  价格: ${safe_format(fv.mid)}")
                    print(f"  价差: {safe_format(fv.spread_bps)} bps")
                    print(f"  毒性流: {safe_format(fv.toxic)}")

                if stress:
                    print(f"\n🚨 市场压力:")
                    print(f"  级别: {stress.level}")
                    print(f"  分数: {safe_format(stress.score)}")

                if regime:
                    print(f"\n🌍 市场状态:")
                    print(f"  价格: {regime.price_regime}")
                    print(f"  波动率: {regime.vol_regime}")
                    print(f"  流动性: {regime.flow_regime}")

                if decision:
                    print(f"\n🛡️ 风控决策:")
                    print(f"  决策: {decision.action}")
                    print(f"  仓位: ${safe_format(decision.size_usd)}")
                    if decision.reasons:
                        print(f"  原因: {decision.reasons[0] if decision.reasons else 'N/A'}")

            # 统计决策
            if decision:
                if decision.action == "ALLOW":
                    allow_count += 1
                    signal_count += 1
                    print(f"  ✅ Tick {i+1}: 交易允许！")
                elif decision.action == "ALLOW_WITH_REDUCTIONS":
                    reduction_count += 1
                    signal_count += 1
                    print(f"  ⚠️  Tick {i+1}: 交易允许但减仓")
                else:
                    deny_count += 1

        except Exception as e:
            print(f"\n❌ Tick {i+1} 出错: {e}")
            import traceback
            traceback.print_exc()
            break

    # 关闭
    orch._shutdown()

    # 打印统计
    print("\n" + "=" * 60)
    print("📊 演示统计")
    print("=" * 60)
    print(f"总 Tick 数: {i+1}")
    print(f"允许: {allow_count}")
    print(f"减仓: {reduction_count}")
    print(f"拒绝: {deny_count}")
    print(f"信号生成次数: {signal_count}")
    print()
    print(f"审计日志: {orch._ledger.log_path}")
    print("=" * 60)
    print()

    if signal_count == 0:
        print("提示: 没有生成交易信号是正常的！")
        print("原因: 策略需要明显的趋势或价格偏离才会触发")
        print("建议: 运行 python demo_anomaly.py 查看异常场景")
    else:
        print(f"🎉 成功生成了 {signal_count} 个交易信号！")


if __name__ == "__main__":
    main()
