"""
TOXICTIDE Market Collector 测试
"""

import pytest
import time

from toxictide.market.collector import PaperMarketCollector
from toxictide.models import OrderBookState, Trade


class TestPaperMarketCollector:
    """测试 PaperMarketCollector"""

    def setup_method(self):
        """每个测试前初始化"""
        self.collector = PaperMarketCollector(
            base_price=2000.0,
            volatility=0.0005,
            spread_bps=5.0,
            depth_levels=20,
        )

    def test_initialization(self):
        """测试初始化"""
        assert self.collector.current_price == 2000.0
        assert self.collector.seq == 0

    def test_get_orderbook_snapshot(self):
        """测试获取订单簿快照"""
        snapshot = self.collector.get_orderbook_snapshot()

        assert isinstance(snapshot, OrderBookState)
        assert len(snapshot.bids) == 20
        assert len(snapshot.asks) == 20
        assert snapshot.seq == 1

    def test_snapshot_ordering(self):
        """测试快照排序正确"""
        snapshot = self.collector.get_orderbook_snapshot()

        # Bids 应该降序
        bid_prices = [b.price for b in snapshot.bids]
        assert bid_prices == sorted(bid_prices, reverse=True)

        # Asks 应该升序
        ask_prices = [a.price for a in snapshot.asks]
        assert ask_prices == sorted(ask_prices)

    def test_snapshot_spread_positive(self):
        """测试快照 spread 为正"""
        snapshot = self.collector.get_orderbook_snapshot()

        assert snapshot.spread > 0
        assert snapshot.bids[0].price < snapshot.asks[0].price

    def test_multiple_snapshots_update_seq(self):
        """测试多次快照更新序列号"""
        snap1 = self.collector.get_orderbook_snapshot()
        snap2 = self.collector.get_orderbook_snapshot()
        snap3 = self.collector.get_orderbook_snapshot()

        assert snap1.seq == 1
        assert snap2.seq == 2
        assert snap3.seq == 3

    def test_price_changes_over_time(self):
        """测试价格随时间变化"""
        prices = []
        for _ in range(10):
            snapshot = self.collector.get_orderbook_snapshot()
            prices.append(snapshot.mid)

        # 价格应该有变化
        unique_prices = set(prices)
        assert len(unique_prices) > 1

    def test_get_recent_trades(self):
        """测试获取最近交易"""
        trades = self.collector.get_recent_trades(count=10)

        assert len(trades) == 10
        for trade in trades:
            assert isinstance(trade, Trade)
            assert trade.price > 0
            assert trade.size > 0
            assert trade.side in ["buy", "sell"]

    def test_trades_sorted_by_time(self):
        """测试交易按时间排序"""
        trades = self.collector.get_recent_trades(count=10)

        timestamps = [t.ts for t in trades]
        assert timestamps == sorted(timestamps)

    def test_generate_single_trade(self):
        """测试生成单笔交易"""
        trade = self.collector.generate_single_trade()

        assert isinstance(trade, Trade)
        assert trade.price > 0
        assert trade.size > 0

    def test_simulate_anomaly_spread_spike(self):
        """测试模拟价差异常"""
        normal_snapshot = self.collector.get_orderbook_snapshot()
        normal_spread = normal_snapshot.spread_bps

        anomaly_snapshot, trades = self.collector.simulate_anomaly("spread_spike")

        # 异常时价差应该更大
        assert anomaly_snapshot.spread_bps > normal_spread

    def test_simulate_anomaly_volume_burst(self):
        """测试模拟成交量爆发"""
        snapshot, trades = self.collector.simulate_anomaly("volume_burst")

        # 应该有很多交易
        assert len(trades) == 50

    def test_simulate_anomaly_liquidity_gap(self):
        """测试模拟流动性断层"""
        snapshot, trades = self.collector.simulate_anomaly("liquidity_gap")

        # 盘口深度应该很浅
        assert len(snapshot.bids) == 3
        assert len(snapshot.asks) == 3

    def test_simulate_anomaly_whale_trade(self):
        """测试模拟鲸鱼交易"""
        snapshot, trades = self.collector.simulate_anomaly("whale_trade")

        assert len(trades) == 1
        assert trades[0].size >= 50.0  # 大单

    def test_reset(self):
        """测试重置"""
        # 生成一些数据
        for _ in range(10):
            self.collector.get_orderbook_snapshot()

        self.collector.reset()

        assert self.collector.current_price == 2000.0
        assert self.collector.seq == 0

    def test_price_bounded(self):
        """测试价格有边界"""
        # 生成很多快照，价格不应该偏离太远
        for _ in range(100):
            snapshot = self.collector.get_orderbook_snapshot()

        # 价格应该在基准价格的 80%-120% 范围内
        assert 1600 <= self.collector.current_price <= 2400

    def test_custom_parameters(self):
        """测试自定义参数"""
        collector = PaperMarketCollector(
            base_price=100.0,
            spread_bps=10.0,
            depth_levels=5,
        )

        snapshot = collector.get_orderbook_snapshot()

        assert len(snapshot.bids) == 5
        assert len(snapshot.asks) == 5
        assert snapshot.mid == pytest.approx(100.0, rel=0.01)
