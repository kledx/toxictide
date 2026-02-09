#!/usr/bin/env python3
"""
TOXICTIDE 学习演示 - 第 5 步

完整实战演练 - 综合运用所有知识
"""

import time
from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def main():
    """第 5 步学习演示"""

    print("=" * 70)
    print("🚀 TOXICTIDE 学习演示 - 第 5 步：完整实战演练")
    print("=" * 70)
    print()

    print("🎓 恭喜您完成前 4 步学习！")
    print()
    print("现在让我们进行一次完整的实战演练，综合运用所学知识：")
    print("  ✅ 第 1 步：理解了系统的 10 步 Tick 流程")
    print("  ✅ 第 2 步：掌握了 5 个交互命令")
    print("  ✅ 第 3 步：深入理解了 7 层风控逻辑")
    print("  ✅ 第 4 步：学会了分析审计日志")
    print()
    print("📝 这次实战将模拟一个完整的交易会话：")
    print("  1. 启动系统并观察初始状态")
    print("  2. 观察市场数据变化")
    print("  3. 等待交易信号产生")
    print("  4. 分析风控决策")
    print("  5. 处理异常场景")
    print("  6. 总结和复盘")
    print()
    input("按回车键开始实战... ")

    # ========== 阶段 1: 系统启动 ==========
    print("\n" + "=" * 70)
    print("阶段 1/6: 系统启动和初始检查")
    print("=" * 70)
    print()

    print("📝 实战任务：")
    print("  - 启动系统")
    print("  - 检查系统状态")
    print("  - 了解当前市场环境")
    print()
    input("按回车键启动系统... ")

    config_obj = load_config()
    config = get_config_dict(config_obj)
    orch = Orchestrator(config)

    print("\n✅ 系统已启动")
    print()
    print("💡 就像使用 /status 命令，让我们检查初始状态...")

    # 运行几个 Tick
    for _ in range(3):
        orch._tick()

    state = orch.state

    print("\n━" * 70)
    print("📊 初始状态")
    print("━" * 70)

    if state.last_features:
        fv = state.last_features
        print(f"价格: ${fv.mid:.2f}")
        print(f"价差: {fv.spread_bps:.2f} bps")

    if state.last_stress:
        emoji = {"OK": "🟢", "WARN": "🟡", "DANGER": "🔴"}.get(state.last_stress.level, "⚪")
        print(f"市场压力: {emoji} {state.last_stress.level}")

    if state.last_regime:
        print(f"市场状态: {state.last_regime.price_regime} / {state.last_regime.flow_regime}")

    print("━" * 70)

    print("\n💡 分析：")
    print("  - 系统正常运行")
    print("  - 市场数据正在积累")
    print("  - 策略等待信号机会")

    input("\n按回车键继续... ")

    # ========== 阶段 2: 观察市场变化 ==========
    print("\n" + "=" * 70)
    print("阶段 2/6: 观察市场数据变化")
    print("=" * 70)
    print()

    print("📝 实战任务：")
    print("  - 运行 20 个 Tick 积累历史数据")
    print("  - 观察市场状态变化")
    print("  - 监控异常检测结果")
    print()
    input("按回车键开始监控... ")

    print("\n🔄 运行中（每 5 个 Tick 显示一次）...\n")

    for i in range(20):
        orch._tick()

        if (i + 1) % 5 == 0:
            fv = orch.state.last_features
            stress = orch.state.last_stress
            regime = orch.state.last_regime

            print(f"Tick {i+1:2d}: ", end="")
            if fv:
                print(f"价格=${fv.mid:.2f} | ", end="")
            if stress:
                print(f"压力={stress.level} | ", end="")
            if regime:
                print(f"状态={regime.price_regime}/{regime.flow_regime}")

    print("\n💡 观察：")
    print("  - 价格在波动")
    print("  - 市场状态在变化（趋势/震荡切换）")
    print("  - 压力级别大部分时间是 OK")
    print("  - 系统在持续监控和分析")

    input("\n按回车键继续... ")

    # ========== 阶段 3: 等待信号 ==========
    print("\n" + "=" * 70)
    print("阶段 3/6: 等待交易信号")
    print("=" * 70)
    print()

    print("📝 实战任务：")
    print("  - 继续运行直到产生信号")
    print("  - 理解为什么大部分时间无信号")
    print("  - 学习耐心等待")
    print()
    input("按回车键继续运行... ")

    print("\n🔄 继续运行 10 个 Tick...\n")

    signal_count = 0
    for i in range(10):
        orch._tick()

        decision = orch.state.last_decision
        if decision:
            if decision.action != "DENY" or (decision.reasons and decision.reasons[0] != "NO_SIGNAL"):
                print(f"Tick {i+1}: 🎯 检测到决策变化!")
                print(f"  决策: {decision.action}")
                print(f"  原因: {', '.join(decision.reasons)}")
                signal_count += 1

    print(f"\n📊 信号统计: {signal_count} 个特殊事件")

    print("\n💡 分析：")
    if signal_count == 0:
        print("  - 这是正常的！大部分时间系统在观望")
        print("  - 原因：策略需要明显的趋势或偏离")
        print("  - 需要 30+ Tick 积累足够历史数据")
        print("  - '不交易' 也是一种保护策略")
    else:
        print("  - 检测到市场变化")
        print("  - 风控系统正在评估")
        print("  - 这就是实际交易的真实情况")

    input("\n按回车键继续... ")

    # ========== 阶段 4: 分析决策 ==========
    print("\n" + "=" * 70)
    print("阶段 4/6: 分析风控决策")
    print("=" * 70)
    print()

    print("📝 实战任务：")
    print("  - 查看最后的决策")
    print("  - 理解拒绝原因")
    print("  - 判断决策是否合理")
    print()
    input("按回车键查看决策... ")

    # 显示决策（模拟 /why 命令）
    if orch.state.last_decision:
        from toxictide.explain.explain import build_explanation

        print("\n━" * 70)
        print("🔍 最后决策（/why 命令）")
        print("━" * 70)

        explanation = build_explanation(orch.state.last_decision)
        print(explanation)

        print("\n━" * 70)

        decision = orch.state.last_decision

        print("\n💡 决策分析：")

        if decision.action == "DENY":
            print("  ❌ 交易被拒绝")
            if "NO_SIGNAL" in decision.reasons:
                print("     → 原因：无交易信号")
                print("     → 评估：合理，系统在等待明确机会")
                print("     → 建议：继续运行，让系统积累数据")
            elif "DAILY_LOSS_EXCEEDED" in decision.reasons:
                print("     → 原因：日亏超限")
                print("     → 评估：合理，风控保护")
                print("     → 建议：停止交易，检查策略")
            else:
                print(f"     → 原因：{', '.join(decision.reasons)}")
                print("     → 评估：风控系统正常工作")

        elif decision.action == "ALLOW_WITH_REDUCTIONS":
            print("  ⚠️  交易允许但减仓")
            print(f"     → 最终仓位：${decision.size_usd:.2f}")
            print("     → 评估：风控系统根据市场条件调整")
            print("     → 建议：这是正常的风险管理")

        elif decision.action == "ALLOW":
            print("  ✅ 交易允许")
            print(f"     → 仓位：${decision.size_usd:.2f}")
            print("     → 评估：所有风控检查通过")
            print("     → 建议：监控执行结果")

    input("\n按回车键继续... ")

    # ========== 阶段 5: 模拟异常场景 ==========
    print("\n" + "=" * 70)
    print("阶段 5/6: 处理异常场景")
    print("=" * 70)
    print()

    print("📝 实战任务：")
    print("  - 模拟日亏超限")
    print("  - 观察风控如何响应")
    print("  - 学习应对策略")
    print()
    input("按回车键模拟异常... ")

    print("\n📉 模拟大额亏损...")
    orch._risk_guardian.record_trade(time.time(), pnl=-120.0)  # -1.2%

    print("🔄 运行一个 Tick 观察风控响应...\n")
    orch._tick()

    if orch.state.last_decision:
        decision = orch.state.last_decision

        print("━" * 70)
        print("🛡️ 风控响应")
        print("━" * 70)

        if "DAILY_LOSS_EXCEEDED" in decision.reasons:
            print("🔥 日亏熔断触发！")
            print(f"   当前日盈亏: {decision.facts.get('daily_pnl_pct', 0):.2f}%")
            print(f"   阈值: {decision.facts.get('max_daily_loss_pct', 0):.2f}%")
            print("\n💡 正确应对：")
            print("   1. 立即停止交易（/pause 或 /quit）")
            print("   2. 检查审计日志，分析亏损原因")
            print("   3. 评估策略是否失效")
            print("   4. 次日系统自动重置")
            print("   5. 不要立即放宽风控参数")

        print("━" * 70)

    input("\n按回车键继续... ")

    # ========== 阶段 6: 总结复盘 ==========
    print("\n" + "=" * 70)
    print("阶段 6/6: 总结和复盘")
    print("=" * 70)
    print()

    print("📊 会话统计分析...")
    print()

    # 统计
    log_path = orch._ledger.log_path

    # 读取日志统计
    import json
    from collections import Counter

    records = []
    with open(log_path, 'r') as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except:
                pass

    decisions = [r['risk']['action'] for r in records if 'risk' in r and r['risk']]
    stress_levels = [r['stress']['level'] for r in records if 'stress' in r and r['stress']]

    print("━" * 70)
    print("📊 本次会话统计")
    print("━" * 70)

    print(f"总 Tick 数: {len(records)}")
    print()

    print("决策分布:")
    for action, count in Counter(decisions).most_common():
        pct = count / len(decisions) * 100 if decisions else 0
        print(f"  {action}: {count} ({pct:.1f}%)")

    print("\n市场压力分布:")
    for level, count in Counter(stress_levels).most_common():
        pct = count / len(stress_levels) * 100 if stress_levels else 0
        emoji = {"OK": "🟢", "WARN": "🟡", "DANGER": "🔴"}.get(level, "⚪")
        print(f"  {emoji} {level}: {count} ({pct:.1f}%)")

    print(f"\n审计日志: {log_path}")
    print("━" * 70)

    # 关闭系统
    orch._shutdown()

    input("\n按回车键查看总结... ")

    # ========== 完整总结 ==========
    print("\n" + "=" * 70)
    print("🎉 恭喜！您已完成全部 5 步学习")
    print("=" * 70)

    print("""
✅ 完整学习路线回顾：

📚 第 1 步：理解系统如何运行
   ✅ 掌握了 10 步 Tick 流程
   ✅ 理解了数据如何流转
   ✅ 知道了每个组件的作用

🎮 第 2 步：体验交互命令
   ✅ 掌握了 5 个核心命令
   ✅ 知道何时使用哪个命令
   ✅ 理解了命令背后的逻辑

🛡️ 第 3 步：深入理解风控决策
   ✅ 完全理解了 7 层风控检查
   ✅ 知道了每层检查的优先级
   ✅ 学会了调整风控参数

📊 第 4 步：分析审计日志
   ✅ 掌握了 JSONL 日志格式
   ✅ 学会了统计分析
   ✅ 能够回放历史决策

🚀 第 5 步：完整实战演练
   ✅ 综合运用所有知识
   ✅ 模拟真实交易场景
   ✅ 学会了应对异常

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 现在您已经完全掌握 TOXICTIDE 系统！

您现在可以：

1️⃣  独立运行完整系统
   → python main_quiet.py
   → 熟练使用所有命令
   → 理解系统的每个决策

2️⃣  调试和优化
   → 分析审计日志
   → 调整风控参数
   → 优化策略配置

3️⃣  准备接入真实数据
   → 理解了系统架构
   → 知道了如何监控
   → 掌握了风控逻辑

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 推荐的下一步：

🔹 熟练阶段（1-2 周）
   → 每天运行 python main_quiet.py
   → 使用交互命令观察系统
   → 分析每天的审计日志
   → 尝试调整配置参数

🔹 进阶阶段（2-4 周）
   → 参考 REAL_DATA_INTEGRATION_GUIDE.md
   → 注册 Binance 测试网
   → 创建真实数据采集器
   → 在测试网运行系统

🔹 实盘阶段（1 个月后）
   ⚠️  测试网运行稳定 1-2 周
   ⚠️  小资金实盘测试（$100-$1000）
   ⚠️  确认盈利后逐步增加
   ⚠️  严格遵守风控规则

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 核心原则（永远记住）：

1. 🛡️ 风控第一
   → 保护本金 > 追求收益
   → 大部分时间观望是正常的
   → "不交易" 也是一种决策

2. 📊 数据驱动
   → 每天分析审计日志
   → 基于数据调整参数
   → 不要凭感觉决策

3. ⏱️ 耐心等待
   → 策略需要时间积累数据
   → 不要频繁调整参数
   → 给系统足够的观察期

4. 🔧 持续优化
   → 小步迭代，不要激进
   → 一次只调一个参数
   → 记录每次调整的效果

5. 📚 不断学习
   → 阅读完整文档
   → 研究市场微观结构
   → 关注系统表现

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 恭喜您完成学习！

您现在已经完全掌握了 TOXICTIDE 系统的使用方法。

从模拟交易开始，逐步积累经验，最终您将能够：
✅ 自信地运行真实交易
✅ 优化系统参数
✅ 开发新的策略
✅ 接入不同的交易所

祝您交易顺利！🚀

有任何问题随时查看文档或提问！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    main()
