"""
TOXICTIDE Signal Engine 测试
"""

import time

import pytest

from toxictide.models import FeatureVector, RegimeState
from toxictide.strategy.signals import SignalEngine


class TestSignalEngine:
    """测试 SignalEngine"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = SignalEngine({})

    def _create_feature(self, mid: float) -> FeatureVector:
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
            toxic=0.3,
        )

    def _create_regime(
        self,
        price_regime: str = "RANGE",
        flow_regime: str = "CALM",
    ) -> RegimeState:
        """创建市场状态"""
        return RegimeState(
            ts=time.time(),
            price_regime=price_regime,
            vol_regime="NORMALVOL",
            flow_regime=flow_regime,
            confidence=0.8,
        )

    def test_initialization(self):
        """测试初始化"""
        assert len(self.engine._price_history) == 0

    def test_no_signal_toxic(self):
        """测试 TOXIC 状态不生成信号"""
        fv = self._create_feature(2000.0)
        regime = self._create_regime(flow_regime="TOXIC")
        policy = {"allowed_strategies": ["trend_breakout", "range_mean_revert"]}
        
        signal = self.engine.generate(fv, regime, policy)
        
        assert signal is None

    def test_no_signal_empty_whitelist(self):
        """测试空白名单不生成信号"""
        fv = self._create_feature(2000.0)
        regime = self._create_regime()
        policy = {"allowed_strategies": []}
        
        signal = self.engine.generate(fv, regime, policy)
        
        assert signal is None

    def test_no_signal_insufficient_data(self):
        """测试数据不足时不生成信号"""
        fv = self._create_feature(2000.0)
        regime = self._create_regime()
        policy = {"allowed_strategies": ["trend_breakout"]}
        
        signal = self.engine.generate(fv, regime, policy)
        
        assert signal is None

    def test_trend_breakout_long(self):
        """测试趋势突破做多信号"""
        policy = {"allowed_strategies": ["trend_breakout"]}
        regime = self._create_regime(price_regime="TREND_UP", flow_regime="ACTIVE")
        
        # 添加价格历史
        for i in range(40):
            fv = self._create_feature(2000.0 + i * 0.5)
            self.engine.generate(fv, regime, policy)
        
        # 突破高点
        fv_breakout = self._create_feature(2021.0)  # 突破前高
        signal = self.engine.generate(fv_breakout, regime, policy)
        
        assert signal is not None
        assert signal.side == "long"
        assert signal.strategy == "trend_breakout"
        assert signal.confidence == 0.7
        assert signal.ttl_sec == 300

    def test_trend_breakout_short(self):
        """测试趋势突破做空信号"""
        policy = {"allowed_strategies": ["trend_breakout"]}
        regime = self._create_regime(price_regime="TREND_DOWN", flow_regime="ACTIVE")
        
        # 添加价格历史
        for i in range(40):
            fv = self._create_feature(2100.0 - i * 0.5)
            self.engine.generate(fv, regime, policy)
        
        # 跌破低点
        fv_breakout = self._create_feature(2079.0)  # 跌破前低
        signal = self.engine.generate(fv_breakout, regime, policy)
        
        assert signal is not None
        assert signal.side == "short"
        assert signal.strategy == "trend_breakout"

    def test_range_mean_revert_long(self):
        """测试震荡均值回归做多信号"""
        policy = {"allowed_strategies": ["range_mean_revert"]}
        regime = self._create_regime(price_regime="RANGE", flow_regime="CALM")
        
        # 添加震荡价格历史（均值约 2000）
        for i in range(40):
            price = 2000.0 + (i % 5 - 2) * 2.0
            fv = self._create_feature(price)
            self.engine.generate(fv, regime, policy)
        
        # 价格严重低于均值（超卖）
        fv_oversold = self._create_feature(1990.0)
        signal = self.engine.generate(fv_oversold, regime, policy)
        
        assert signal is not None
        assert signal.side == "long"
        assert signal.strategy == "range_mean_revert"
        assert signal.confidence == 0.6
        assert signal.ttl_sec == 600

    def test_range_mean_revert_short(self):
        """测试震荡均值回归做空信号"""
        policy = {"allowed_strategies": ["range_mean_revert"]}
        regime = self._create_regime(price_regime="RANGE", flow_regime="CALM")
        
        # 添加震荡价格历史
        for i in range(40):
            price = 2000.0 + (i % 5 - 2) * 2.0
            fv = self._create_feature(price)
            self.engine.generate(fv, regime, policy)
        
        # 价格严重高于均值（超买）
        fv_overbought = self._create_feature(2010.0)
        signal = self.engine.generate(fv_overbought, regime, policy)
        
        assert signal is not None
        assert signal.side == "short"
        assert signal.strategy == "range_mean_revert"

    def test_policy_whitelist_filter(self):
        """测试策略白名单过滤"""
        policy = {"allowed_strategies": ["trend_breakout"]}  # 只允许突破
        regime = self._create_regime(price_regime="RANGE", flow_regime="CALM")
        
        # 添加数据
        for i in range(40):
            fv = self._create_feature(2000.0)
            self.engine.generate(fv, regime, policy)
        
        # 虽然满足均值回归条件，但策略不在白名单
        fv_oversold = self._create_feature(1990.0)
        signal = self.engine.generate(fv_oversold, regime, policy)
        
        # 应该无信号（因为 range_mean_revert 不在白名单）
        assert signal is None

    def test_stop_and_tp_prices(self):
        """测试止损止盈价格设置"""
        policy = {"allowed_strategies": ["trend_breakout"]}
        regime = self._create_regime(price_regime="TREND_UP", flow_regime="ACTIVE")
        
        for i in range(40):
            fv = self._create_feature(2000.0 + i * 0.5)
            self.engine.generate(fv, regime, policy)
        
        fv_breakout = self._create_feature(2021.0)
        signal = self.engine.generate(fv_breakout, regime, policy)
        
        assert signal is not None
        assert signal.stop_price < signal.entry_price  # 做多止损低于入场价
        assert signal.tp_price > signal.entry_price    # 做多止盈高于入场价

    def test_reset(self):
        """测试重置"""
        for i in range(10):
            fv = self._create_feature(2000.0)
            regime = self._create_regime()
            policy = {"allowed_strategies": ["trend_breakout"]}
            self.engine.generate(fv, regime, policy)
        
        self.engine.reset()
        
        assert len(self.engine._price_history) == 0
