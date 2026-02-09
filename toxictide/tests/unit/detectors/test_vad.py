"""
TOXICTIDE VAD 测试
"""

import time

import pytest

from toxictide.detectors.vad import VolumeAnomalyDetector
from toxictide.models import FeatureVector


class TestVolumeAnomalyDetector:
    """测试 VolumeAnomalyDetector"""

    def setup_method(self):
        """每个测试前初始化"""
        config = {
            "vad": {
                "z_warn": 4.0,
                "z_danger": 6.0,
                "toxic_warn": 0.6,
                "toxic_danger": 0.75,
            }
        }
        self.vad = VolumeAnomalyDetector(config)

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
            signed_imb=0.1,
            toxic=0.3,
        )

    def test_initialization(self):
        """测试初始化"""
        assert self.vad._z_warn == 4.0
        assert self.vad._z_danger == 6.0
        assert self.vad._toxic_warn == 0.6
        assert self.vad._toxic_danger == 0.75

    def test_normal_state(self):
        """测试正常状态"""
        ts = time.time()
        
        for i in range(20):
            fv = self._create_normal_features(ts + i)
            report = self.vad.detect(fv)
        
        assert report.level == "OK"
        assert not report.events["burst"]
        assert not report.events["drought"]
        assert not report.events["whale"]

    def test_volume_burst(self):
        """测试成交量爆发"""
        ts = time.time()
        
        # 添加正常数据
        for i in range(20):
            fv = self._create_normal_features(ts + i)
            self.vad.detect(fv)
        
        # 添加爆发成交量
        fv_burst = self._create_normal_features(ts + 20)
        fv_burst = FeatureVector(
            **{**fv_burst.model_dump(), "vol": 1000.0}  # 10 倍成交量
        )
        
        report = self.vad.detect(fv_burst)
        
        assert report.level in ["WARN", "DANGER"]
        assert report.events["burst"]

    def test_volume_drought(self):
        """测试成交量干涸"""
        ts = time.time()
        
        # 添加正常数据
        for i in range(20):
            fv = self._create_normal_features(ts + i)
            self.vad.detect(fv)
        
        # 添加极低成交量
        fv_drought = self._create_normal_features(ts + 20)
        fv_drought = FeatureVector(
            **{**fv_drought.model_dump(), "vol": 0.001}
        )
        
        report = self.vad.detect(fv_drought)
        
        assert report.events["drought"]

    def test_whale_trade(self):
        """测试鲸鱼交易"""
        ts = time.time()
        
        for i in range(20):
            fv = self._create_normal_features(ts + i)
            self.vad.detect(fv)
        
        # 添加异常大单
        fv_whale = self._create_normal_features(ts + 20)
        fv_whale = FeatureVector(
            **{**fv_whale.model_dump(), "max_trade": 200.0}  # 10 倍大单
        )
        
        report = self.vad.detect(fv_whale)
        
        assert report.level in ["WARN", "DANGER"]
        assert report.events["whale"]

    def test_toxic_warn(self):
        """测试毒性流 WARN"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        fv = FeatureVector(
            **{**fv.model_dump(), "toxic": 0.65}
        )
        
        report = self.vad.detect(fv)
        
        assert report.level == "WARN"

    def test_toxic_danger(self):
        """测试毒性流 DANGER"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        fv = FeatureVector(
            **{**fv.model_dump(), "toxic": 0.8}
        )
        
        report = self.vad.detect(fv)
        
        assert report.level == "DANGER"

    def test_triggers_recorded(self):
        """测试触发器记录"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        report = self.vad.detect(fv)
        
        assert "vol_z" in report.triggers
        assert "trades_z" in report.triggers
        assert "max_trade_z" in report.triggers
        assert "signed_imb" in report.triggers
        assert "toxic" in report.triggers

    def test_events_recorded(self):
        """测试事件记录"""
        ts = time.time()
        
        fv = self._create_normal_features(ts)
        report = self.vad.detect(fv)
        
        assert "burst" in report.events
        assert "drought" in report.events
        assert "whale" in report.events

    def test_reset(self):
        """测试重置"""
        ts = time.time()
        
        for i in range(10):
            fv = self._create_normal_features(ts + i)
            self.vad.detect(fv)
        
        self.vad.reset()
        
        assert self.vad._rolling.count("log_vol") == 0
