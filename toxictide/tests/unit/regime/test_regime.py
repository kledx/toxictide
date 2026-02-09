"""
TOXICTIDE Regime Classifier 测试
"""

import time

import pytest

from toxictide.models import (
    FeatureVector,
    OrderbookAnomalyReport,
    VolumeAnomalyReport,
)
from toxictide.regime.regime import RegimeClassifier


class TestRegimeClassifier:
    """测试 RegimeClassifier"""

    def setup_method(self):
        """每个测试前初始化"""
        self.classifier = RegimeClassifier({})

    def _create_feature(self, mid: float, toxic: float = 0.3) -> FeatureVector:
        """创建特征向量"""
        return FeatureVector(
            ts=time.time(),
            mid=mid,
            spread=1.0,
            spread_bps=5.0,
            top_bid_sz=10.0,
            top_ask_sz=10.0,
            depth_bid_k=50000.0,
            depth_ask_k=50000.0,
            imb_k=0.0,
            micro_minus_mid=0.0,
            impact_buy_bps=5.0,
            impact_sell_bps=5.0,
            msg_rate=10.0,
            churn=1000.0,
            vol=100.0,
            trades=10,
            avg_trade=10.0,
            max_trade=20.0,
            signed_imb=0.0,
            toxic=toxic,
        )

    def _create_oad(self, level: str = "OK") -> OrderbookAnomalyReport:
        """创建 OAD 报告"""
        return OrderbookAnomalyReport(
            ts=time.time(),
            level=level,
            score=0.0,
            triggers={},
            liquidity_state="THICK",
        )

    def _create_vad(self, toxic: float = 0.3, vol_z: float = 0.0) -> VolumeAnomalyReport:
        """创建 VAD 报告"""
        return VolumeAnomalyReport(
            ts=time.time(),
            level="OK",
            score=0.0,
            triggers={"toxic": toxic, "vol_z": vol_z},
            events={},
        )

    def test_initialization(self):
        """测试初始化"""
        assert len(self.classifier._price_history) == 0

    def test_insufficient_data_range(self):
        """测试数据不足时返回 RANGE"""
        fv = self._create_feature(2000.0)
        oad = self._create_oad()
        vad = self._create_vad()
        
        regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.price_regime == "RANGE"
        assert regime.confidence < 0.8

    def test_trend_up_detection(self):
        """测试上升趋势检测"""
        # 添加上升价格序列
        for i in range(50):
            price = 2000.0 + i * 2.0  # 持续上涨
            fv = self._create_feature(price)
            oad = self._create_oad()
            vad = self._create_vad()
            regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.price_regime == "TREND_UP"

    def test_trend_down_detection(self):
        """测试下降趋势检测"""
        # 添加下降价格序列
        for i in range(50):
            price = 2100.0 - i * 2.0  # 持续下跌
            fv = self._create_feature(price)
            oad = self._create_oad()
            vad = self._create_vad()
            regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.price_regime == "TREND_DOWN"

    def test_range_detection(self):
        """测试震荡检测"""
        # 添加震荡价格序列
        for i in range(50):
            price = 2000.0 + (i % 2) * 1.0  # 小幅震荡
            fv = self._create_feature(price)
            oad = self._create_oad()
            vad = self._create_vad()
            regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.price_regime == "RANGE"

    def test_flow_calm(self):
        """测试 CALM 流动性状态"""
        fv = self._create_feature(2000.0, toxic=0.3)
        oad = self._create_oad("OK")
        vad = self._create_vad(toxic=0.3, vol_z=1.0)
        
        regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.flow_regime == "CALM"

    def test_flow_active(self):
        """测试 ACTIVE 流动性状态"""
        fv = self._create_feature(2000.0)
        oad = self._create_oad("WARN")
        vad = self._create_vad()
        
        regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.flow_regime == "ACTIVE"

    def test_flow_toxic_high_toxic(self):
        """测试 TOXIC 状态（高毒性）"""
        fv = self._create_feature(2000.0, toxic=0.7)
        oad = self._create_oad("OK")
        vad = self._create_vad(toxic=0.7)
        
        regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.flow_regime == "TOXIC"

    def test_flow_toxic_oad_danger(self):
        """测试 TOXIC 状态（OAD DANGER）"""
        fv = self._create_feature(2000.0)
        oad = self._create_oad("DANGER")
        vad = self._create_vad()
        
        regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.flow_regime == "TOXIC"

    def test_flow_toxic_high_impact(self):
        """测试 TOXIC 状态（高冲击）"""
        fv = self._create_feature(2000.0)
        fv = FeatureVector(**{**fv.model_dump(), "impact_buy_bps": 25.0})
        oad = self._create_oad()
        vad = self._create_vad()
        
        regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.flow_regime == "TOXIC"

    def test_confidence_increase(self):
        """测试置信度随数据增加"""
        for i in range(60):
            fv = self._create_feature(2000.0)
            oad = self._create_oad()
            vad = self._create_vad()
            regime = self.classifier.classify(fv, oad, vad)
        
        assert regime.confidence >= 0.8

    def test_reset(self):
        """测试重置"""
        for i in range(10):
            fv = self._create_feature(2000.0)
            oad = self._create_oad()
            vad = self._create_vad()
            self.classifier.classify(fv, oad, vad)
        
        self.classifier.reset()
        
        assert len(self.classifier._price_history) == 0
