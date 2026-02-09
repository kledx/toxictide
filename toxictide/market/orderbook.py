"""
TOXICTIDE Orderbook 维护

L2 订单簿维护，支持：
- 快照应用
- 增量更新
- 数据一致性检查
- 深度计算
"""

import time
from collections import OrderedDict
from typing import Literal

import structlog

from toxictide.exceptions import OrderbookInconsistentError, SequenceError
from toxictide.models import OrderBookLevel, OrderBookState

logger = structlog.get_logger(__name__)


class OrderBook:
    """L2 订单簿维护

    维护买卖盘口数据，支持快照和增量更新。

    Example:
        >>> book = OrderBook()
        >>> bids = [OrderBookLevel(price=100, size=10)]
        >>> asks = [OrderBookLevel(price=101, size=15)]
        >>> book.apply_snapshot(bids, asks, seq=1)
        >>> state = book.get_state()
        >>> print(state.mid)
        100.5
    """

    def __init__(self) -> None:
        """初始化订单簿"""
        self._bids: dict[float, float] = {}  # price -> size
        self._asks: dict[float, float] = {}  # price -> size
        self._seq: int = 0
        self._last_update_ts: float = 0.0
        self._update_count: int = 0

    def apply_snapshot(
        self,
        bids: list[OrderBookLevel],
        asks: list[OrderBookLevel],
        seq: int,
    ) -> None:
        """应用完整快照

        Args:
            bids: 买盘列表
            asks: 卖盘列表
            seq: 序列号

        Raises:
            OrderbookInconsistentError: 数据不一致
        """
        self._bids.clear()
        self._asks.clear()

        for level in bids:
            self._bids[level.price] = level.size

        for level in asks:
            self._asks[level.price] = level.size

        self._seq = seq
        self._last_update_ts = time.time()
        self._update_count += 1

        if not self.is_consistent():
            raise OrderbookInconsistentError(
                f"Snapshot inconsistent at seq={seq}: "
                f"best_bid={self.best_bid_price}, best_ask={self.best_ask_price}"
            )

        logger.debug(
            "snapshot_applied",
            seq=seq,
            bids_count=len(bids),
            asks_count=len(asks),
            mid=self.mid,
        )

    def apply_delta(
        self,
        changes: list[dict],
        seq: int,
    ) -> None:
        """应用增量更新

        Args:
            changes: 变更列表，每个变更包含 {side, price, size}
                     size=0 表示删除该价位
            seq: 序列号

        Raises:
            SequenceError: 序列号不连续
            OrderbookInconsistentError: 数据不一致
        """
        # 检查序列号连续性
        if seq != self._seq + 1:
            raise SequenceError(
                f"Sequence gap: expected {self._seq + 1}, got {seq}"
            )

        for change in changes:
            side = change["side"]
            price = float(change["price"])
            size = float(change["size"])

            if side == "bid":
                if size == 0:
                    self._bids.pop(price, None)
                else:
                    self._bids[price] = size
            elif side == "ask":
                if size == 0:
                    self._asks.pop(price, None)
                else:
                    self._asks[price] = size

        self._seq = seq
        self._last_update_ts = time.time()
        self._update_count += 1

        if not self.is_consistent():
            raise OrderbookInconsistentError(
                f"Delta caused inconsistency at seq={seq}"
            )

        logger.debug(
            "delta_applied",
            seq=seq,
            changes_count=len(changes),
        )

    def is_consistent(self) -> bool:
        """检查数据一致性

        Returns:
            True 如果数据一致（spread >= 0）
        """
        if not self._bids or not self._asks:
            return True  # 空盘口视为一致

        best_bid = max(self._bids.keys())
        best_ask = min(self._asks.keys())

        if best_ask <= best_bid:
            logger.warning(
                "negative_spread_detected",
                best_bid=best_bid,
                best_ask=best_ask,
            )
            return False

        return True

    def get_state(self) -> OrderBookState:
        """获取当前订单簿状态

        Returns:
            OrderBookState 对象
        """
        # 按价格排序构建列表
        bids = [
            OrderBookLevel(price=p, size=s)
            for p, s in sorted(self._bids.items(), reverse=True)
        ]
        asks = [
            OrderBookLevel(price=p, size=s)
            for p, s in sorted(self._asks.items())
        ]

        return OrderBookState(
            ts=self._last_update_ts,
            bids=bids,
            asks=asks,
            seq=self._seq,
        )

    def top_n(self, n: int) -> tuple[list[OrderBookLevel], list[OrderBookLevel]]:
        """获取前 N 档盘口

        Args:
            n: 档数

        Returns:
            (bids, asks) 元组
        """
        state = self.get_state()
        return state.bids[:n], state.asks[:n]

    def depth_usd(
        self,
        side: Literal["bid", "ask"],
        levels: int = 20,
    ) -> float:
        """计算指定档数的 USD 深度

        Args:
            side: 买盘或卖盘
            levels: 计算的档数

        Returns:
            USD 深度总量
        """
        if side == "bid":
            prices = sorted(self._bids.keys(), reverse=True)[:levels]
            return sum(p * self._bids[p] for p in prices)
        else:
            prices = sorted(self._asks.keys())[:levels]
            return sum(p * self._asks[p] for p in prices)

    def depth_to_price(
        self,
        side: Literal["bid", "ask"],
        target_usd: float,
    ) -> tuple[float, float]:
        """计算消耗指定 USD 需要扫过的价格

        Args:
            side: 买入用 ask，卖出用 bid
            target_usd: 目标 USD 数量

        Returns:
            (avg_price, remaining_usd) 元组
            如果流动性不足，remaining_usd > 0
        """
        if side == "ask":
            prices = sorted(self._asks.keys())
            book = self._asks
        else:
            prices = sorted(self._bids.keys(), reverse=True)
            book = self._bids

        remaining_usd = target_usd
        total_cost = 0.0
        total_size = 0.0

        for price in prices:
            if remaining_usd <= 0:
                break

            size = book[price]
            level_usd = price * size

            if level_usd >= remaining_usd:
                # 部分消耗这一档
                consumed_size = remaining_usd / price
                total_cost += remaining_usd
                total_size += consumed_size
                remaining_usd = 0
            else:
                # 完全消耗这一档
                total_cost += level_usd
                total_size += size
                remaining_usd -= level_usd

        avg_price = total_cost / total_size if total_size > 0 else 0.0
        return avg_price, remaining_usd

    @property
    def best_bid_price(self) -> float | None:
        """最优买价"""
        return max(self._bids.keys()) if self._bids else None

    @property
    def best_ask_price(self) -> float | None:
        """最优卖价"""
        return min(self._asks.keys()) if self._asks else None

    @property
    def mid(self) -> float:
        """中间价"""
        if not self._bids or not self._asks:
            return 0.0
        return (self.best_bid_price + self.best_ask_price) / 2

    @property
    def spread(self) -> float:
        """买卖价差"""
        if not self._bids or not self._asks:
            return 0.0
        return self.best_ask_price - self.best_bid_price

    @property
    def spread_bps(self) -> float:
        """买卖价差（基点）"""
        mid = self.mid
        if mid == 0:
            return 0.0
        return (self.spread / mid) * 10000

    @property
    def seq(self) -> int:
        """当前序列号"""
        return self._seq

    @property
    def last_update_ts(self) -> float:
        """最后更新时间戳"""
        return self._last_update_ts

    @property
    def update_count(self) -> int:
        """更新次数"""
        return self._update_count

    @property
    def bids_count(self) -> int:
        """买盘价位数"""
        return len(self._bids)

    @property
    def asks_count(self) -> int:
        """卖盘价位数"""
        return len(self._asks)

    def clear(self) -> None:
        """清空订单簿"""
        self._bids.clear()
        self._asks.clear()
        self._seq = 0
        self._last_update_ts = 0.0
