"""
TOXICTIDE Execution Planner 测试
"""

import time

import pytest

from toxictide.execution.planner import ExecutionPlanner
from toxictide.models import (
    FeatureVector,
    RiskDecision,
    TradeCandidate,
    VolumeAnomalyReport,
)


class TestExecutionPlanner:
    """测试 ExecutionPlanner"""

    def setup_method(self):
        """每个测试前初始化"""
        config = {
            "execution": {
                "slicing_threshold_bps": 10.0,
            }
        }
        self.planner = ExecutionPlanner(config)

    def _create_fv(self, impact_buy: float = 5.0) -> FeatureVector:
        """创建特征向量"""
        return FeatureVector(
            ts=time.time(),
            mid=2000.0,
            spread=1.0,
            spread_bps=5.0,
            top_bid_sz=10.0,
            top_ask_sz=10.0,
            depth_bid_k=50000.0,
            depth_ask_k=50000.0,
            imb_k=0.0,
            micro_minus_mid=0.0,
            impact_buy_bps=impact_buy,
            impact_sell_bps=5.0,
            msg_rate=10.0,
            churn=1000.0,
            vol=100.0,
            trades=10,
            avg_trade=10.0,
            max_trade=20.0,
            signed_imb=0.0,
            toxic=0.3,
        )

    def _create_risk_allow(self) -> RiskDecision:
        """创建允许的风控决策"""
        return RiskDecision(
            ts=time.time(),
            action="ALLOW",
            size_usd=1000.0,
            max_slippage_bps=7.5,
            reasons=[],
            facts={},
        )

    def _create_risk_deny(self) -> RiskDecision:
        """创建拒绝的风控决策"""
        return RiskDecision(
            ts=time.time(),
            action="DENY",
            size_usd=0.0,
            max_slippage_bps=0.0,
            reasons=["DAILY_LOSS_EXCEEDED"],
            facts={},
        )

    def _create_candidate(self) -> TradeCandidate:
        """创建交易候选"""
        return TradeCandidate(
            ts=time.time(),
            side="long",
            entry_price=2000.0,
            stop_price=1990.0,
            tp_price=2020.0,
            confidence=0.7,
            ttl_sec=300,
            strategy="trend_breakout",
        )

    def _create_vad(self, toxic: float = 0.3) -> VolumeAnomalyReport:
        """创建 VAD 报告"""
        return VolumeAnomalyReport(
            ts=time.time(),
            level="OK",
            score=0.0,
            triggers={"toxic": toxic},
            events={},
        )

    def test_deny_empty_plan(self):
        """测试风控拒绝返回空计划"""
        risk = self._create_risk_deny()
        candidate = self._create_candidate()
        fv = self._create_fv()
        vad = self._create_vad()

        plan = self.planner.plan(risk, candidate, fv, vad)

        assert plan.mode == "reduce_only"
        assert len(plan.orders) == 0
        assert "DAILY_LOSS_EXCEEDED" in plan.reasons

    def test_no_candidate_empty_plan(self):
        """测试无候选返回空计划"""
        risk = self._create_risk_allow()
        fv = self._create_fv()
        vad = self._create_vad()

        plan = self.planner.plan(risk, None, fv, vad)

        assert plan.mode == "reduce_only"
        assert len(plan.orders) == 0

    def test_normal_maker_mode(self):
        """测试正常 maker 模式"""
        risk = self._create_risk_allow()
        candidate = self._create_candidate()
        fv = self._create_fv(impact_buy=5.0)
        vad = self._create_vad(toxic=0.3)

        plan = self.planner.plan(risk, candidate, fv, vad)

        assert plan.mode == "maker"
        assert len(plan.orders) == 1
        assert plan.orders[0]["type"] == "limit"
        assert plan.orders[0]["side"] == "long"

    def test_high_impact_slicing(self):
        """测试高冲击分片执行"""
        risk = self._create_risk_allow()
        candidate = self._create_candidate()
        fv = self._create_fv(impact_buy=12.0)  # 超过阈值 10
        vad = self._create_vad(toxic=0.3)

        plan = self.planner.plan(risk, candidate, fv, vad)

        assert plan.mode == "slicing"
        assert len(plan.orders) == 5
        assert "HIGH_IMPACT_SLICING" in plan.reasons

    def test_toxic_taker_only(self):
        """测试高毒性 taker only"""
        risk = self._create_risk_allow()
        candidate = self._create_candidate()
        fv = self._create_fv()
        vad = self._create_vad(toxic=0.7)

        plan = self.planner.plan(risk, candidate, fv, vad)

        assert plan.mode == "taker"
        assert len(plan.orders) == 1
        assert plan.orders[0]["type"] == "market"
        assert "TOXIC_TAKER_ONLY" in plan.reasons

    def test_slicing_order_structure(self):
        """测试分片订单结构"""
        risk = self._create_risk_allow()
        candidate = self._create_candidate()
        fv = self._create_fv(impact_buy=15.0)
        vad = self._create_vad()

        plan = self.planner.plan(risk, candidate, fv, vad)

        # 检查每个分片订单
        for i, order in enumerate(plan.orders):
            assert order["type"] == "limit"
            assert order["size_usd"] == pytest.approx(200.0)  # 1000 / 5
            assert order["time_delay_sec"] == i * 10
