"""
TOXICTIDE Position Manager

持仓管理器 - 管理所有活跃持仓
"""

from typing import Optional
import structlog

from toxictide.models import Position, TradeCandidate, Fill

logger = structlog.get_logger(__name__)


class PositionManager:
    """持仓管理器

    管理所有活跃持仓，提供持仓的增删改查功能。

    **核心功能：**

    1. 记录新开仓位
    2. 查询活跃仓位
    3. 平仓处理
    4. 持仓统计

    Example:
        >>> pm = PositionManager()
        >>> position = pm.open_position(candidate, fills, size_usd)
        >>> active = pm.get_active_positions()
        >>> pm.close_position(position.position_id, close_price, close_time, "stop_loss")
    """

    def __init__(self):
        """初始化持仓管理器"""
        self._positions: dict[str, Position] = {}
        self._next_id = 1

        logger.info("position_manager_initialized")

    def open_position(
        self,
        candidate: TradeCandidate,
        fills: list[Fill],
        size_usd: float,
    ) -> Position:
        """开仓

        Args:
            candidate: 交易候选（包含止损/止盈信息）
            fills: 成交记录
            size_usd: 最终仓位大小（USD）

        Returns:
            Position 对象
        """
        # 生成唯一 ID
        position_id = f"pos_{self._next_id:06d}"
        self._next_id += 1

        # 计算平均成交价格和总数量
        if fills:
            total_cost = sum(f.price * f.size for f in fills)
            total_size = sum(f.size for f in fills)
            avg_price = total_cost / total_size if total_size > 0 else candidate.entry_price
        else:
            avg_price = candidate.entry_price
            total_size = size_usd / avg_price

        # 创建持仓记录
        position = Position(
            position_id=position_id,
            side=candidate.side,
            entry_price=avg_price,
            entry_time=candidate.ts,
            size=total_size,
            size_usd=size_usd,
            stop_price=candidate.stop_price,
            tp_price=candidate.tp_price,
            strategy=candidate.strategy,
            is_open=True,
        )

        self._positions[position_id] = position

        logger.info(
            "position_opened",
            position_id=position_id,
            side=candidate.side,
            entry=avg_price,
            size_usd=size_usd,
            stop=candidate.stop_price,
            tp=candidate.tp_price,
            strategy=candidate.strategy,
        )

        return position

    def get_active_positions(self) -> list[Position]:
        """获取所有活跃仓位

        Returns:
            活跃仓位列表
        """
        return [p for p in self._positions.values() if p.is_open]

    def get_position(self, position_id: str) -> Optional[Position]:
        """获取指定仓位

        Args:
            position_id: 仓位 ID

        Returns:
            Position 对象，若不存在则返回 None
        """
        return self._positions.get(position_id)

    def close_position(
        self,
        position_id: str,
        close_price: float,
        close_time: float,
        reason: str,
    ) -> Optional[Position]:
        """平仓

        Args:
            position_id: 仓位 ID
            close_price: 平仓价格
            close_time: 平仓时间
            reason: 平仓原因（stop_loss/take_profit/manual）

        Returns:
            已平仓的 Position 对象，若不存在则返回 None
        """
        position = self._positions.get(position_id)

        if not position:
            logger.warning("position_not_found", position_id=position_id)
            return None

        if not position.is_open:
            logger.warning("position_already_closed", position_id=position_id)
            return None

        # 平仓
        position.close(close_price, close_time, reason)

        logger.info(
            "position_closed",
            position_id=position_id,
            entry=position.entry_price,
            close=close_price,
            pnl=position.pnl,
            reason=reason,
        )

        return position

    def get_total_exposure(self) -> float:
        """获取总持仓敞口（USD）

        Returns:
            所有活跃仓位的总价值
        """
        return sum(p.size_usd for p in self.get_active_positions())

    def get_unrealized_pnl(self, current_price: float) -> float:
        """获取总未实现盈亏

        Args:
            current_price: 当前市场价格

        Returns:
            所有活跃仓位的未实现盈亏总和
        """
        return sum(p.unrealized_pnl(current_price) for p in self.get_active_positions())

    def get_statistics(self) -> dict:
        """获取持仓统计

        Returns:
            统计信息字典
        """
        all_positions = list(self._positions.values())
        active_positions = self.get_active_positions()
        closed_positions = [p for p in all_positions if not p.is_open]

        # 计算胜率和盈亏
        if closed_positions:
            winning_trades = [p for p in closed_positions if p.pnl and p.pnl > 0]
            losing_trades = [p for p in closed_positions if p.pnl and p.pnl < 0]

            total_pnl = sum(p.pnl for p in closed_positions if p.pnl)
            win_rate = len(winning_trades) / len(closed_positions) * 100

            avg_win = sum(p.pnl for p in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(p.pnl for p in losing_trades) / len(losing_trades) if losing_trades else 0
        else:
            total_pnl = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0

        return {
            "total_positions": len(all_positions),
            "active_positions": len(active_positions),
            "closed_positions": len(closed_positions),
            "total_exposure_usd": self.get_total_exposure(),
            "total_pnl": total_pnl,
            "win_rate_pct": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    def reset(self) -> None:
        """重置持仓管理器"""
        self._positions.clear()
        self._next_id = 1
        logger.info("position_manager_reset")
