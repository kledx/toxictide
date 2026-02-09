#!/usr/bin/env python3
"""
TOXICTIDE 学习演示 - 第 4 步

学习如何分析审计日志
"""

import json
from pathlib import Path
from collections import Counter
from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict


def main():
    """第 4 步学习演示"""

    print("=" * 70)
    print("📊 TOXICTIDE 学习演示 - 第 4 步：分析审计日志")
    print("=" * 70)
    print()

    print("📝 这个演示将教您：")
    print("  1. 审计日志的格式和内容")
    print("  2. 如何读取和解析日志")
    print("  3. 如何统计分析决策")
    print("  4. 如何回放历史决策")
    print()
    input("按回车键开始... ")

    # ========== 生成一些审计日志 ==========
    print("\n" + "=" * 70)
    print("准备工作：生成审计日志")
    print("=" * 70)
    print()
    print("运行 30 个 Tick 生成审计日志...")

    config_obj = load_config()
    config = get_config_dict(config_obj)
    orch = Orchestrator(config)

    # 运行 30 个 Tick
    for i in range(30):
        orch._tick()
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i+1}/30 Tick...")

    log_path = orch._ledger.log_path
    orch._shutdown()

    print(f"\n✅ 审计日志已生成: {log_path}")
    print()
    input("按回车键继续... ")

    # ========== 审计日志格式 ==========
    print("\n" + "=" * 70)
    print("1/4: 理解审计日志格式")
    print("=" * 70)
    print()
    print("📝 格式: JSONL (JSON Lines)")
    print("  - 每行一个 JSON 对象")
    print("  - 每个对象是一个完整的决策记录")
    print("  - 可以逐行解析")
    print()
    print("📋 每条记录包含:")
    print("  - ts: 时间戳")
    print("  - policy: 策略配置")
    print("  - features: 19 维特征向量")
    print("  - oad: 盘口异常检测结果")
    print("  - vad: 成交量异常检测结果")
    print("  - stress: 市场压力指数")
    print("  - regime: 市场状态分类")
    print("  - signal: 交易信号（如果有）")
    print("  - risk: 风控决策")
    print("  - plan: 执行计划")
    print("  - fills: 成交记录")
    print("  - explain: 人类可读解释")
    print()

    # 读取第一条记录
    print("让我们看一下第一条记录的结构...")
    print()

    with open(log_path, 'r') as f:
        first_line = f.readline()
        first_record = json.loads(first_line)

    print("记录的顶层字段:")
    for key in first_record.keys():
        print(f"  - {key}")

    print()
    input("按回车键查看详细内容... ")

    # 显示部分内容
    print("\n特征向量 (features) 示例:")
    if 'features' in first_record and first_record['features']:
        fv = first_record['features']
        print(f"  价格: ${fv.get('mid', 0):.2f}")
        print(f"  价差: {fv.get('spread_bps', 0):.2f} bps")
        print(f"  买方冲击: {fv.get('impact_buy_bps', 0):.2f} bps")
        print(f"  卖方冲击: {fv.get('impact_sell_bps', 0):.2f} bps")
        print(f"  毒性流: {fv.get('toxic', 0):.2f}")
        print(f"  成交量: {fv.get('vol', 0):.2f}")

    print("\n风控决策 (risk) 示例:")
    if 'risk' in first_record and first_record['risk']:
        risk = first_record['risk']
        print(f"  决策: {risk.get('action', 'N/A')}")
        print(f"  仓位: ${risk.get('size_usd', 0):.2f}")
        print(f"  原因: {', '.join(risk.get('reasons', []))}")

    print("\n可读解释 (explain) 示例:")
    if 'explain' in first_record:
        print(f"  {first_record['explain']}")

    input("\n按回车键继续... ")

    # ========== 读取和统计分析 ==========
    print("\n" + "=" * 70)
    print("2/4: 统计分析")
    print("=" * 70)
    print()
    print("现在让我们统计分析所有决策记录...")
    print()

    # 读取所有记录
    records = []
    with open(log_path, 'r') as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except:
                pass

    print(f"📊 总记录数: {len(records)}")
    print()

    # 统计决策
    decisions = []
    stress_levels = []
    regimes = []
    signals = []

    for record in records:
        if 'risk' in record and record['risk']:
            decisions.append(record['risk'].get('action', 'UNKNOWN'))

        if 'stress' in record and record['stress']:
            stress_levels.append(record['stress'].get('level', 'UNKNOWN'))

        if 'regime' in record and record['regime']:
            regime = record['regime']
            regimes.append(f"{regime.get('price_regime', 'N/A')}/{regime.get('flow_regime', 'N/A')}")

        if 'signal' in record and record['signal']:
            signals.append(record['signal'].get('strategy', 'unknown'))

    # 显示统计
    print("━" * 70)
    print("📊 决策统计")
    print("━" * 70)

    decision_counts = Counter(decisions)
    for action, count in decision_counts.most_common():
        pct = count / len(decisions) * 100 if decisions else 0
        print(f"  {action}: {count} 次 ({pct:.1f}%)")

    print("\n━" * 70)
    print("🚨 市场压力统计")
    print("━" * 70)

    stress_counts = Counter(stress_levels)
    for level, count in stress_counts.most_common():
        pct = count / len(stress_levels) * 100 if stress_levels else 0
        emoji = {"OK": "🟢", "WARN": "🟡", "DANGER": "🔴"}.get(level, "⚪")
        print(f"  {emoji} {level}: {count} 次 ({pct:.1f}%)")

    print("\n━" * 70)
    print("🌍 市场状态统计")
    print("━" * 70)

    regime_counts = Counter(regimes)
    for regime, count in regime_counts.most_common(5):
        pct = count / len(regimes) * 100 if regimes else 0
        print(f"  {regime}: {count} 次 ({pct:.1f}%)")

    print("\n━" * 70)
    print("💡 信号统计")
    print("━" * 70)

    signal_counts = Counter(signals)
    if signal_counts:
        for strategy, count in signal_counts.most_common():
            print(f"  {strategy}: {count} 次")
    else:
        print("  无信号生成")

    print("\n💡 分析：")
    print("  - 大部分决策是 DENY（拒绝）是正常的")
    print("  - 原因：需要 30+ Tick 积累历史数据才能生成信号")
    print("  - 系统倾向于观望，而不是盲目交易")

    input("\n按回车键继续... ")

    # ========== 拒绝原因分析 ==========
    print("\n" + "=" * 70)
    print("3/4: 拒绝原因分析")
    print("=" * 70)
    print()
    print("让我们分析为什么交易被拒绝...")
    print()

    # 统计拒绝原因
    deny_reasons = []
    for record in records:
        if 'risk' in record and record['risk']:
            if record['risk'].get('action') == 'DENY':
                reasons = record['risk'].get('reasons', [])
                deny_reasons.extend(reasons)

    print("━" * 70)
    print("❌ 拒绝原因统计")
    print("━" * 70)

    reason_counts = Counter(deny_reasons)
    for reason, count in reason_counts.most_common():
        pct = count / len(deny_reasons) * 100 if deny_reasons else 0
        print(f"  {reason}: {count} 次 ({pct:.1f}%)")

    print("\n💡 常见拒绝原因解释:")
    print("  - NO_SIGNAL: 无交易信号（最常见，正常现象）")
    print("  - DATA_STALE: 数据过期（网络问题）")
    print("  - DAILY_LOSS_EXCEEDED: 日亏超限（风控保护）")
    print("  - IMPACT_HARD_CAP_EXCEEDED: 冲击成本过高")
    print("  - MARKET_STRESS_DANGER: 市场异常严重")

    input("\n按回车键继续... ")

    # ========== 回放决策 ==========
    print("\n" + "=" * 70)
    print("4/4: 回放历史决策")
    print("=" * 70)
    print()
    print("让我们回放几个有代表性的决策...")
    print()

    # 找出不同类型的决策
    allow_records = []
    reduction_records = []
    deny_records = []

    for record in records:
        if 'risk' in record and record['risk']:
            action = record['risk'].get('action')
            if action == 'ALLOW':
                allow_records.append(record)
            elif action == 'ALLOW_WITH_REDUCTIONS':
                reduction_records.append(record)
            elif action == 'DENY':
                deny_records.append(record)

    # 回放示例
    print("━" * 70)
    print("示例 1: DENY（拒绝）决策")
    print("━" * 70)

    if deny_records:
        record = deny_records[0]
        print(f"\n时间戳: {record.get('ts', 0):.2f}")

        if 'features' in record and record['features']:
            fv = record['features']
            print(f"价格: ${fv.get('mid', 0):.2f}")
            print(f"市场压力: {record.get('stress', {}).get('level', 'N/A')}")
            print(f"市场状态: {record.get('regime', {}).get('price_regime', 'N/A')}")

        if 'risk' in record and record['risk']:
            risk = record['risk']
            print(f"\n决策: {risk.get('action')}")
            print(f"原因: {', '.join(risk.get('reasons', []))}")

        if 'explain' in record:
            print(f"\n解释:\n{record['explain']}")

    if reduction_records:
        print("\n" + "━" * 70)
        print("示例 2: ALLOW_WITH_REDUCTIONS（减仓）决策")
        print("━" * 70)

        record = reduction_records[0]
        print(f"\n时间戳: {record.get('ts', 0):.2f}")

        if 'features' in record and record['features']:
            fv = record['features']
            print(f"价格: ${fv.get('mid', 0):.2f}")
            print(f"买方冲击: {fv.get('impact_buy_bps', 0):.2f} bps")
            print(f"毒性流: {fv.get('toxic', 0):.2f}")

        if 'risk' in record and record['risk']:
            risk = record['risk']
            print(f"\n决策: {risk.get('action')}")
            print(f"最终仓位: ${risk.get('size_usd', 0):.2f}")
            print(f"原因: {', '.join(risk.get('reasons', []))}")

        if 'explain' in record:
            print(f"\n解释:\n{record['explain']}")

    input("\n按回车键继续... ")

    # ========== 导出工具函数 ==========
    print("\n" + "=" * 70)
    print("💡 实用工具函数")
    print("=" * 70)
    print()
    print("我为您准备了一个分析脚本模板...")
    print()

    analyze_script = """# analyze_log.py - 审计日志分析工具

import json
from collections import Counter
from pathlib import Path

def analyze_log(log_file):
    '''分析审计日志'''

    # 读取所有记录
    records = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except:
                pass

    print(f"总记录数: {len(records)}")
    print()

    # 统计决策
    decisions = [r['risk']['action'] for r in records
                 if 'risk' in r and r['risk']]

    print("决策统计:")
    for action, count in Counter(decisions).most_common():
        pct = count / len(decisions) * 100
        print(f"  {action}: {count} ({pct:.1f}%)")

    # 统计拒绝原因
    deny_reasons = []
    for r in records:
        if r.get('risk', {}).get('action') == 'DENY':
            deny_reasons.extend(r['risk'].get('reasons', []))

    print("\\n拒绝原因:")
    for reason, count in Counter(deny_reasons).most_common():
        pct = count / len(deny_reasons) * 100
        print(f"  {reason}: {count} ({pct:.1f}%)")

# 使用示例
if __name__ == "__main__":
    analyze_log("logs/session_20260208.jsonl")
"""

    print(analyze_script)

    input("\n按回车键继续... ")

    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print("🎉 恭喜！您已完成第 4 步学习")
    print("=" * 70)

    print(f"""
✅ 您现在掌握了：

📊 审计日志格式：
   - JSONL 格式（每行一个 JSON）
   - 完整的决策快照
   - 包含所有输入和输出

📈 统计分析：
   - 决策分布（允许/减仓/拒绝）
   - 市场压力分布
   - 市场状态分布
   - 信号生成统计

🔍 拒绝原因分析：
   - 统计最常见的拒绝原因
   - 理解每个原因的含义
   - 判断是否需要调整参数

🎬 决策回放：
   - 重现历史决策过程
   - 分析决策是否合理
   - 学习系统逻辑

💻 分析工具：
   - 可以自己编写分析脚本
   - 导出统计报告
   - 可视化分析（可扩展）

📚 下一步学习：
  → 运行 python learn_step5.py
  → 完整实战演练
  → 综合运用所有知识
  → 为接入真实数据做准备

🚀 现在您可以：
  → 分析自己的审计日志
  → 统计交易效果
  → 优化系统参数
  → 编写自定义分析工具

审计日志位置: {log_path}
    """)


if __name__ == "__main__":
    main()
