"""
TOXICTIDE Price Impact 测试
"""

import pytest

from toxictide.features.impact import (
    estimate_impact_bps,
    estimate_market_depth_usd,
    estimate_slippage_bps,
)
from toxictide.models import OrderBookLevel


class TestEstimateImpact:
    """测试 estimate_impact_bps"""

    def test_sufficient_liquidity_buy(self):
        """测试买入方向流动性充足"""
        asks = [
            OrderBookLevel(price=100.0, size=10.0),  # 1000 USD
            OrderBookLevel(price=101.0, size=10.0),  # 1010 USD
        ]
        
        # 买入 1000 USD，只消耗第一档
        impact = estimate_impact_bps(asks, "buy", 1000.0, 99.5)
        
        # 平均成交价 = 100.0
        # Impact = (100.0 - 99.5) / 99.5 * 10000 ≈ 50 bps
        assert 45 < impact < 55

    def test_sufficient_liquidity_sell(self):
        """测试卖出方向流动性充足"""
        bids = [
            OrderBookLevel(price=100.0, size=10.0),
            OrderBookLevel(price=99.0, size=10.0),
        ]
        
        impact = estimate_impact_bps(bids, "sell", 1000.0, 100.5)
        
        # 平均成交价 = 100.0
        # Impact = (100.5 - 100.0) / 100.5 * 10000 ≈ 50 bps
        assert 45 < impact < 55

    def test_insufficient_liquidity(self):
        """测试流动性不足"""
        asks = [
            OrderBookLevel(price=100.0, size=1.0),  # 只有 100 USD
        ]
        
        # 尝试买入 10000 USD
        impact = estimate_impact_bps(asks, "buy", 10000.0, 99.5)
        
        # 应该返回 9999.9（流动性不足信号）
        assert impact == 9999.9

    def test_empty_levels(self):
        """测试空盘口"""
        impact = estimate_impact_bps([], "buy", 1000.0, 100.0)
        assert impact == 9999.9

    def test_zero_quantity(self):
        """测试零数量"""
        asks = [OrderBookLevel(price=100.0, size=10.0)]
        impact = estimate_impact_bps(asks, "buy", 0.0, 100.0)
        assert impact == 0.0

    def test_cross_multiple_levels(self):
        """测试跨越多档"""
        asks = [
            OrderBookLevel(price=100.0, size=5.0),   # 500 USD
            OrderBookLevel(price=101.0, size=5.0),   # 505 USD
            OrderBookLevel(price=102.0, size=5.0),   # 510 USD
        ]
        
        # 买入 1200 USD，需要跨 3 档
        impact = estimate_impact_bps(asks, "buy", 1200.0, 99.5)
        
        # 平均价格应该 > 100 且 < 102
        assert impact > 50  # 至少 50 bps


class TestEstimateMarketDepth:
    """测试 estimate_market_depth_usd"""

    def test_basic_depth(self):
        """测试基础深度计算"""
        asks = [
            OrderBookLevel(price=100.0, size=10.0),
            OrderBookLevel(price=102.0, size=10.0),
        ]
        
        # 最大允许 100 bps 冲击，能执行多少 USD？
        depth = estimate_market_depth_usd(asks, 100.0, 99.0, "buy")
        
        assert depth > 0
        assert depth <= 2020  # 总流动性上限

    def test_zero_max_impact(self):
        """测试零冲击上限"""
        asks = [OrderBookLevel(price=100.0, size=10.0)]
        depth = estimate_market_depth_usd(asks, 0.0, 100.0, "buy")
        assert depth == 0.0

    def test_empty_levels(self):
        """测试空盘口"""
        depth = estimate_market_depth_usd([], 50.0, 100.0, "buy")
        assert depth == 0.0


class TestEstimateSlippage:
    """测试 estimate_slippage_bps"""

    def test_buy_positive_slippage(self):
        """测试买入正滑点（不利）"""
        # 决策时 mid = 100.0，实际成交 100.5
        slippage = estimate_slippage_bps(100.5, 100.0, "buy")
        assert slippage == pytest.approx(50.0)

    def test_buy_negative_slippage(self):
        """测试买入负滑点（有利）"""
        # 决策时 mid = 100.0，实际成交 99.5
        slippage = estimate_slippage_bps(99.5, 100.0, "buy")
        assert slippage == pytest.approx(-50.0)

    def test_sell_positive_slippage(self):
        """测试卖出正滑点"""
        # 决策时 mid = 100.0，实际成交 99.5
        slippage = estimate_slippage_bps(99.5, 100.0, "sell")
        assert slippage == pytest.approx(50.0)

    def test_sell_negative_slippage(self):
        """测试卖出负滑点"""
        slippage = estimate_slippage_bps(100.5, 100.0, "sell")
        assert slippage == pytest.approx(-50.0)

    def test_no_slippage(self):
        """测试无滑点"""
        slippage = estimate_slippage_bps(100.0, 100.0, "buy")
        assert slippage == 0.0
