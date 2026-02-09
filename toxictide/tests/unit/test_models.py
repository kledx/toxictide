"""
TOXICTIDE 数据模型测试
"""

import pytest
from pydantic import ValidationError

from toxictide.models import (
    OrderBookLevel,
    OrderBookState,
    Trade,
    FeatureVector,
    OrderbookAnomalyReport,
    VolumeAnomalyReport,
    MarketStressIndex,
    RegimeState,
    TradeCandidate,
    RiskDecision,
    ExecutionPlan,
    Fill,
    LedgerRecord,
)


class TestOrderBookLevel:
    """测试 OrderBookLevel 模型"""

    def test_valid_level(self):
        """测试有效的价位"""
        level = OrderBookLevel(price=100.5, size=10.0)
        assert level.price == 100.5
        assert level.size == 10.0

    def test_price_must_be_positive(self):
        """测试价格必须为正"""
        with pytest.raises(ValidationError):
            OrderBookLevel(price=0, size=10.0)

        with pytest.raises(ValidationError):
            OrderBookLevel(price=-1, size=10.0)

    def test_size_must_be_positive(self):
        """测试数量必须为正"""
        with pytest.raises(ValidationError):
            OrderBookLevel(price=100, size=0)

        with pytest.raises(ValidationError):
            OrderBookLevel(price=100, size=-1)

    def test_frozen(self):
        """测试模型不可变"""
        level = OrderBookLevel(price=100, size=10)
        with pytest.raises(ValidationError):
            level.price = 200


class TestOrderBookState:
    """测试 OrderBookState 模型"""

    def test_valid_orderbook(self):
        """测试有效的订单簿"""
        bids = [
            OrderBookLevel(price=100, size=10),
            OrderBookLevel(price=99, size=20),
        ]
        asks = [
            OrderBookLevel(price=101, size=15),
            OrderBookLevel(price=102, size=25),
        ]

        state = OrderBookState(ts=1234567890.0, bids=bids, asks=asks, seq=1)

        assert state.mid == 100.5
        assert state.spread == 1.0
        assert state.spread_bps == pytest.approx(99.5, rel=0.01)

    def test_bids_must_be_descending(self):
        """测试买盘必须降序"""
        bids = [
            OrderBookLevel(price=99, size=10),  # 错误：应该更高
            OrderBookLevel(price=100, size=20),
        ]
        asks = [
            OrderBookLevel(price=101, size=15),
        ]

        with pytest.raises(ValidationError, match="descending"):
            OrderBookState(ts=1234567890.0, bids=bids, asks=asks, seq=1)

    def test_asks_must_be_ascending(self):
        """测试卖盘必须升序"""
        bids = [
            OrderBookLevel(price=100, size=10),
        ]
        asks = [
            OrderBookLevel(price=102, size=15),  # 错误：应该更低
            OrderBookLevel(price=101, size=25),
        ]

        with pytest.raises(ValidationError, match="ascending"):
            OrderBookState(ts=1234567890.0, bids=bids, asks=asks, seq=1)

    def test_spread_must_be_positive(self):
        """测试 spread 必须为正"""
        bids = [OrderBookLevel(price=101, size=10)]
        asks = [OrderBookLevel(price=100, size=15)]  # 错误：ask < bid

        with pytest.raises(ValidationError, match="Negative spread"):
            OrderBookState(ts=1234567890.0, bids=bids, asks=asks, seq=1)

    def test_empty_bids_asks(self):
        """测试空的买卖盘"""
        state = OrderBookState(ts=1234567890.0, bids=[], asks=[], seq=0)
        assert state.mid == 0.0
        assert state.spread == 0.0


