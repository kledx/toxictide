"""
TOXICTIDE Orderbook 测试
"""

import pytest
import time

from toxictide.market.orderbook import OrderBook
from toxictide.models import OrderBookLevel
from toxictide.exceptions import OrderbookInconsistentError, SequenceError


class TestOrderBook:
    """测试 OrderBook"""

    def setup_method(self):
        """每个测试前初始化"""
        self.book = OrderBook()

    def _create_valid_snapshot(self):
        """创建有效的快照数据"""
        bids = [
            OrderBookLevel(price=100.0, size=10.0),
            OrderBookLevel(price=99.0, size=20.0),
            OrderBookLevel(price=98.0, size=30.0),
        ]
        asks = [
            OrderBookLevel(price=101.0, size=15.0),
            OrderBookLevel(price=102.0, size=25.0),
            OrderBookLevel(price=103.0, size=35.0),
        ]
        return bids, asks

    def test_apply_snapshot(self):
        """测试应用快照"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        assert self.book.seq == 1
        assert self.book.bids_count == 3
        assert self.book.asks_count == 3
        assert self.book.best_bid_price == 100.0
        assert self.book.best_ask_price == 101.0

    def test_mid_price(self):
        """测试中间价计算"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        assert self.book.mid == 100.5

    def test_spread(self):
        """测试价差计算"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        assert self.book.spread == 1.0
        assert self.book.spread_bps == pytest.approx(99.5, rel=0.01)

    def test_negative_spread_raises_error(self):
        """测试负价差抛出异常"""
        bids = [OrderBookLevel(price=101.0, size=10.0)]
        asks = [OrderBookLevel(price=100.0, size=15.0)]

        with pytest.raises(OrderbookInconsistentError):
            self.book.apply_snapshot(bids, asks, seq=1)

    def test_apply_delta(self):
        """测试增量更新"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        # 添加新价位
        changes = [
            {"side": "bid", "price": 99.5, "size": 5.0},
            {"side": "ask", "price": 101.5, "size": 8.0},
        ]
        self.book.apply_delta(changes, seq=2)

        assert self.book.seq == 2
        assert self.book.bids_count == 4
        assert self.book.asks_count == 4

    def test_apply_delta_remove_level(self):
        """测试增量更新删除价位"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        # 删除价位（size=0）
        changes = [
            {"side": "bid", "price": 99.0, "size": 0},
        ]
        self.book.apply_delta(changes, seq=2)

        assert self.book.bids_count == 2

    def test_apply_delta_sequence_error(self):
        """测试序列号不连续抛出异常"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        changes = [{"side": "bid", "price": 99.5, "size": 5.0}]

        with pytest.raises(SequenceError):
            self.book.apply_delta(changes, seq=3)  # 跳过了 seq=2

    def test_top_n(self):
        """测试获取前 N 档"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        top_bids, top_asks = self.book.top_n(2)

        assert len(top_bids) == 2
        assert len(top_asks) == 2
        assert top_bids[0].price == 100.0
        assert top_asks[0].price == 101.0

    def test_depth_usd(self):
        """测试 USD 深度计算"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        # bid 深度 = 100*10 + 99*20 + 98*30 = 1000 + 1980 + 2940 = 5920
        bid_depth = self.book.depth_usd("bid", levels=3)
        assert bid_depth == pytest.approx(5920.0, rel=0.01)

    def test_depth_to_price(self):
        """测试消耗深度计算"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        # 消耗 1000 USD 的 ask
        avg_price, remaining = self.book.depth_to_price("ask", 1000)

        assert remaining == 0  # 流动性足够
        assert avg_price > 100  # 平均价格在 ask 侧

    def test_depth_to_price_insufficient_liquidity(self):
        """测试流动性不足"""
        bids = [OrderBookLevel(price=100.0, size=1.0)]
        asks = [OrderBookLevel(price=101.0, size=1.0)]
        self.book.apply_snapshot(bids, asks, seq=1)

        # 尝试消耗 10000 USD
        avg_price, remaining = self.book.depth_to_price("ask", 10000)

        assert remaining > 0  # 有剩余

    def test_get_state(self):
        """测试获取状态"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        state = self.book.get_state()

        assert len(state.bids) == 3
        assert len(state.asks) == 3
        assert state.seq == 1
        assert state.bids[0].price == 100.0  # 最高买价在前

    def test_empty_book(self):
        """测试空订单簿"""
        assert self.book.mid == 0.0
        assert self.book.spread == 0.0
        assert self.book.best_bid_price is None
        assert self.book.best_ask_price is None
        assert self.book.is_consistent()

    def test_clear(self):
        """测试清空订单簿"""
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)

        self.book.clear()

        assert self.book.bids_count == 0
        assert self.book.asks_count == 0
        assert self.book.seq == 0

    def test_update_count(self):
        """测试更新计数"""
        bids, asks = self._create_valid_snapshot()

        assert self.book.update_count == 0

        self.book.apply_snapshot(bids, asks, seq=1)
        assert self.book.update_count == 1

        changes = [{"side": "bid", "price": 99.5, "size": 5.0}]
        self.book.apply_delta(changes, seq=2)
        assert self.book.update_count == 2

    def test_last_update_ts(self):
        """测试最后更新时间"""
        before = time.time()
        bids, asks = self._create_valid_snapshot()
        self.book.apply_snapshot(bids, asks, seq=1)
        after = time.time()

        assert before <= self.book.last_update_ts <= after
