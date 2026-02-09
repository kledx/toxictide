#!/usr/bin/env python3
"""
TOXICTIDE 学习演示 - 第 3 步

深入理解风控决策的 7 层检查逻辑
"""

import time
from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict
from toxictide.models import TradeCandidate


def main():
    """第 3 步学习演示"""

    print("=" * 70)
    print("🛡️ TOXICTIDE 学习演示 - 第 3 步：深入理解风控决策逻辑")
    print("=" * 70)
    print()

    print("📝 这个演示将教您：")
    print("  1. 风控守护的 7 层检查是什么")
    print("  2. 每层检查的优先级和逻辑")
    print("  3. 为什么交易被拒绝/允许/减仓")
    print("  4. 如何调整风控参数")
    print()
    input("按回车键开始... ")

    # ========== 初始化 ==========
    print("\n" + "=" * 70)
    print("准备工作：初始化系统")
    print("=" * 70)

    config_obj = load_config()
    config = get_config_dict(config_obj)
    orch = Orchestrator(config)

    print("✅ 系统已启动")
    print()

    # ========== 7 层风控概述 ==========
    print("=" * 70)
    print("风控守护的 7 层检查（从高到低优先级）")
    print("=" * 70)
    print("""
风控守护是系统的**安全核心**，通过 7 层优先级检查保护资金安全。

优先级从高到低（数字越小越优先）：

🔴 优先级 1: 数据质量检查
   → 数据过期（> 10 秒无更新）
   → 盘口不一致（spread <= 0）
   💡 触发后果: 立即拒绝（DENY）
   💡 原因: 数据有问题，不能基于错误数据交易

🔥 优先级 2: 日亏熔断
   → 日盈亏 < -1%（当日亏损超过 1%）
   💡 触发后果: 当日禁止新开仓（DENY）
   💡 原因: 防止单日巨亏

❄️ 优先级 3: 冷却期
   → 连续亏损触发冷却（如 3 笔连续亏损）
   💡 触发后果: 冷却期内禁止交易（DENY）
   💡 原因: 可能策略失效，需要暂停观察

📏 优先级 4: 仓位上限
   → 仓位 >= $3000（默认）
   💡 触发后果: 拒绝新开仓（DENY）
   💡 原因: 控制总风险敞口

💥 优先级 5: Impact/Toxic 检查
   → 冲击 > 20 bps (硬上限) → 拒绝（DENY）
   → 毒性流 >= 0.75 → 拒绝（DENY）
   → 冲击 > 10 bps (入场上限) → 减仓 50%（REDUCE）
   → 毒性流 >= 0.6 → 减仓 30%（REDUCE）
   💡 触发后果: 拒绝或减仓
   💡 原因: 市场流动性差，减少冲击成本

⚠️ 优先级 6: Market Stress
   → 压力 = DANGER → 拒绝（DENY）
   → 压力 = WARN → 减仓 50%（REDUCE）
   💡 触发后果: 拒绝或减仓
   💡 原因: 市场异常，降低风险

⏱️ 优先级 7: 交易频率
   → 最近 1 小时 >= 6 笔 → 拒绝（DENY）
   💡 触发后果: 拒绝新交易
   💡 原因: 防止过度交易

""")
    input("按回车键继续... ")

    # ========== 场景 1: 正常允许 ==========
    print("\n" + "=" * 70)
    print("场景 1: 正常允许（所有检查通过）")
    print("=" * 70)
    print()
    print("💡 条件：")
    print("  ✅ 数据正常")
    print("  ✅ 日盈亏正常")
    print("  ✅ 无冷却期")
    print("  ✅ 仓位未满")
    print("  ✅ 冲击和毒性正常")
    print("  ✅ 市场压力 OK")
    print("  ✅ 交易频率正常")
    print()

    # 运行几个 Tick
    for _ in range(5):
        orch._tick()

    if orch.state.last_decision:
        decision = orch.state.last_decision
        print(f"结果: {decision.action}")

        if decision.action == "ALLOW":
            print(f"✅ 交易允许，仓位 ${decision.size_usd:.2f}")
        elif decision.action == "DENY":
            print(f"❌ 被拒绝")
            print(f"原因: {', '.join(decision.reasons)}")

    input("\n按回车键继续... ")

    # ========== 场景 2: 日亏熔断 ==========
    print("\n" + "=" * 70)
    print("场景 2: 日亏熔断（优先级 2）")
    print("=" * 70)
    print()
    print("💡 模拟：记录一笔大亏损，触发日亏熔断")
    print()

    # 模拟日亏
    print("📉 模拟交易亏损 -$150（余额 $10,000 的 1.5%）...")
    orch._risk_guardian.record_trade(time.time(), pnl=-150.0)

    # 运行 Tick
    orch._tick()

    if orch.state.last_decision:
        decision = orch.state.last_decision
        print(f"\n结果: {decision.action}")

        if "DAILY_LOSS_EXCEEDED" in decision.reasons:
            print("🔥 触发日亏熔断！")
            print(f"   当前日盈亏: {decision.facts.get('daily_pnl_pct', 0):.2f}%")
            print(f"   阈值: {decision.facts.get('max_daily_loss_pct', 0):.2f}%")
            print()
            print("💡 解释：")
            print("   - 日亏超过 1%，系统自动停止当日新开仓")
            print("   - 这是保护机制，防止单日巨亏")
            print("   - 次日自动重置")

    input("\n按回车键继续... ")

    # ========== 场景 3: 冲击成本过高（减仓） ==========
    print("\n" + "=" * 70)
    print("场景 3: 冲击成本偏高（优先级 5 - 减仓）")
    print("=" * 70)
    print()
    print("💡 说明：")
    print("  - 冲击成本 > 10 bps（入场上限）")
    print("  - 不是完全拒绝，而是减仓 50%")
    print("  - 原因：市场流动性一般，降低冲击")
    print()
    print("风控逻辑:")
    print("  如果 impact > 10 bps (入场上限):")
    print("    → 原计划仓位 $1000")
    print("    → 减仓 50% → 最终仓位 $500")
    print("    → 决策: ALLOW_WITH_REDUCTIONS")

    input("\n按回车键继续... ")

    # ========== 场景 4: 冲击成本过高（拒绝） ==========
    print("\n" + "=" * 70)
    print("场景 4: 冲击成本过高（优先级 5 - 拒绝）")
    print("=" * 70)
    print()
    print("💡 说明：")
    print("  - 冲击成本 > 20 bps（硬上限）")
    print("  - 完全拒绝交易")
    print("  - 原因：市场流动性太差，交易成本过高")
    print()
    print("风控逻辑:")
    print("  如果 impact > 20 bps (硬上限):")
    print("    → 决策: DENY")
    print("    → 原因: IMPACT_HARD_CAP_EXCEEDED")

    input("\n按回车键继续... ")

    # ========== 场景 5: 毒性流过高 ==========
    print("\n" + "=" * 70)
    print("场景 5: 毒性流过高（优先级 5）")
    print("=" * 70)
    print()
    print("💡 什么是毒性流（Toxic Flow）？")
    print("  - 买卖严重不平衡")
    print("  - toxic = abs(买量 - 卖量) / (买量 + 卖量)")
    print("  - toxic = 0.75 表示 87.5% vs 12.5%（极度不平衡）")
    print()
    print("风控逻辑:")
    print("  如果 toxic >= 0.75 (DANGER):")
    print("    → 决策: DENY")
    print("    → 原因: 知情交易者在大量买/卖，不宜跟进")
    print()
    print("  如果 toxic >= 0.6 (WARN):")
    print("    → 减仓 30%")
    print("    → 决策: ALLOW_WITH_REDUCTIONS")

    input("\n按回车键继续... ")

    # ========== 场景 6: 市场压力 DANGER ==========
    print("\n" + "=" * 70)
    print("场景 6: 市场压力 DANGER（优先级 6）")
    print("=" * 70)
    print()
    print("💡 Market Stress Index 综合了：")
    print("  - OAD (盘口异常): 价差、冲击、流动性")
    print("  - VAD (成交量异常): 爆发、干涸、鲸鱼交易")
    print("  - Toxic Flow: 买卖不平衡")
    print()
    print("风控逻辑:")
    print("  如果 stress = DANGER:")
    print("    → 决策: DENY")
    print("    → 原因: 市场异常严重，暂停新开仓")
    print()
    print("  如果 stress = WARN:")
    print("    → 减仓 50%")
    print("    → 决策: ALLOW_WITH_REDUCTIONS")

    input("\n按回车键继续... ")

    # ========== 场景 7: 交易频率过高 ==========
    print("\n" + "=" * 70)
    print("场景 7: 交易频率过高（优先级 7）")
    print("=" * 70)
    print()
    print("💡 说明：")
    print("  - 最近 1 小时内已有 >= 6 笔交易")
    print("  - 拒绝新交易")
    print("  - 原因：防止过度交易，控制手续费")
    print()
    print("风控逻辑:")
    print("  如果 trades_last_hour >= 6:")
    print("    → 决策: DENY")
    print("    → 原因: TRADE_FREQUENCY_EXCEEDED")

    input("\n按回车键继续... ")

    # ========== 决策流程图 ==========
    print("\n" + "=" * 70)
    print("风控决策完整流程图")
    print("=" * 70)
    print("""
交易信号产生
    ↓
🔴 检查 1: 数据质量
    ↓ PASS
🔥 检查 2: 日亏熔断
    ↓ PASS
❄️ 检查 3: 冷却期
    ↓ PASS
📏 检查 4: 仓位上限
    ↓ PASS
💥 检查 5: Impact/Toxic
    ↓ PASS 或 REDUCE
⚠️ 检查 6: Market Stress
    ↓ PASS 或 REDUCE
⏱️ 检查 7: 交易频率
    ↓ PASS
━━━━━━━━━━━━━━━━━━━━━━━━
最终决策: ALLOW / ALLOW_WITH_REDUCTIONS / DENY

如果任何检查失败（DENY）:
  → 立即返回 DENY
  → 后续检查不再执行

如果检查建议减仓（REDUCE）:
  → 继续后续检查
  → 累积减仓比例
  → 最终决策: ALLOW_WITH_REDUCTIONS

如果所有检查通过（PASS）:
  → 最终决策: ALLOW
""")
    input("\n按回车键继续... ")

    # ========== 如何调整风控参数 ==========
    print("\n" + "=" * 70)
    print("如何调整风控参数")
    print("=" * 70)
    print()
    print("📝 配置文件: toxictide/config/default.yaml")
    print()
    print("🔧 可调整的关键参数：")
    print()
    print("1️⃣  日亏熔断")
    print("   max_daily_loss_pct: 1.0  # 当前: 1%")
    print("   调整建议:")
    print("     - 更保守: 0.5  (0.5%)")
    print("     - 更激进: 2.0  (2%)")
    print()
    print("2️⃣  仓位上限")
    print("   max_position_notional: 3000  # 当前: $3000")
    print("   调整建议:")
    print("     - 小资金: 500   ($500)")
    print("     - 大资金: 10000 ($10,000)")
    print()
    print("3️⃣  冲击成本上限")
    print("   impact_entry_cap_bps: 10.0  # 入场上限: 10 bps")
    print("   impact_hard_cap_bps: 20.0   # 硬上限: 20 bps")
    print("   调整建议:")
    print("     - 更严格: 5.0 / 10.0")
    print("     - 放宽: 15.0 / 30.0")
    print()
    print("4️⃣  毒性流阈值")
    print("   toxic_warn: 0.6     # 警告: 0.6")
    print("   toxic_danger: 0.75  # 危险: 0.75")
    print("   调整建议:")
    print("     - 更严格: 0.5 / 0.6")
    print("     - 放宽: 0.7 / 0.85")
    print()
    print("5️⃣  异常检测阈值")
    print("   oad.z_warn: 4.0    # OAD 警告: MAD z-score >= 4")
    print("   oad.z_danger: 6.0  # OAD 危险: MAD z-score >= 6")
    print("   vad.z_warn: 4.0    # VAD 警告")
    print("   vad.z_danger: 6.0  # VAD 危险")
    print("   调整建议:")
    print("     - 更敏感: 3.0 / 5.0 (更多告警)")
    print("     - 放宽: 5.0 / 8.0 (更少告警)")

    input("\n按回车键继续... ")

    # ========== 实战建议 ==========
    print("\n" + "=" * 70)
    print("实战建议")
    print("=" * 70)
    print("""
🛡️ 风控参数设置原则：

1️⃣  新手阶段（第 1-2 周）
   ✅ 使用默认参数
   ✅ 不要急于放宽限制
   ✅ 观察系统决策逻辑
   ✅ 理解为什么被拒绝

2️⃣  调试阶段（第 3-4 周）
   ✅ 根据实际情况微调
   ✅ 一次只调一个参数
   ✅ 观察效果后再调下一个
   ✅ 记录调整原因和结果

3️⃣  实盘阶段（1 个月后）
   ⚠️  先用测试网验证参数
   ⚠️  小资金实盘测试
   ⚠️  确认盈利后扩大规模
   ⚠️  定期审查风控参数

🚫 不要做的事：

❌ 不要因为交易被拒绝就放宽所有限制
❌ 不要同时调整多个参数
❌ 不要跳过测试网直接用真金白银
❌ 不要在亏损后立即调整参数（可能是策略问题）

✅ 应该做的事：

✅ 每天查看审计日志，分析拒绝原因
✅ 统计拒绝原因分布，针对性调整
✅ 回测参数调整的效果
✅ 保守 > 激进（保护本金最重要）

💡 记住：
   - 风控的目的是保护资金，不是增加交易频率
   - 大部分交易被拒绝是正常的
   - "不交易"也是一种决策
   - 宁可错过机会，不可冒险亏损
""")

    input("\n按回车键继续... ")

    # ========== 总结 ==========
    orch._shutdown()

    print("\n" + "=" * 70)
    print("🎉 恭喜！您已完成第 3 步学习")
    print("=" * 70)

    print("""
✅ 您现在深入理解了：

🛡️ 7 层风控检查：
   1. 🔴 数据质量（优先级最高）
   2. 🔥 日亏熔断（防止单日巨亏）
   3. ❄️ 冷却期（策略失效保护）
   4. 📏 仓位上限（风险敞口控制）
   5. 💥 Impact/Toxic（市场流动性检查）
   6. ⚠️ Market Stress（异常综合判断）
   7. ⏱️ 交易频率（过度交易防护）

💡 决策逻辑：
   - 优先级高的检查先执行
   - DENY 立即返回，不执行后续检查
   - REDUCE 累积，最终调整仓位
   - PASS 继续下一层检查

🔧 参数调整：
   - 知道哪些参数可以调整
   - 理解调整的影响
   - 掌握调整的原则

📚 下一步学习：
  → 运行 python learn_step4.py
  → 学习如何分析审计日志
  → 掌握决策回放和统计分析

🚀 现在您可以：
  → 理解 /why 命令显示的拒绝原因
  → 根据实际情况调整风控参数
  → 分析系统为什么做出某个决策
    """)


if __name__ == "__main__":
    main()
