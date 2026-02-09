"""
TOXICTIDE Explainability

可解释性模块 - 生成人类可读的决策解释
"""

import structlog

from toxictide.models import RiskDecision
from toxictide.risk.reason_codes import format_reason

logger = structlog.get_logger(__name__)


def build_explanation(risk: RiskDecision) -> str:
    """构建人类可读的决策解释

    根据 RiskDecision 生成清晰的文本说明，用于：
    - UI 显示
    - 日志记录
    - 用户反馈

    Args:
        risk: RiskDecision 对象

    Returns:
        多行格式化的解释文本

    Example:
        >>> explanation = build_explanation(risk_decision)
        >>> print(explanation)
        ❌ 交易被拒绝，原因：
          - 日亏超限（当前 -1.50% < 阈值 -1.00%）
          - 冷却期激活（剩余 120 秒）
    """
    if risk.action == "DENY":
        return _build_deny_explanation(risk)
    elif risk.action == "ALLOW_WITH_REDUCTIONS":
        return _build_reduction_explanation(risk)
    else:  # ALLOW
        return _build_allow_explanation(risk)


def _build_deny_explanation(risk: RiskDecision) -> str:
    """构建拒绝解释

    Args:
        risk: RiskDecision 对象

    Returns:
        解释文本
    """
    lines = ["❌ 交易被拒绝，原因："]

    for code in risk.reasons:
        reason_text = format_reason(code, risk.facts)
        lines.append(f"  - {reason_text}")

    return "\n".join(lines)


def _build_reduction_explanation(risk: RiskDecision) -> str:
    """构建减仓解释

    Args:
        risk: RiskDecision 对象

    Returns:
        解释文本
    """
    lines = ["⚠️  交易允许，但已调整仓位："]

    for code in risk.reasons:
        reason_text = format_reason(code, risk.facts)
        lines.append(f"  - {reason_text}")

    lines.append("")

    # 安全格式化数字字段
    try:
        size = float(risk.size_usd)
        slippage = float(risk.max_slippage_bps)
        lines.append(f"最终仓位: ${size:.2f}")
        lines.append(f"最大滑点: {slippage:.2f} bps")
    except (ValueError, TypeError):
        lines.append(f"最终仓位: ${risk.size_usd}")
        lines.append(f"最大滑点: {risk.max_slippage_bps} bps")

    return "\n".join(lines)


def _build_allow_explanation(risk: RiskDecision) -> str:
    """构建允许解释

    Args:
        risk: RiskDecision 对象

    Returns:
        解释文本
    """
    lines = ["✅ 交易允许"]

    # 安全格式化数字字段
    try:
        size = float(risk.size_usd)
        slippage = float(risk.max_slippage_bps)
        lines.append(f"仓位: ${size:.2f}")
        lines.append(f"最大滑点: {slippage:.2f} bps")
    except (ValueError, TypeError):
        lines.append(f"仓位: ${risk.size_usd}")
        lines.append(f"最大滑点: {risk.max_slippage_bps} bps")

    return "\n".join(lines)


def build_summary(
    signal_count: int,
    allow_count: int,
    reduction_count: int,
    deny_count: int,
) -> str:
    """构建会话摘要

    Args:
        signal_count: 信号总数
        allow_count: 允许次数
        reduction_count: 减仓次数
        deny_count: 拒绝次数

    Returns:
        摘要文本

    Example:
        >>> summary = build_summary(100, 60, 20, 20)
        >>> print(summary)
        📊 会话摘要
        - 信号总数: 100
        - 允许: 60 (60.0%)
        - 减仓: 20 (20.0%)
        - 拒绝: 20 (20.0%)
    """
    total = allow_count + reduction_count + deny_count

    lines = ["📊 会话摘要"]
    lines.append(f"- 信号总数: {signal_count}")

    if total > 0:
        lines.append(f"- 允许: {allow_count} ({allow_count/total*100:.1f}%)")
        lines.append(f"- 减仓: {reduction_count} ({reduction_count/total*100:.1f}%)")
        lines.append(f"- 拒绝: {deny_count} ({deny_count/total*100:.1f}%)")
    else:
        lines.append("- 无决策记录")

    return "\n".join(lines)
