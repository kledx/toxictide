#!/usr/bin/env python3
"""
TOXICTIDE 学习演示 - 第 1 步

这是一个最简单的演示，帮助您理解系统的基本流程
"""

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def main():
    """第 1 步学习演示"""

    print("=" * 70)
    print("🎓 TOXICTIDE 学习演示 - 第 1 步：理解系统如何运行")
    print("=" * 70)
    print()

    print("📝 这个演示将展示：")
    print("  1. 系统如何初始化")
    print("  2. 系统如何运行 Tick")
    print("  3. 每个 Tick 经历了哪些步骤")
    print("  4. 最终产生什么结果")
    print()
    input("按回车键开始... ")

    # ========== 初始化 ==========
    print("\n" + "=" * 70)
    print("步骤 1/4: 初始化系统")
    print("=" * 70)

    print("\n正在加载配置...")
    config_obj = load_config()
    config = get_config_dict(config_obj)
    print("✅ 配置加载完成")

    print("\n正在初始化系统组件...")
    print("  - 市场数据采集器（模拟模式）")
    print("  - 盘口维护器")
    print("  - 成交带")
    print("  - 特征引擎（19 维特征）")
    print("  - 异常检测器（OAD + VAD）")
    print("  - 市场状态分类器")
    print("  - 策略信号引擎")
    print("  - 风控守护（7 层检查）")
    print("  - 执行规划器")
    print("  - 执行适配器（模拟模式）")
    print("  - 审计日志")

    orch = Orchestrator(config)
    print("✅ 系统初始化完成")

    input("\n按回车键继续... ")

    # ========== 运行 Tick ==========
    print("\n" + "=" * 70)
    print("步骤 2/4: 运行第一个 Tick")
    print("=" * 70)
    print()
    print("现在系统将运行一个 Tick，您将看到每个步骤的详细过程...")
    print()
    input("按回车键运行 Tick... ")

    print("\n🔄 Tick 开始...")
    print()

    # 运行一个 Tick
    orch._tick()

    print("✅ Tick 完成！")

    # ========== 展示结果 ==========
    print("\n" + "=" * 70)
    print("步骤 3/4: 查看 Tick 结果")
    print("=" * 70)

    # 市场特征
    if orch.state.last_features:
        fv = orch.state.last_features
        print("\n📊 市场特征（19 维特征向量）：")
        print(f"  价格: ${fv.mid:.2f}")
        print(f"  价差: {fv.spread_bps:.2f} bps")
        print(f"  买方深度: ${fv.depth_bid_k:.0f}")
        print(f"  卖方深度: ${fv.depth_ask_k:.0f}")
        print(f"  深度不平衡: {fv.imb_k:.2f}")
        print(f"  买方冲击: {fv.impact_buy_bps:.2f} bps")
        print(f"  卖方冲击: {fv.impact_sell_bps:.2f} bps")
        print(f"  成交量: {fv.vol:.2f}")
        print(f"  毒性流: {fv.toxic:.2f}")

    # 市场压力
    if orch.state.last_stress:
        stress = orch.state.last_stress
        print(f"\n🚨 市场压力：{stress.level}")
        print(f"  压力分数: {stress.score:.2f}")

        if stress.level == "OK":
            print("  📌 解释: 市场状态正常，无明显异常")
        elif stress.level == "WARN":
            print("  📌 解释: 检测到市场异常，需要警惕")
        else:
            print("  📌 解释: 市场异常严重，高风险状态")

    # 市场状态
    if orch.state.last_regime:
        regime = orch.state.last_regime
        print(f"\n🌍 市场状态：")
        print(f"  价格状态: {regime.price_regime}")

        if regime.price_regime == "TREND_UP":
            print("    → 上升趋势")
        elif regime.price_regime == "TREND_DOWN":
            print("    → 下降趋势")
        else:
            print("    → 震荡市场")

        print(f"  波动率状态: {regime.vol_regime}")
        print(f"  流动性状态: {regime.flow_regime}")

    # 风控决策
    if orch.state.last_decision:
        decision = orch.state.last_decision
        print(f"\n🛡️ 风控决策：{decision.action}")

        if decision.action == "DENY":
            print("  ❌ 交易被拒绝")
        elif decision.action == "ALLOW_WITH_REDUCTIONS":
            print(f"  ⚠️  交易允许但减仓到 ${decision.size_usd:.2f}")
        else:
            print(f"  ✅ 交易允许，仓位 ${decision.size_usd:.2f}")

        if decision.reasons:
            print("  原因:")
            for reason in decision.reasons:
                print(f"    - {reason}")

    input("\n按回车键继续... ")

    # ========== 解释流程 ==========
    print("\n" + "=" * 70)
    print("步骤 4/4: 理解 Tick 的完整流程")
    print("=" * 70)

    print("""
一个 Tick 经历了以下 10 个步骤：

1️⃣  【采集数据】
   → 获取盘口快照（20 档 bids/asks）
   → 获取最新成交

2️⃣  【计算特征】
   → 从盘口和成交计算 19 维特征向量
   → 包括：价格、价差、深度、冲击、成交量、毒性流等

3️⃣  【异常检测】
   → OAD：检测盘口异常（价差飙升、流动性断层等）
   → VAD：检测成交量异常（爆发、干涸、鲸鱼交易等）
   → Stress：综合压力指数（OK/WARN/DANGER）

4️⃣  【状态分类】
   → 价格状态：趋势/震荡
   → 波动率状态：高/正常/低
   → 流动性状态：毒性/活跃/平静

5️⃣  【信号生成】
   → 根据市场状态选择策略
   → 趋势突破策略：突破近期高低点
   → 均值回归策略：偏离均值 > 1.5σ

6️⃣  【风控评估】
   → 7 层优先级检查：
     1. 数据质量
     2. 日亏熔断
     3. 冷却期
     4. 仓位上限
     5. Impact/Toxic 检查
     6. 市场压力
     7. 交易频率

7️⃣  【执行规划】
   → 高冲击：自动分片（5 个子订单）
   → 高毒性：使用 taker 模式
   → 正常：使用 maker 模式

8️⃣  【执行订单】
   → Paper Mode：模拟成交
   → Real Mode：真实下单（需要实现）

9️⃣  【审计记录】
   → 记录完整决策过程到 JSONL 日志
   → 包括：特征、异常、状态、信号、风控、执行

🔟 【日志输出】
   → 输出结构化日志（JSON 格式）
   → 便于监控和调试
""")

    input("按回车键继续... ")

    # ========== 运行多个 Tick ==========
    print("\n" + "=" * 70)
    print("🎯 现在让系统连续运行 5 个 Tick，观察状态变化")
    print("=" * 70)
    print()

    for i in range(5):
        print(f"\n{'='*70}")
        print(f"Tick {i+1}/5")
        print('='*70)

        orch._tick()

        if orch.state.last_features and orch.state.last_decision:
            fv = orch.state.last_features
            stress = orch.state.last_stress
            regime = orch.state.last_regime
            decision = orch.state.last_decision

            print(f"价格: ${fv.mid:.2f} | 压力: {stress.level if stress else 'N/A'} | " +
                  f"状态: {regime.price_regime if regime else 'N/A'} | " +
                  f"决策: {decision.action}")

    # ========== 总结 ==========
    orch._shutdown()

    print("\n" + "=" * 70)
    print("🎉 恭喜！您已完成第 1 步学习")
    print("=" * 70)

    print("""
✅ 您现在理解了：
  1. 系统如何初始化 11 个核心组件
  2. 每个 Tick 经历的 10 个步骤
  3. 系统如何从市场数据到最终决策
  4. 每个步骤产生什么结果

📚 下一步学习：
  → 运行 python learn_step2.py
  → 学习如何使用交互命令
  → 深入理解风控决策逻辑

审计日志已保存到: """ + str(orch._ledger.log_path) + """
    """)


if __name__ == "__main__":
    main()