class TestTrade:
    """测试 Trade 模型"""

    def test_valid_trade(self):
        """测试有效的交易"""
        trade = Trade(ts=1234567890.0, price=100.0, size=5.0, side="buy")
        assert trade.price == 100.0
        assert trade.side == "buy"

    def test_side_must_be_valid(self):
        """测试 side 必须是有效值"""
        with pytest.raises(ValidationError):
            Trade(ts=1234567890.0, price=100.0, size=5.0, side="invalid")

    def test_all_valid_sides(self):
        """测试所有有效的 side 值"""
        for side in ["buy", "sell", "unknown"]:
            trade = Trade(ts=1234567890.0, price=100.0, size=5.0, side=side)
            assert trade.side == side


class TestFeatureVector:
    """测试 FeatureVector 模型"""

    def test_valid_feature_vector(self):
        """测试有效的特征向量"""
        fv = FeatureVector(
            ts=1234567890.0,
            mid=100.0,
            spread=0.5,
            spread_bps=50.0,
            top_bid_sz=10.0,
            top_ask_sz=15.0,
            depth_bid_k=50000.0,
            depth_ask_k=60000.0,
            imb_k=0.1,
            micro_minus_mid=0.01,
            impact_buy_bps=5.0,
            impact_sell_bps=4.5,
            msg_rate=100.0,
            churn=500.0,
            vol=1000.0,
            trades=50,
            avg_trade=20.0,
            max_trade=100.0,
            signed_imb=0.2,
            toxic=0.3,
        )

        assert fv.mid == 100.0
        assert fv.toxic == 0.3

    def test_imb_k_range(self):
        """测试 imb_k 范围 [-1, 1]"""
        with pytest.raises(ValidationError):
            FeatureVector(
                ts=1.0, mid=100.0, spread=0.5, spread_bps=50.0,
                top_bid_sz=10.0, top_ask_sz=15.0,
                depth_bid_k=50000.0, depth_ask_k=60000.0,
                imb_k=1.5,  # 超出范围
                micro_minus_mid=0.01,
                impact_buy_bps=5.0, impact_sell_bps=4.5,
                msg_rate=100.0, churn=500.0,
                vol=1000.0, trades=50, avg_trade=20.0, max_trade=100.0,
                signed_imb=0.2, toxic=0.3,
            )

    def test_toxic_range(self):
        """测试 toxic 范围 [0, 1]"""
        with pytest.raises(ValidationError):
            FeatureVector(
                ts=1.0, mid=100.0, spread=0.5, spread_bps=50.0,
                top_bid_sz=10.0, top_ask_sz=15.0,
                depth_bid_k=50000.0, depth_ask_k=60000.0,
                imb_k=0.1, micro_minus_mid=0.01,
                impact_buy_bps=5.0, impact_sell_bps=4.5,
                msg_rate=100.0, churn=500.0,
                vol=1000.0, trades=50, avg_trade=20.0, max_trade=100.0,
                signed_imb=0.2,
                toxic=1.5,  # 超出范围
            )


class TestAnomalyReports:
    """测试异常报告模型"""

    def test_orderbook_anomaly_report(self):
        """测试盘口异常报告"""
        report = OrderbookAnomalyReport(
            ts=1234567890.0,
            level="WARN",
            score=5.5,
            triggers={"spread_z": 4.5, "impact_z": 3.2},
            liquidity_state="THIN",
        )
        assert report.level == "WARN"
        assert report.liquidity_state == "THIN"

    def test_volume_anomaly_report(self):
        """测试成交量异常报告"""
        report = VolumeAnomalyReport(
            ts=1234567890.0,
            level="DANGER",
            score=7.0,
            triggers={"vol_z": 6.5, "toxic": 0.8},
            events={"burst": True, "drought": False, "whale": True},
        )
        assert report.level == "DANGER"
        assert report.events["burst"] is True

    def test_market_stress_index(self):
        """测试市场压力指数"""
        stress = MarketStressIndex(
            ts=1234567890.0,
            level="OK",
            score=2.5,
            components={"oad_score": 1.5, "vad_score": 1.0},
        )
        assert stress.level == "OK"


