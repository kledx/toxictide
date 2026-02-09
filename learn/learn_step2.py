#!/usr/bin/env python3
"""
TOXICTIDE 学习演示 - 第 2 步

学习如何使用交互命令控制系统
"""

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def main():
    """第 2 步学习演示"""

    print("=" * 70)
    print("🎮 TOXICTIDE 学习演示 - 第 2 步：体验交互命令")
    print("=" * 70)
    print()

    print("📝 这个演示将教您：")
    print("  1. 系统的 5 个交互命令是什么")
    print("  2. 每个命令什么时候用")
    print("  3. 如何查看系统状态")
    print("  4. 如何理解风控决策")
    print()
    input("按回车键开始... ")

    # ========== 初始化 ==========
    print("\n" + "=" * 70)
    print("准备工作：初始化系统")
    print("=" * 70)

    config_obj = load_config()
    config = get_config_dict(config_obj)
    orch = Orchestrator(config)

    print("✅ 系统已启动（后台模拟运行中）")
    print()

    # ========== 命令 1: /status ==========
    print("=" * 70)
    print("命令 1/5: /status - 查看系统状态")
    print("=" * 70)
    print()
    print("💡 作用：显示当前系统运行状态")
    print("💡 何时使用：")
    print("   - 想知道系统是否正常运行")
    print("   - 查看当前市场价格和压力")
    print("   - 检查系统是运行还是暂停")
    print()
    input("按回车键模拟 /status 命令... ")

    # 运行几个 Tick 积累数据
    print("\n🔄 运行 3 个 Tick 积累数据...")
    for _ in range(3):
        orch._tick()
    print("✅ 数据准备完成\n")

    # 显示状态
    print("━" * 70)
    print("📊 系统状态")
    print("━" * 70)

    state = orch.state

    status = "运行中" if not state.paused else "已暂停"
    print(f"状态: {status}")

    if state.last_stress:
        stress_emoji = {
            "OK": "🟢",
            "WARN": "🟡",
            "DANGER": "🔴",
        }
        emoji = stress_emoji.get(state.last_stress.level, "⚪")
        print(f"市场压力: {emoji} {state.last_stress.level}")

    if state.last_regime:
        print(f"市场状态: {state.last_regime.price_regime} / {state.last_regime.flow_regime}")

    if state.last_features:
        print(f"价格: ${state.last_features.mid:.2f}")
        print(f"价差: {state.last_features.spread_bps:.2f} bps")

    print("━" * 70)

    print("\n✅ 这就是 /status 命令显示的信息！")
    input("\n按回车键继续... ")

    # ========== 命令 2: /pause ==========
    print("\n" + "=" * 70)
    print("命令 2/5: /pause - 暂停交易")
    print("=" * 70)
    print()
    print("💡 作用：暂停交易决策（系统继续监控，但不执行交易）")
    print("💡 何时使用：")
    print("   - 市场波动过大，想先观望")
    print("   - 需要手动调整仓位")
    print("   - 调试或测试时")
    print()
    input("按回车键模拟 /pause 命令... ")

    orch.state.paused = True
    print("\n⏸️  系统已暂停")
    print("\n💡 说明：")
    print("   ✅ 系统继续采集市场数据")
    print("   ✅ 系统继续检测异常")
    print("   ✅ 系统继续生成信号")
    print("   ❌ 但不会执行任何交易（风控自动拒绝）")

    input("\n按回车键继续... ")

    # ========== 命令 3: /resume ==========
    print("\n" + "=" * 70)
    print("命令 3/5: /resume - 恢复交易")
    print("=" * 70)
    print()
    print("💡 作用：恢复正常交易")
    print("💡 何时使用：")
    print("   - 暂停观察后，确认可以继续")
    print("   - 手动调整完成后")
    print()
    input("按回车键模拟 /resume 命令... ")

    orch.state.paused = False
    print("\n▶️  系统已恢复")
    print("\n💡 说明：")
    print("   ✅ 系统恢复正常交易决策")

    input("\n按回车键继续... ")

    # ========== 命令 4: /why ==========
    print("\n" + "=" * 70)
    print("命令 4/5: /why - 显示最后决策解释")
    print("=" * 70)
    print()
    print("💡 作用：查看最后一次风控决策的详细解释")
    print("💡 何时使用：")
    print("   - 想知道为什么交易被拒绝")
    print("   - 想知道为什么仓位被调整")
    print("   - 学习系统的决策逻辑")
    print()
    input("按回车键模拟 /why 命令... ")

    # 运行一个 Tick 产生决策
    print("\n🔄 运行一个 Tick 产生决策...")
    orch._tick()

    if orch.state.last_decision:
        from toxictide.explain.explain import build_explanation

        print("\n━" * 70)
        print("🔍 最后决策")
        print("━" * 70)

        explanation = build_explanation(orch.state.last_decision)
        print(explanation)

        print("\n━" * 70)

        print("\n✅ 这就是 /why 命令显示的解释！")
        print("\n💡 解释包含：")
        print("   - 决策结果（允许/减仓/拒绝）")
        print("   - 详细原因")
        print("   - 市场事实数据")
        print("   - 最终仓位和滑点")

    input("\n按回车键继续... ")

    # ========== 命令 5: /quit ==========
    print("\n" + "=" * 70)
    print("命令 5/5: /quit - 退出系统")
    print("=" * 70)
    print()
    print("💡 作用：优雅关闭系统")
    print("💡 何时使用：")
    print("   - 想停止系统运行")
    print("   - 需要修改配置")
    print("   - 结束今天的交易")
    print()
    print("💡 关闭时会：")
    print("   ✅ 停止主循环")
    print("   ✅ 保存所有审计日志")
    print("   ✅ 清理资源")
    print("   ✅ 显示会话统计")
    print()

    input("按回车键模拟 /quit（不会真的退出）... ")
    print("\n👋 正常情况下系统会在这里关闭...")
    print("（本演示不会真的退出）")

    input("\n按回车键继续... ")

    # ========== 实战练习 ==========
    print("\n" + "=" * 70)
    print("🎯 实战练习：理解不同场景下的决策")
    print("=" * 70)
    print()
    print("现在让我们运行 10 个 Tick，观察不同的决策...")
    print()

    allow_count = 0
    reduction_count = 0
    deny_count = 0

    for i in range(10):
        orch._tick()

        if orch.state.last_decision:
            decision = orch.state.last_decision

            print(f"Tick {i+1:2d}: ", end="")

            if decision.action == "ALLOW":
                print(f"✅ 允许（仓位 ${decision.size_usd:.0f}）")
                allow_count += 1
            elif decision.action == "ALLOW_WITH_REDUCTIONS":
                print(f"⚠️  允许但减仓到 ${decision.size_usd:.0f}")
                if decision.reasons:
                    print(f"        原因: {decision.reasons[0]}")
                reduction_count += 1
            else:
                print(f"❌ 拒绝")
                if decision.reasons:
                    print(f"        原因: {decision.reasons[0]}")
                deny_count += 1

    print()
    print("━" * 70)
    print("📊 决策统计")
    print("━" * 70)
    print(f"允许: {allow_count} 次")
    print(f"减仓: {reduction_count} 次")
    print(f"拒绝: {deny_count} 次")
    print("━" * 70)

    print("\n💡 观察：")
    print("  - 大部分交易被拒绝是正常的！")
    print("  - 原因：没有符合条件的信号（需要 30+ Tick 积累历史）")
    print("  - 风控保护 > 盲目交易")

    input("\n按回车键继续... ")

    # ========== 总结 ==========
    orch._shutdown()

    print("\n" + "=" * 70)
    print("🎉 恭喜！您已完成第 2 步学习")
    print("=" * 70)

    print("""
✅ 您现在掌握了：

1️⃣  /status  - 查看系统状态
   → 市场压力、价格、状态
   → 定期使用，了解系统运行情况

2️⃣  /pause   - 暂停交易
   → 继续监控，停止交易
   → 观望、调试、手动干预

3️⃣  /resume  - 恢复交易
   → 恢复正常决策
   → 确认后继续运行

4️⃣  /why     - 查看决策解释
   → 详细的拒绝/允许原因
   → 学习系统逻辑

5️⃣  /quit    - 优雅退出
   → 保存日志
   → 结束运行

💡 使用技巧：
  - 每 10 分钟查看一次 /status
  - 看到异常时立即 /why
  - 不确定时先 /pause 观察
  - 结束时用 /quit（不要直接关窗口）

📚 下一步学习：
  → 运行 python learn_step3.py
  → 深入理解风控决策的 7 层检查
  → 学习如何调整风控参数

🚀 现在您可以：
  → 运行 python main_quiet.py 体验完整系统
  → 使用学到的命令控制系统
    """)


if __name__ == "__main__":
    main()
