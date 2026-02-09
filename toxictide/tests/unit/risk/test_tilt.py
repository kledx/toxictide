"""
TOXICTIDE Tilt Tracker 测试
"""

import time

import pytest

from toxictide.risk.tilt import TiltTracker


class TestTiltTracker:
    """测试 TiltTracker"""

    def setup_method(self):
        """每个测试前初始化"""
        self.tracker = TiltTracker()

    def test_initialization(self):
        """测试初始化"""
        assert self.tracker.total_trades == 0
        assert self.tracker.daily_pnl == 0.0

    def test_record_trade(self):
        """测试记录交易"""
        ts = time.time()
        
        self.tracker.record_trade(ts, pnl=50.0)
        
        assert self.tracker.total_trades == 1
        assert self.tracker.daily_pnl == 50.0

    def test_daily_pnl_accumulation(self):
        """测试日盈亏累计"""
        ts = time.time()
        
        self.tracker.record_trade(ts, pnl=50.0)
        self.tracker.record_trade(ts + 1, pnl=-30.0)
        self.tracker.record_trade(ts + 2, pnl=20.0)
        
        assert self.tracker.daily_pnl == 40.0

    def test_daily_pnl_pct(self):
        """测试日盈亏百分比"""
        ts = time.time()
        
        self.tracker.record_trade(ts, pnl=-100.0)
        
        pct = self.tracker.daily_pnl_pct(balance=10000.0)
        
        assert pct == pytest.approx(-1.0)

    def test_trades_last_hour(self):
        """测试最近 1 小时交易笔数"""
        ts = time.time()
        
        # 添加 1 小时内的交易
        for i in range(5):
            self.tracker.record_trade(ts - i * 60, pnl=10.0)
        
        # 添加 1 小时外的交易
        self.tracker.record_trade(ts - 7200, pnl=10.0)
        
        count = self.tracker.trades_last_hour(ts)
        
        assert count == 5

    def test_reset(self):
        """测试重置"""
        ts = time.time()
        
        self.tracker.record_trade(ts, pnl=50.0)
        self.tracker.reset()
        
        assert self.tracker.total_trades == 0
        assert self.tracker.daily_pnl == 0.0
