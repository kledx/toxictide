"""
TOXICTIDE Rolling Statistics

滚动统计工具，用于稳健的异常检测
"""

import time
from collections import deque
from typing import Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class RollingMAD:
    """滚动 Median + MAD 统计
    
    使用 Median（中位数）和 MAD（Median Absolute Deviation）进行稳健统计，
    相比均值+标准差更抗极值影响，适合金融数据。
    
    MAD z-score 计算公式：
        z = |x - median| / (1.4826 * MAD + eps)
    
    其中 1.4826 是将 MAD 转换为标准差的系数（假设正态分布）。
    
    Example:
        >>> rolling = RollingMAD(window_sec=300)
        >>> rolling.update("price", 100.0, time.time())
        >>> rolling.update("price", 102.0, time.time())
        >>> z = rolling.zscore("price")
        >>> print(f"Z-score: {z:.2f}")
    """

    def __init__(self, window_sec: int) -> None:
        """初始化滚动统计
        
        Args:
            window_sec: 窗口大小（秒）
        """
        self._window_sec = window_sec
        self._data: dict[str, deque[tuple[float, float]]] = {}  # name -> [(ts, value), ...]
        
    def update(self, name: str, value: float, ts: float) -> None:
        """更新数据点
        
        Args:
            name: 指标名称
            value: 值
            ts: 时间戳
        """
        if name not in self._data:
            self._data[name] = deque()
        
        self._data[name].append((ts, value))
        self._cleanup(name, ts)
    
    def _cleanup(self, name: str, current_ts: float) -> None:
        """清理过期数据
        
        Args:
            name: 指标名称
            current_ts: 当前时间戳
        """
        if name not in self._data:
            return
        
        cutoff_ts = current_ts - self._window_sec
        
        while self._data[name] and self._data[name][0][0] < cutoff_ts:
            self._data[name].popleft()
    
    def median(self, name: str) -> float:
        """计算中位数
        
        Args:
            name: 指标名称
        
        Returns:
            中位数，无数据时返回 0.0
        """
        if name not in self._data or not self._data[name]:
            return 0.0
        
        values = [v for _, v in self._data[name]]
        return float(np.median(values))
    
    def mad(self, name: str) -> float:
        """计算 MAD (Median Absolute Deviation)
        
        Args:
            name: 指标名称
        
        Returns:
            MAD 值，数据不足时返回 0.0
        """
        if name not in self._data or len(self._data[name]) < 2:
            return 0.0
        
        values = np.array([v for _, v in self._data[name]])
        median_val = np.median(values)
        mad_val = np.median(np.abs(values - median_val))
        
        return float(mad_val)
    
    def zscore(self, name: str) -> float:
        """计算 MAD z-score（稳健 z-score）
        
        相比传统 z-score 使用均值+标准差，MAD z-score 使用中位数+MAD，
        对极值更稳健。
        
        Args:
            name: 指标名称
        
        Returns:
            z-score 值，数据不足或无变化时返回 0.0
        """
        if name not in self._data or not self._data[name]:
            return 0.0
        
        values = [v for _, v in self._data[name]]
        current_value = values[-1]
        
        median_val = self.median(name)
        mad_val = self.mad(name)
        
        # 若 MAD 为 0（数据无变化），返回 0
        if mad_val == 0:
            return 0.0
        
        # MAD to standard deviation conversion factor (assumes normality)
        # σ ≈ 1.4826 * MAD
        z = abs(current_value - median_val) / (1.4826 * mad_val + 1e-9)
        
        return float(z)
    
    def mean(self, name: str) -> float:
        """计算均值（辅助函数）
        
        Args:
            name: 指标名称
        
        Returns:
            均值
        """
        if name not in self._data or not self._data[name]:
            return 0.0
        
        values = [v for _, v in self._data[name]]
        return float(np.mean(values))
    
    def std(self, name: str) -> float:
        """计算标准差（辅助函数）
        
        Args:
            name: 指标名称
        
        Returns:
            标准差
        """
        if name not in self._data or len(self._data[name]) < 2:
            return 0.0
        
        values = [v for _, v in self._data[name]]
        return float(np.std(values))
    
    def count(self, name: str) -> int:
        """获取当前窗口内的数据点数量
        
        Args:
            name: 指标名称
        
        Returns:
            数据点数量
        """
        if name not in self._data:
            return 0
        return len(self._data[name])
    
    def clear(self, name: Optional[str] = None) -> None:
        """清空数据
        
        Args:
            name: 指标名称，None 表示清空所有
        """
        if name is None:
            self._data.clear()
        elif name in self._data:
            self._data[name].clear()
    
    @property
    def window_sec(self) -> int:
        """窗口大小（秒）"""
        return self._window_sec