class TestRiskDecision:
    """测试风控决策模型"""

    def test_allow_decision(self):
        """测试允许决策"""
        decision = RiskDecision(
            ts=1234567890.0,
            action="ALLOW",
            size_usd=1000.0,
            max_slippage_bps=5.0,
            reasons=[],
            facts={"impact_bps": 3.5},
        )
        assert decision.action == "ALLOW"
        assert decision.size_usd == 1000.0

    def test_deny_decision(self):
        """测试拒绝决策"""
        decision = RiskDecision(
            ts=1234567890.0,
            action="DENY",
            size_usd=0.0,
            max_slippage_bps=0.0,
            reasons=["DAILY_LOSS_EXCEEDED", "TOXIC_DANGER_LEVEL"],
            facts={"daily_pnl_pct": -2.5, "toxic": 0.85},
        )
        assert decision.action == "DENY"
        assert len(decision.reasons) == 2

    def test_allow_with_reductions(self):
        """测试带减仓的允许决策"""
        decision = RiskDecision(
            ts=1234567890.0,
            action="ALLOW_WITH_REDUCTIONS",
            size_usd=500.0,
            max_slippage_bps=10.0,
            reasons=["RISK_POSITION_SIZE_REDUCED"],
            facts={"original_size": 1000.0, "reduced_size": 500.0},
        )
        assert decision.action == "ALLOW_WITH_REDUCTIONS"


class TestFill:
    """测试成交回执模型"""

    def test_valid_fill(self):
        """测试有效的成交回执"""
        fill = Fill(
            ts=1234567890.0,
            order_id="order_123",
            price=100.5,
            size=10.0,
            fee=0.05,
            side="buy",
        )
        assert fill.order_id == "order_123"
        assert fill.fee == 0.05


class TestLedgerRecord:
    """测试审计日志模型"""

    def test_valid_ledger_record(self):
        """测试有效的审计日志记录"""
        # 创建所有必要的子模型
        features = FeatureVector(
            ts=1.0, mid=100.0, spread=0.5, spread_bps=50.0,
            top_bid_sz=10.0, top_ask_sz=15.0,
            depth_bid_k=50000.0, depth_ask_k=60000.0,
            imb_k=0.1, micro_minus_mid=0.01,
            impact_buy_bps=5.0, impact_sell_bps=4.5,
            msg_rate=100.0, churn=500.0,
            vol=1000.0, trades=50, avg_trade=20.0, max_trade=100.0,
            signed_imb=0.2, toxic=0.3,
        )

        oad = OrderbookAnomalyReport(
            ts=1.0, level="OK", score=1.0,
            triggers={}, liquidity_state="THICK",
        )

        vad = VolumeAnomalyReport(
            ts=1.0, level="OK", score=1.0,
            triggers={}, events={"burst": False, "drought": False, "whale": False},
        )

        stress = MarketStressIndex(
            ts=1.0, level="OK", score=1.0, components={},
        )

        regime = RegimeState(
            ts=1.0, price_regime="RANGE",
            vol_regime="NORMALVOL", flow_regime="CALM",
            confidence=0.8,
        )

        risk = RiskDecision(
            ts=1.0, action="DENY", size_usd=0.0,
            max_slippage_bps=0.0, reasons=["NO_SIGNAL"], facts={},
        )

        plan = ExecutionPlan(
            ts=1.0, orders=[], mode="reduce_only", reasons=["NO_SIGNAL"],
        )

        record = LedgerRecord(
            ts=1.0,
            policy={"max_daily_loss_pct": 1.0},
            features=features,
            oad=oad,
            vad=vad,
            stress=stress,
            regime=regime,
            signal=None,
            risk=risk,
            plan=plan,
            fills=[],
            explain="No signal generated",
        )

        assert record.ts == 1.0
        assert record.signal is None
        assert len(record.fills) == 0
