"""
TOXICTIDE Tilt Tracker

交易频率和盈亏跟踪 - 用于检测过度交易和日亏熔断
"""

from collections import deque
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class TiltTracker:
    """交易频率和盈亏跟踪器
    
    跟踪以下指标：
    1. **交易历史** - 时间戳和盈亏
    2. **最近 1 小时交易笔数** - 防止过度交易
    3. **当日累计盈亏** - 日亏熔断判断
    4. **日盈亏百分比** - 相对账户余额
    
    每日零点自动重置日盈亏统计。
    
    Example:
        >>> tracker = TiltTracker()
        >>> tracker.record_trade(time.time(), pnl=-50.0)
        >>> trades_count = tracker.trades_last_hour(time.time())
        >>> daily_pnl_pct = tracker.daily_pnl_pct(balance=10000.0)
    """

    def __init__(self) -> None:
        """初始化 Tilt Tracker"""
        self._trades: deque[tuple[float, float]] = deque()  # (ts, pnl)
        self._daily_pnl: float = 0.0
        self._last_reset_date: Optional[str] = None
        
        logger.info("tilt_tracker_initialized")
    
    def record_trade(self, ts: float, pnl: float) -> None:
        """记录交易
        
        Args:
            ts: 时间戳
            pnl: 盈亏（正数为盈利，负数为亏损）
        """
        # 检查是否需要重置（跨日）
        current_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        
        if self._last_reset_date != current_date:
            self._daily_pnl = 0.0
            self._last_reset_date = current_date
            logger.info("daily_pnl_reset", date=current_date)
        
        # 记录交易
        self._trades.append((ts, pnl))
        self._daily_pnl += pnl
        
        logger.debug(
            "trade_recorded",
            ts=ts,
            pnl=pnl,
            daily_pnl=self._daily_pnl,
        )
    
    def trades_last_hour(self, ts: float) -> int:
        """获取最近 1 小时的交易笔数
        
        Args:
            ts: 当前时间戳
        
        Returns:
            交易笔数
        """
        cutoff = ts - 3600  # 1 小时前
        count = sum(1 for t, _ in self._trades if t >= cutoff)
        return count
    
    def daily_pnl_pct(self, balance: float) -> float:
        """计算日盈亏百分比
        
        Args:
            balance: 账户余额
        
        Returns:
            日盈亏百分比（如 -1.5 表示亏损 1.5%）
        """
        if balance <= 0:
            return 0.0
        
        return (self._daily_pnl / balance) * 100
    
    @property
    def daily_pnl(self) -> float:
        """当日累计盈亏（绝对值）"""
        return self._daily_pnl
    
    @property
    def total_trades(self) -> int:
        """历史总交易笔数"""
        return len(self._trades)
    
    def reset(self) -> None:
        """重置所有统计"""
        self._trades.clear()
        self._daily_pnl = 0.0
        self._last_reset_date = None
        logger.info("tilt_tracker_reset")
