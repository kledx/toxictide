"""
TOXICTIDE Trade Tape 测试
"""

import pytest
import time

from toxictide.market.tape import TradeTape, TradeAggregation
from toxictide.models import Trade


class TestTradeTape:
    """测试 TradeTape"""

    def setup_method(self):
        """每个测试前初始化"""
        self.tape = TradeTape(window_sec=300)

    def _create_trade(self, price=100.0, size=1.0, side="buy", ts=None):
        """创建测试交易"""
        return Trade(
            ts=ts or time.time(),
            price=price,
            size=size,
            side=side,
        )

    def test_add_trade(self):
        """测试添加交易"""
        trade = self._create_trade()
        self.tape.add(trade)

        assert len(self.tape) == 1
        assert self.tape.total_trades == 1

    def test_add_batch(self):
        """测试批量添加"""
        trades = [
            self._create_trade(size=1.0),
            self._create_trade(size=2.0),
            self._create_trade(size=3.0),
        ]
        self.tape.add_batch(trades)

        assert len(self.tape) == 3
        assert self.tape.total_trades == 3

    def test_window_cleanup(self):
        """测试窗口清理"""
        # 添加一个过期的交易
        old_trade = self._create_trade(ts=time.time() - 400)  # 400秒前
        self.tape.add(old_trade)

        # 添加一个新交易
        new_trade = self._create_trade()
        self.tape.add(new_trade)

        # 旧交易应该被清理
        assert len(self.tape) == 1

    def test_recent(self):
        """测试获取最近交易"""
        # 添加一些交易
        for i in range(5):
            trade = self._create_trade(size=float(i + 1))
            self.tape.add(trade)

        recent = self.tape.recent(sec=60)
        assert len(recent) == 5

    def test_aggregate_basic(self):
        """测试基础聚合"""
        trades = [
            self._create_trade(price=100.0, size=1.0, side="buy"),
            self._create_trade(price=100.0, size=2.0, side="sell"),
            self._create_trade(price=100.0, size=3.0, side="buy"),
        ]
        self.tape.add_batch(trades)

        agg = self.tape.aggregate()

        assert agg.vol == 6.0
        assert agg.trades == 3
        assert agg.buy_vol == 4.0
        assert agg.sell_vol == 2.0
        assert agg.avg_trade == 2.0
        assert agg.max_trade == 3.0
        assert agg.min_trade == 1.0

    def test_aggregate_signed_imbalance(self):
        """测试带符号不平衡"""
        # 全部买单
        trades = [
            self._create_trade(size=1.0, side="buy"),
            self._create_trade(size=1.0, side="buy"),
        ]
        self.tape.add_batch(trades)

        agg = self.tape.aggregate()
        assert agg.signed_imbalance == pytest.approx(1.0, rel=0.01)

        # 清空并添加全部卖单
        self.tape.clear()
        trades = [
            self._create_trade(size=1.0, side="sell"),
            self._create_trade(size=1.0, side="sell"),
        ]
        self.tape.add_batch(trades)

        agg = self.tape.aggregate()
        assert agg.signed_imbalance == pytest.approx(-1.0, rel=0.01)

    def test_aggregate_vwap(self):
        """测试成交量加权平均价"""
        trades = [
            self._create_trade(price=100.0, size=1.0, side="buy"),
            self._create_trade(price=200.0, size=1.0, side="buy"),
        ]
        self.tape.add_batch(trades)

        agg = self.tape.aggregate()
        # VWAP = (100*1 + 200*1) / 2 = 150
        assert agg.vwap == 150.0

    def test_aggregate_empty(self):
        """测试空 tape 聚合"""
        agg = self.tape.aggregate()

        assert agg.vol == 0.0
        assert agg.trades == 0
        assert agg.avg_trade == 0.0

    def test_get_toxic_score(self):
        """测试毒性分数"""
        # 极端不平衡
        trades = [
            self._create_trade(size=1.0, side="buy"),
            self._create_trade(size=1.0, side="buy"),
        ]
        self.tape.add_batch(trades)

        score = self.tape.get_toxic_score()
        assert score == pytest.approx(1.0, rel=0.01)

    def test_get_trade_rate(self):
        """测试交易速率"""
        for _ in range(10):
            self.tape.add(self._create_trade())

        rate = self.tape.get_trade_rate(sec=60)
        assert rate == pytest.approx(10 / 60, rel=0.01)

    def test_get_volume_rate(self):
        """测试成交量速率"""
        for _ in range(10):
            self.tape.add(self._create_trade(size=2.0))

        rate = self.tape.get_volume_rate(sec=60)
        assert rate == pytest.approx(20 / 60, rel=0.01)

    def test_iterator(self):
        """测试迭代器"""
        trades = [
            self._create_trade(size=1.0),
            self._create_trade(size=2.0),
        ]
        self.tape.add_batch(trades)

        count = 0
        for trade in self.tape:
            count += 1
        assert count == 2

    def test_is_empty(self):
        """测试是否为空"""
        assert self.tape.is_empty

        self.tape.add(self._create_trade())
        assert not self.tape.is_empty

    def test_clear(self):
        """测试清空"""
        self.tape.add(self._create_trade())
        self.tape.clear()

        assert self.tape.is_empty
        assert len(self.tape) == 0

    def test_window_sec_property(self):
        """测试窗口大小属性"""
        assert self.tape.window_sec == 300

    def test_unknown_side_handling(self):
        """测试 unknown side 处理"""
        trades = [
            self._create_trade(size=2.0, side="unknown"),
        ]
        self.tape.add_batch(trades)

        agg = self.tape.aggregate()
        # unknown 平分到 buy/sell
        assert agg.buy_vol == 1.0
        assert agg.sell_vol == 1.0
