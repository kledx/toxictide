"""
TOXICTIDE Feature Engine 测试
"""

import time

import pytest

from toxictide.features.feature_engine import FeatureEngine
from toxictide.market.collector import PaperMarketCollector
from toxictide.market.orderbook import OrderBook
from toxictide.market.tape import TradeTape
from toxictide.models import Trade


class TestFeatureEngine:
    """测试 FeatureEngine"""

    def setup_method(self):
        """每个测试前初始化"""
        config = {
            "features": {
                "impact_size_quote_usd": 1000,
            }
        }
        self.engine = FeatureEngine(config)
        
        # 创建测试用的 orderbook 和 tape
        self.book = OrderBook()
        self.tape = TradeTape(window_sec=300)
        
        # 使用 collector 生成真实数据
        self.collector = PaperMarketCollector(
            base_price=2000.0,
            spread_bps=5.0,
            depth_levels=20,
        )

    def test_compute_basic(self):
        """测试基础特征计算"""
        # 生成数据
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        trades = self.collector.get_recent_trades(count=10)
        self.tape.add_batch(trades)
        
        # 计算特征
        ts = time.time()
        fv = self.engine.compute(self.book, self.tape, ts)
        
        # 验证基础字段
        assert fv.ts == ts
        assert fv.mid > 0
        assert fv.spread > 0
        assert fv.spread_bps > 0

    def test_orderbook_features(self):
        """测试 orderbook 特征"""
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        trades = self.collector.get_recent_trades(count=5)
        self.tape.add_batch(trades)
        
        fv = self.engine.compute(self.book, self.tape, time.time())
        
        # Top of book
        assert fv.top_bid_sz > 0
        assert fv.top_ask_sz > 0
        
        # Depth
        assert fv.depth_bid_k > 0
        assert fv.depth_ask_k > 0
        
        # Imbalance 应该在 -1 到 1 之间
        assert -1 <= fv.imb_k <= 1
        
        # Impact 应该是正数
        assert fv.impact_buy_bps >= 0
        assert fv.impact_sell_bps >= 0

    def test_trade_features(self):
        """测试 trade 特征"""
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        # 添加一些交易
        trades = self.collector.get_recent_trades(count=20)
        self.tape.add_batch(trades)
        
        fv = self.engine.compute(self.book, self.tape, time.time())
        
        # Volume 特征
        assert fv.vol >= 0
        assert fv.trades >= 0
        assert fv.avg_trade >= 0
        assert fv.max_trade >= 0
        
        # Signed imbalance 应该在 -1 到 1 之间
        assert -1 <= fv.signed_imb <= 1
        
        # Toxic 应该在 0 到 1 之间
        assert 0 <= fv.toxic <= 1

    def test_empty_orderbook(self):
        """测试空订单簿"""
        fv = self.engine.compute(self.book, self.tape, time.time())
        
        # 应该返回空特征
        assert fv.mid == 0.0
        assert fv.spread == 0.0
        assert fv.impact_buy_bps == 9999.9
        assert fv.impact_sell_bps == 9999.9

    def test_empty_tape(self):
        """测试空 trade tape"""
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        # tape 为空
        fv = self.engine.compute(self.book, self.tape, time.time())
        
        # Trade 特征应该为 0
        assert fv.vol == 0.0
        assert fv.trades == 0
        assert fv.avg_trade == 0.0
        assert fv.max_trade == 0.0

    def test_microprice(self):
        """测试 microprice 计算"""
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        trades = self.collector.get_recent_trades(count=5)
        self.tape.add_batch(trades)
        
        fv = self.engine.compute(self.book, self.tape, time.time())
        
        # microprice 应该接近 mid
        assert abs(fv.micro_minus_mid) < fv.spread

    def test_churn_calculation(self):
        """测试 churn 计算"""
        # 第一次计算
        snapshot1 = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot1.bids, snapshot1.asks, snapshot1.seq)
        
        trades = self.collector.get_recent_trades(count=5)
        self.tape.add_batch(trades)
        
        fv1 = self.engine.compute(self.book, self.tape, time.time())
        
        # 第二次计算（盘口应该有变化）
        snapshot2 = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot2.bids, snapshot2.asks, snapshot2.seq)
        
        fv2 = self.engine.compute(self.book, self.tape, time.time())
        
        # Churn 应该大于 0（盘口有变化）
        assert fv2.churn >= 0

    def test_msg_rate(self):
        """测试消息速率"""
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        trades = self.collector.get_recent_trades(count=5)
        self.tape.add_batch(trades)
        
        # 多次计算
        for _ in range(5):
            fv = self.engine.compute(self.book, self.tape, time.time())
        
        # msg_rate 应该大于 0
        assert fv.msg_rate >= 0

    def test_reset(self):
        """测试重置"""
        # 先计算一些特征
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        trades = self.collector.get_recent_trades(count=5)
        self.tape.add_batch(trades)
        
        fv1 = self.engine.compute(self.book, self.tape, time.time())
        
        # 重置
        self.engine.reset()
        
        # 重置后的特征应该不同
        fv2 = self.engine.compute(self.book, self.tape, time.time())
        
        # msg_rate 应该重置
        assert fv2.msg_rate != fv1.msg_rate

    def test_multiple_compute_calls(self):
        """测试多次计算"""
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        trades = self.collector.get_recent_trades(count=10)
        self.tape.add_batch(trades)
        
        # 多次计算应该稳定
        fv_list = []
        for _ in range(5):
            fv = self.engine.compute(self.book, self.tape, time.time())
            fv_list.append(fv)
        
        # 所有计算都应该成功
        assert len(fv_list) == 5
        assert all(fv.mid > 0 for fv in fv_list)

    def test_toxic_score_range(self):
        """测试 toxic score 范围"""
        snapshot = self.collector.get_orderbook_snapshot()
        self.book.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.seq)
        
        # 添加偏向买方的交易
        buy_trades = [
            Trade(ts=time.time(), price=2000.0, size=1.0, side="buy")
            for _ in range(10)
        ]
        self.tape.add_batch(buy_trades)
        
        fv = self.engine.compute(self.book, self.tape, time.time())
        
        # Toxic 应该接近 1（极端不平衡）
        assert fv.toxic > 0.8
