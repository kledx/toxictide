"""
TOXICTIDE Trade Tape

滑动窗口 trade 存储，支持：
- 时间窗口自动清理
- 聚合统计（volume, trades, buy/sell split）
- VPIN 相关指标计算
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import Iterator

import structlog

from toxictide.models import Trade

logger = structlog.get_logger(__name__)


@dataclass
class TradeAggregation:
    """交易聚合统计"""
    vol: float = 0.0
    trades: int = 0
    buy_vol: float = 0.0
    sell_vol: float = 0.0
    avg_trade: float = 0.0
    max_trade: float = 0.0
    min_trade: float = 0.0
    vwap: float = 0.0
    signed_imbalance: float = 0.0


class TradeTape:
    """Trade Tape 滑动窗口

    维护最近一段时间的交易记录，提供聚合统计。

    Example:
        >>> tape = TradeTape(window_sec=300)
        >>> tape.add(Trade(ts=time.time(), price=100.0, size=1.0, side="buy"))
        >>> agg = tape.aggregate(sec=60)
        >>> print(agg.vol)
        1.0
    """

    def __init__(self, window_sec: int = 300) -> None:
        """初始化 Trade Tape

        Args:
            window_sec: 窗口大小（秒）
        """
        self._window_sec = window_sec
        self._trades: deque[Trade] = deque()
        self._total_trades: int = 0

    def add(self, trade: Trade) -> None:
        """添加交易

        Args:
            trade: Trade 对象
        """
        self._trades.append(trade)
        self._total_trades += 1
        self._cleanup()

    def add_batch(self, trades: list[Trade]) -> None:
        """批量添加交易

        Args:
            trades: Trade 列表
        """
        for trade in trades:
            self._trades.append(trade)
            self._total_trades += 1
        self._cleanup()

    def _cleanup(self, current_ts: float | None = None) -> None:
        """清理过期数据"""
        if current_ts is None:
            current_ts = time.time()

        cutoff_ts = current_ts - self._window_sec

        while self._trades and self._trades[0].ts < cutoff_ts:
            self._trades.popleft()

    def recent(self, sec: int | None = None) -> list[Trade]:
        """获取最近 N 秒的交易

        Args:
            sec: 秒数，None 表示全部窗口

        Returns:
            Trade 列表
        """
        self._cleanup()

        if sec is None:
            return list(self._trades)

        cutoff_ts = time.time() - sec
        return [t for t in self._trades if t.ts >= cutoff_ts]

    def aggregate(self, sec: int | None = None) -> TradeAggregation:
        """聚合统计

        Args:
            sec: 统计的秒数，None 表示全部窗口

        Returns:
            TradeAggregation 对象
        """
        trades = self.recent(sec)

        if not trades:
            return TradeAggregation()

        # 基础统计
        buy_vol = 0.0
        sell_vol = 0.0
        total_notional = 0.0
        trade_sizes = []

        for t in trades:
            size = t.size
            notional = t.price * t.size
            trade_sizes.append(size)
            total_notional += notional

            if t.side == "buy":
                buy_vol += size
            elif t.side == "sell":
                sell_vol += size
            else:  # unknown
                # 平分到 buy/sell
                buy_vol += size / 2
                sell_vol += size / 2

        total_vol = buy_vol + sell_vol
        trades_count = len(trades)

        # 计算指标
        avg_trade = total_vol / trades_count if trades_count > 0 else 0.0
        max_trade = max(trade_sizes) if trade_sizes else 0.0
        min_trade = min(trade_sizes) if trade_sizes else 0.0
        vwap = total_notional / total_vol if total_vol > 0 else 0.0

        # 带符号不平衡
        signed_imb = (buy_vol - sell_vol) / (buy_vol + sell_vol + 1e-9)

        return TradeAggregation(
            vol=total_vol,
            trades=trades_count,
            buy_vol=buy_vol,
            sell_vol=sell_vol,
            avg_trade=avg_trade,
            max_trade=max_trade,
            min_trade=min_trade,
            vwap=vwap,
            signed_imbalance=signed_imb,
        )

    def get_toxic_score(self, sec: int | None = None) -> float:
        """计算毒性流分数（简化 VPIN）

        基于买卖不平衡的绝对值，范围 [0, 1]

        Args:
            sec: 统计的秒数

        Returns:
            毒性分数
        """
        agg = self.aggregate(sec)
        return abs(agg.signed_imbalance)

    def get_trade_rate(self, sec: int = 60) -> float:
        """获取交易速率（笔/秒）

        Args:
            sec: 统计的秒数

        Returns:
            每秒交易笔数
        """
        trades = self.recent(sec)
        if not trades:
            return 0.0
        return len(trades) / sec

    def get_volume_rate(self, sec: int = 60) -> float:
        """获取成交量速率（数量/秒）

        Args:
            sec: 统计的秒数

        Returns:
            每秒成交量
        """
        agg = self.aggregate(sec)
        return agg.vol / sec if sec > 0 else 0.0

    def __iter__(self) -> Iterator[Trade]:
        """迭代所有交易"""
        return iter(self._trades)

    def __len__(self) -> int:
        """当前窗口内的交易数量"""
        self._cleanup()
        return len(self._trades)

    @property
    def window_sec(self) -> int:
        """窗口大小"""
        return self._window_sec

    @property
    def total_trades(self) -> int:
        """历史总交易数（包括已清理的）"""
        return self._total_trades

    @property
    def is_empty(self) -> bool:
        """是否为空"""
        self._cleanup()
        return len(self._trades) == 0

    def clear(self) -> None:
        """清空所有交易"""
        self._trades.clear()
