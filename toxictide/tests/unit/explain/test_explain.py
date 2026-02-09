"""
TOXICTIDE Explain 测试
"""

import time

import pytest

from toxictide.explain.explain import (
    build_explanation,
    build_summary,
)
from toxictide.models import RiskDecision
from toxictide.risk.reason_codes import (
    DAILY_LOSS_EXCEEDED,
    IMPACT_ENTRY_CAP_EXCEEDED,
    NO_SIGNAL,
    RISK_POSITION_SIZE_REDUCED,
)


class TestExplain:
    """测试 Explain"""

    def test_build_explanation_deny(self):
        """测试拒绝解释"""
        risk = RiskDecision(
            ts=time.time(),
            action="DENY",
            size_usd=0.0,
            max_slippage_bps=0.0,
            reasons=[DAILY_LOSS_EXCEEDED, NO_SIGNAL],
            facts={
                "daily_pnl_pct": -1.5,
                "max_daily_loss_pct": 1.0,
            },
        )

        explanation = build_explanation(risk)

        assert "❌" in explanation
        assert "拒绝" in explanation
        assert "-1.50%" in explanation

    def test_build_explanation_allow_with_reductions(self):
        """测试减仓解释"""
        risk = RiskDecision(
            ts=time.time(),
            action="ALLOW_WITH_REDUCTIONS",
            size_usd=500.0,
            max_slippage_bps=7.5,
            reasons=[IMPACT_ENTRY_CAP_EXCEEDED, RISK_POSITION_SIZE_REDUCED],
            facts={
                "impact_bps": 12.0,
                "entry_cap_bps": 10.0,
                "original_size": 1000.0,
                "reduced_size": 500.0,
            },
        )

        explanation = build_explanation(risk)

        assert "⚠️" in explanation
        assert "调整" in explanation
        assert "$500.00" in explanation
        assert "7.50 bps" in explanation

    def test_build_explanation_allow(self):
        """测试允许解释"""
        risk = RiskDecision(
            ts=time.time(),
            action="ALLOW",
            size_usd=1000.0,
            max_slippage_bps=5.0,
            reasons=[],
            facts={},
        )

        explanation = build_explanation(risk)

        assert "✅" in explanation
        assert "允许" in explanation
        assert "$1000.00" in explanation
        assert "5.00 bps" in explanation

    def test_build_summary(self):
        """测试会话摘要"""
        summary = build_summary(
            signal_count=100,
            allow_count=60,
            reduction_count=20,
            deny_count=20,
        )

        assert "📊" in summary
        assert "100" in summary
        assert "60.0%" in summary
        assert "20.0%" in summary

    def test_build_summary_no_decisions(self):
        """测试无决策摘要"""
        summary = build_summary(
            signal_count=0,
            allow_count=0,
            reduction_count=0,
            deny_count=0,
        )

        assert "无决策" in summary
