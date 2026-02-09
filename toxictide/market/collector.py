"""
TOXICTIDE Market Collector

市场数据采集器，支持：
- Paper 模式（模拟数据）
- 未来可扩展为真实数据源
"""

import random
import time
from abc import ABC, abstractmethod
from typing import Protocol

import numpy as np
import structlog

from toxictide.models import OrderBookLevel, OrderBookState, Trade

logger = structlog.get_logger(__name__)


class IMarketCollector(Protocol):
    """市场数据采集器接口"""

    def get_orderbook_snapshot(self) -> OrderBookState:
        """获取订单簿快照"""
        ...

    def get_recent_trades(self) -> list[Trade]:
        """获取最近的交易"""
        ...


class PaperMarketCollector:
    """Paper 模式市场数据采集器

    生成模拟的市场数据，用于测试和演示。

    Example:
        >>> collector = PaperMarketCollector(base_price=2000.0)
        >>> snapshot = collector.get_orderbook_snapshot()
        >>> print(snapshot.mid)
        2000.05
    """

    def __init__(
        self,
        base_price: float = 2000.0,
        volatility: float = 0.0005,
        spread_bps: float = 5.0,
        depth_levels: int = 20,
        tick_size: float = 0.01,
    ) -> None:
        """初始化 Paper 采集器

        Args:
            base_price: 基准价格
            volatility: 价格波动率（每 tick）
            spread_bps: 买卖价差（基点）
            depth_levels: 盘口深度档数
            tick_size: 最小价格变动
        """
        self._base_price = base_price
        self._current_price = base_price
        self._volatility = volatility
        self._spread_bps = spread_bps
        self._depth_levels = depth_levels
        self._tick_size = tick_size
        self._seq = 0
        self._trade_id = 0

        # 价格历史（用于趋势模拟）
        self._price_history: list[float] = [base_price]
        self._trend_direction = 0.0  # -1 到 1

        logger.info(
            "paper_collector_initialized",
            base_price=base_price,
            volatility=volatility,
            spread_bps=spread_bps,
        )

    def _update_price(self) -> None:
        """更新当前价格"""
        # 随机游走 + 趋势
        random_return = np.random.normal(0, self._volatility)
        trend_return = self._trend_direction * self._volatility * 0.5

        # 偶尔改变趋势方向
        if random.random() < 0.05:
            self._trend_direction = np.random.uniform(-1, 1)

        total_return = random_return + trend_return
        self._current_price *= (1 + total_return)

        # 限制价格范围
        self._current_price = max(
            self._base_price * 0.8,
            min(self._base_price * 1.2, self._current_price)
        )

        # 对齐到 tick size
        self._current_price = round(
            self._current_price / self._tick_size
        ) * self._tick_size

        self._price_history.append(self._current_price)
        if len(self._price_history) > 1000:
            self._price_history = self._price_history[-500:]

    def get_orderbook_snapshot(self) -> OrderBookState:
        """生成订单簿快照

        Returns:
            OrderBookState 对象
        """
        self._update_price()
        self._seq += 1

        mid = self._current_price
        spread = mid * (self._spread_bps / 10000)
        half_spread = spread / 2

        best_bid = mid - half_spread
        best_ask = mid + half_spread

        # 生成盘口
        bids: list[OrderBookLevel] = []
        asks: list[OrderBookLevel] = []

        for i in range(self._depth_levels):
            # 价格递减/递增
            bid_price = best_bid - i * self._tick_size * (1 + i * 0.1)
            ask_price = best_ask + i * self._tick_size * (1 + i * 0.1)

            # 数量：近档小，远档大（模拟真实市场）
            base_size = random.uniform(0.5, 3.0)
            depth_multiplier = 1 + i * 0.2

            bid_size = base_size * depth_multiplier * random.uniform(0.8, 1.2)
            ask_size = base_size * depth_multiplier * random.uniform(0.8, 1.2)

            bids.append(OrderBookLevel(
                price=round(bid_price, 2),
                size=round(bid_size, 4),
            ))
            asks.append(OrderBookLevel(
                price=round(ask_price, 2),
                size=round(ask_size, 4),
            ))

        return OrderBookState(
            ts=time.time(),
            bids=bids,
            asks=asks,
            seq=self._seq,
        )

    def get_recent_trades(self, count: int = 10) -> list[Trade]:
        """生成最近的交易

        Args:
            count: 交易数量

        Returns:
            Trade 列表
        """
        trades: list[Trade] = []
        current_ts = time.time()

        for i in range(count):
            self._trade_id += 1

            # 随机时间（最近几秒内）
            ts = current_ts - random.uniform(0, 5)

            # 随机价格（在当前价格附近）
            price_offset = np.random.normal(0, self._current_price * 0.0001)
            price = self._current_price + price_offset
            price = round(price / self._tick_size) * self._tick_size

            # 随机数量（大部分小单，偶尔大单）
            if random.random() < 0.05:
                # 大单
                size = random.uniform(5.0, 20.0)
            else:
                # 小单
                size = random.uniform(0.01, 2.0)

            # 随机方向（可以有不平衡）
            buy_probability = 0.5 + self._trend_direction * 0.1
            side = "buy" if random.random() < buy_probability else "sell"

            trades.append(Trade(
                ts=ts,
                price=round(price, 2),
                size=round(size, 4),
                side=side,
            ))

        # 按时间排序
        trades.sort(key=lambda t: t.ts)
        return trades

    def generate_single_trade(self) -> Trade:
        """生成单笔交易

        Returns:
            Trade 对象
        """
        self._trade_id += 1

        price_offset = np.random.normal(0, self._current_price * 0.0001)
        price = self._current_price + price_offset
        price = round(price / self._tick_size) * self._tick_size

        if random.random() < 0.05:
            size = random.uniform(5.0, 20.0)
        else:
            size = random.uniform(0.01, 2.0)

        buy_probability = 0.5 + self._trend_direction * 0.1
        side = "buy" if random.random() < buy_probability else "sell"

        return Trade(
            ts=time.time(),
            price=round(price, 2),
            size=round(size, 4),
            side=side,
        )

    def simulate_anomaly(
        self,
        anomaly_type: str,
    ) -> tuple[OrderBookState, list[Trade]]:
        """模拟异常情况

        Args:
            anomaly_type: 异常类型
                - "spread_spike": 价差突然扩大
                - "volume_burst": 成交量爆发
                - "liquidity_gap": 流动性断层
                - "whale_trade": 鲸鱼交易

        Returns:
            (OrderBookState, trades) 元组
        """
        if anomaly_type == "spread_spike":
            # 临时增加价差
            original_spread = self._spread_bps
            self._spread_bps = original_spread * 5
            snapshot = self.get_orderbook_snapshot()
            self._spread_bps = original_spread
            trades = self.get_recent_trades(5)

        elif anomaly_type == "volume_burst":
            # 生成大量交易
            snapshot = self.get_orderbook_snapshot()
            trades = []
            for _ in range(50):
                trade = self.generate_single_trade()
                trades.append(Trade(
                    ts=trade.ts,
                    price=trade.price,
                    size=trade.size * 3,  # 放大
                    side=trade.side,
                ))

        elif anomaly_type == "liquidity_gap":
            # 减少盘口深度
            original_levels = self._depth_levels
            self._depth_levels = 3
            snapshot = self.get_orderbook_snapshot()
            self._depth_levels = original_levels
            trades = self.get_recent_trades(5)

        elif anomaly_type == "whale_trade":
            # 生成鲸鱼交易
            snapshot = self.get_orderbook_snapshot()
            whale_trade = Trade(
                ts=time.time(),
                price=self._current_price,
                size=random.uniform(50.0, 200.0),
                side=random.choice(["buy", "sell"]),
            )
            trades = [whale_trade]

        else:
            snapshot = self.get_orderbook_snapshot()
            trades = self.get_recent_trades(5)

        return snapshot, trades

    @property
    def current_price(self) -> float:
        """当前价格"""
        return self._current_price

    @property
    def seq(self) -> int:
        """当前序列号"""
        return self._seq

    def reset(self) -> None:
        """重置到初始状态"""
        self._current_price = self._base_price
        self._seq = 0
        self._trade_id = 0
        self._price_history = [self._base_price]
        self._trend_direction = 0.0
