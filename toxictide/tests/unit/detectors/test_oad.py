"""
TOXICTIDE OAD 测试
"""

import time

import pytest

from toxictide.detectors.oad import OrderbookAnomalyDetector
from toxictide.models import FeatureVector


class TestOrderbookAnomalyDetector:
    """测试 OrderbookAnomalyDetector"""

    def setup_method(self):
        """每个测试前初始化"""
        config = {
            "oad": {
                "z_warn": 4.0,
                "z_danger": 6.0,
            }
        }
        self.oad = OrderbookAnomalyDetector(config)

    def _create_normal_features(self, ts: float = None) -> FeatureVector:
        """创建正常特征"""
        if ts is None:
            ts = time.time()
        
        return FeatureVector(
            ts=ts,
            mid=2000.0,
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
            toxic=0.3,
        )

    def test_initialization(self):
        """测试初始化"""
        assert self.oad._z_warn == 4.0
        assert self.oad._z_danger == 6.0

    def test_normal_state(self):
        """测试正常状态"""
        # 添加一些正常数据点
        ts = time.time()
        for i in range(20):
            fv = self._create_normal_features(ts + i)
            report = self.oad.detect(fv)
        
        # 应该是 OK 状态
        assert report.level == "OK"
        assert report.liquidity_state in ["THICK", "THIN"]

    def test_spread_spike(self):
        """测试价差异常"""
        ts = time.time()
        
        # 添加正常数据
        for i in range(20):
            fv = self._create_normal_features(ts + i)
            self.oad.detect(fv)
        
        # 添加异常价差
        fv_anomaly = self._create_normal_features(ts + 20)
        fv_anomaly = FeatureVector(
            **{**fv_anomaly.model_dump(), "spread_bps": 50.0}
        )
        
        report = self.oad.detect(fv_anomaly)
        
        # 应该检测到异常
        assert report.level in ["WARN", "DANGER"]
        assert report.triggers["spread_z"] > 4.0

    def test_impact_spike(self):
        """测试冲击异常"""
        ts = time.time()
        
        for i in range(20):
            fv = self._create_normal_features(ts + i)
            self.oad.detect(fv)
        
        # 添加高 impact
        fv_anomaly = self._create_normal_features(ts + 20)
        fv_anomaly = FeatureVector(
            **{**fv_anomaly.model_dump(), "impact_buy_bps": 100.0}
        )
        
        report = self.oad.detect(fv_anomaly)
        
        assert report.level in ["WARN", "DANGER"]
        assert report.triggers["impact_buy_z"] > 4.0

    def test_liquidity_gap(self):
        """测试流动性断层"""
        ts = time.time()
        
        # 添加正常深度
        for i in range(30):
            fv = self._create_normal_features(ts + i)
            self.oad.detect(fv)
        
        # 深度突然减半
        fv_gap = self._create_normal_features(ts + 30)
        fv_gap = FeatureVector(
            **{**fv_gap.model_dump(), "depth_bid_k": 10000.0}  # 从 50000 降到 10000
        )
        
        report = self.oad.detect(fv_gap)
        
        # 应该检测到 gap
        assert report.triggers["gap_flag"] == 1.0
        assert report.level == "DANGER"

    def test_liquidity_state_thick(self):
        """测试 THICK 流动性状态"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        fv = FeatureVector(
            **{**fv.model_dump(), "impact_buy_bps": 3.0, "impact_sell_bps": 3.0}
        )
        
        report = self.oad.detect(fv)
        assert report.liquidity_state == "THICK"

    def test_liquidity_state_thin(self):
        """测试 THIN 流动性状态"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        fv = FeatureVector(
            **{**fv.model_dump(), "impact_buy_bps": 15.0}
        )
        
        report = self.oad.detect(fv)
        assert report.liquidity_state == "THIN"

    def test_liquidity_state_toxic(self):
        """测试 TOXIC 流动性状态"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        fv = FeatureVector(
            **{**fv.model_dump(), "impact_buy_bps": 25.0}
        )
        
        report = self.oad.detect(fv)
        assert report.liquidity_state == "TOXIC"

    def test_reset(self):
        """测试重置"""
        ts = time.time()
        
        for i in range(10):
            fv = self._create_normal_features(ts + i)
            self.oad.detect(fv)
        
        self.oad.reset()
        
        # 重置后统计应该清空
        assert self.oad._rolling_short.count("spread_bps") == 0
        assert self.oad._rolling_long.count("depth_bid") == 0

    def test_triggers_recorded(self):
        """测试所有触发器都被记录"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        report = self.oad.detect(fv)
        
        # 所有触发器都应该存在
        assert "spread_z" in report.triggers
        assert "impact_buy_z" in report.triggers
        assert "impact_sell_z" in report.triggers
        assert "msg_rate_z" in report.triggers
        assert "gap_flag" in report.triggers
