"""
TOXICTIDE Position Monitor

持仓监控器 - 监控止损/止盈触发
"""

import time
from typing import Literal
import structlog

from toxictide.models import Position
from toxictide.position.manager import PositionManager

logger = structlog.get_logger(__name__)


class PositionMonitor:
    """持仓监控器

    持续监控所有活跃仓位，检测止损/止盈/TTL 触发条件。

    **核心功能：**

    1. 止损检测：价格触及止损价格
    2. 止盈检测：价格触及止盈价格
    3. TTL 检测：持仓超过最大持有时间
    4. 返回需要平仓的仓位列表

    Example:
        >>> pm = PositionManager()
        >>> monitor = PositionMonitor(pm, max_hold_time_sec=3600)
        >>> to_close = monitor.check_positions(current_price=2100.50, current_time=time.time())
        >>> for position_id, reason, price in to_close:
        ...     pm.close_position(position_id, price, time.time(), reason)
    """

    def __init__(
        self,
        position_manager: PositionManager,
        max_hold_time_sec: int = 3600,
    ):
        """初始化持仓监控器

        Args:
            position_manager: 持仓管理器实例
            max_hold_time_sec: 最大持有时间（秒），默认 1 小时
        """
        self._pm = position_manager
        self._max_hold_time = max_hold_time_sec

        logger.info(
            "position_monitor_initialized",
            max_hold_time_sec=max_hold_time_sec,
        )

    def check_positions(
        self,
        current_price: float,
        current_time: float,
    ) -> list[tuple[str, str, float]]:
        """检查所有活跃仓位

        Args:
            current_price: 当前市场价格
            current_time: 当前时间戳

        Returns:
            需要平仓的仓位列表：[(position_id, reason, close_price), ...]
            reason 可能是：'stop_loss', 'take_profit', 'ttl_expired'
        """
        to_close: list[tuple[str, str, float]] = []

        for position in self._pm.get_active_positions():
            # 检查止损
            if self._should_stop_loss(position, current_price):
                logger.warning(
                    "stop_loss_triggered",
                    position_id=position.position_id,
                    side=position.side,
                    entry=position.entry_price,
                    stop=position.stop_price,
                    current=current_price,
                    unrealized_pnl=position.unrealized_pnl(current_price),
                )
                to_close.append((position.position_id, "stop_loss", current_price))
                continue  # 止损优先级最高，直接跳过后续检查

            # 检查止盈
            if self._should_take_profit(position, current_price):
                logger.info(
                    "take_profit_triggered",
                    position_id=position.position_id,
                    side=position.side,
                    entry=position.entry_price,
                    tp=position.tp_price,
                    current=current_price,
                    unrealized_pnl=position.unrealized_pnl(current_price),
                )
                to_close.append((position.position_id, "take_profit", current_price))
                continue

            # 检查 TTL（最大持有时间）
            if self._should_expire_by_ttl(position, current_time):
                logger.info(
                    "position_ttl_expired",
                    position_id=position.position_id,
                    entry_time=position.entry_time,
                    current_time=current_time,
                    hold_time_sec=current_time - position.entry_time,
                    unrealized_pnl=position.unrealized_pnl(current_price),
                )
                to_close.append((position.position_id, "ttl_expired", current_price))

        return to_close

    def _should_stop_loss(self, position: Position, current_price: float) -> bool:
        """判断是否触发止损

        Args:
            position: 持仓对象
            current_price: 当前价格

        Returns:
            True 表示触发止损
        """
        if position.side == "long":
            # 多头：当前价格 <= 止损价
            return current_price <= position.stop_price
        else:  # short
            # 空头：当前价格 >= 止损价
            return current_price >= position.stop_price

    def _should_take_profit(self, position: Position, current_price: float) -> bool:
        """判断是否触发止盈

        Args:
            position: 持仓对象
            current_price: 当前价格

        Returns:
            True 表示触发止盈
        """
        # 如果没有设置止盈价格，则不触发
        if not position.tp_price:
            return False

        if position.side == "long":
            # 多头：当前价格 >= 止盈价
            return current_price >= position.tp_price
        else:  # short
            # 空头：当前价格 <= 止盈价
            return current_price <= position.tp_price

    def _should_expire_by_ttl(self, position: Position, current_time: float) -> bool:
        """判断是否超过最大持有时间

        Args:
            position: 持仓对象
            current_time: 当前时间戳

        Returns:
            True 表示超过最大持有时间
        """
        hold_time = current_time - position.entry_time
        return hold_time >= self._max_hold_time

    def get_position_status(
        self,
        position: Position,
        current_price: float,
    ) -> dict:
        """获取单个仓位的详细状态

        Args:
            position: 持仓对象
            current_price: 当前价格

        Returns:
            状态字典
        """
        unrealized_pnl = position.unrealized_pnl(current_price)
        unrealized_pnl_pct = (unrealized_pnl / position.size_usd) * 100

        # 计算距离止损/止盈的百分比
        if position.side == "long":
            stop_distance_pct = ((current_price - position.stop_price) / current_price) * 100
            tp_distance_pct = ((position.tp_price - current_price) / current_price) * 100 if position.tp_price else None
        else:  # short
            stop_distance_pct = ((position.stop_price - current_price) / current_price) * 100
            tp_distance_pct = ((current_price - position.tp_price) / current_price) * 100 if position.tp_price else None

        return {
            "position_id": position.position_id,
            "side": position.side,
            "strategy": position.strategy,
            "entry_price": position.entry_price,
            "current_price": current_price,
            "stop_price": position.stop_price,
            "tp_price": position.tp_price,
            "size_usd": position.size_usd,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "stop_distance_pct": stop_distance_pct,
            "tp_distance_pct": tp_distance_pct,
            "will_stop_loss": self._should_stop_loss(position, current_price),
            "will_take_profit": self._should_take_profit(position, current_price),
        }
