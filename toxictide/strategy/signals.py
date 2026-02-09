"""
TOXICTIDE Signal Engine

策略信号生成引擎 - 基于市场状态生成交易候选
"""

from collections import deque
from typing import Optional

import numpy as np
import structlog

from toxictide.models import (
    FeatureVector,
    RegimeState,
    TradeCandidate,
)

logger = structlog.get_logger(__name__)


class SignalEngine:
    """策略信号生成引擎
    
    实现两大策略：
    
    1. **Trend Breakout（趋势突破）**
       - 适用场景：TREND_UP/DOWN + ACTIVE
       - 突破近期高/低点时开仓
       - 止损：入场价 ±0.5%
       - 止盈：入场价 ±1.0%
       - 置信度：0.7
       - TTL：5 分钟
    
    2. **Range Mean Revert（震荡均值回归）**
       - 适用场景：RANGE + CALM
       - 价格偏离均值 ±1.5σ 时反向开仓
       - 止损：入场价 ±0.2%
       - 止盈：均值
       - 置信度：0.6
       - TTL：10 分钟
    
    **风控集成：**
    - TOXIC 状态不生成信号
    - 基于 Policy 白名单过滤策略
    
    Example:
        >>> config = {}
        >>> policy = {"allowed_strategies": ["trend_breakout", "range_mean_revert"]}
        >>> engine = SignalEngine(config)
        >>> candidate = engine.generate(fv, regime, policy)
        >>> if candidate:
        ...     print(f"Signal: {candidate.side} @ {candidate.entry_price}")
    """

    def __init__(self, config: dict) -> None:
        """初始化信号引擎
        
        Args:
            config: 配置字典
        """
        self._config = config
        
        # 价格历史（用于策略计算）
        self._price_history: deque[tuple[float, float]] = deque(maxlen=100)
        
        logger.info("signal_engine_initialized")
    
    def generate(
        self,
        fv: FeatureVector,
        regime: RegimeState,
        policy: dict,
    ) -> Optional[TradeCandidate]:
        """生成交易信号
        
        Args:
            fv: 特征向量
            regime: 市场状态
            policy: 策略策略（包含 allowed_strategies 白名单）
        
        Returns:
            TradeCandidate 对象，若无信号则返回 None
        """
        ts = fv.ts
        
        # 记录价格历史
        self._price_history.append((ts, fv.mid))
        
        # ========== 风控前置检查 ==========
        
        # TOXIC 状态不生成信号
        if regime.flow_regime == "TOXIC":
            logger.debug("no_signal_toxic_regime", ts=ts)
            return None
        
        # 获取策略白名单
        allowed_strategies = policy.get("allowed_strategies", [])
        
        if not allowed_strategies:
            logger.debug("no_allowed_strategies", ts=ts)
            return None
        
        # 数据不足
        if len(self._price_history) < 5:
            logger.debug("insufficient_price_history", count=len(self._price_history))
            return None
        
        # ========== 策略 1: Trend Breakout ==========
        
        if "trend_breakout" in allowed_strategies:
            candidate = self._trend_breakout(fv, regime)
            if candidate:
                return candidate
        
        # ========== 策略 2: Range Mean Revert ==========
        
        if "range_mean_revert" in allowed_strategies:
            candidate = self._range_mean_revert(fv, regime)
            if candidate:
                return candidate
        
        # 无信号
        return None
    
    def _trend_breakout(
        self,
        fv: FeatureVector,
        regime: RegimeState,
    ) -> Optional[TradeCandidate]:
        """趋势突破策略
        
        Args:
            fv: 特征向量
            regime: 市场状态
        
        Returns:
            TradeCandidate 或 None
        """
        # 仅在趋势 + 活跃时触发
        if regime.price_regime not in ["TREND_UP", "TREND_DOWN"]:
            return None
        
        if regime.flow_regime != "ACTIVE":
            return None
        
        # 计算近期高低点
        prices = np.array([p for _, p in self._price_history])
        recent_high = np.max(prices[-20:])
        recent_low = np.min(prices[-20:])
        
        current_price = fv.mid
        
        # ========== Breakout Long ==========
        
        if current_price > recent_high * 1.001:  # 突破高点 0.1%
            stop_price = current_price * 0.995   # 止损 -0.5%
            tp_price = current_price * 1.01      # 止盈 +1.0%
            
            logger.info(
                "signal_trend_breakout_long",
                entry=current_price,
                stop=stop_price,
                tp=tp_price,
                recent_high=recent_high,
            )
            
            return TradeCandidate(
                ts=fv.ts,
                side="long",
                entry_price=current_price,
                stop_price=stop_price,
                tp_price=tp_price,
                confidence=0.7,
                ttl_sec=300,  # 5 分钟
                strategy="trend_breakout",
            )
        
        # ========== Breakout Short ==========
        
        if current_price < recent_low * 0.999:  # 跌破低点 0.1%
            stop_price = current_price * 1.005   # 止损 +0.5%
            tp_price = current_price * 0.99      # 止盈 -1.0%
            
            logger.info(
                "signal_trend_breakout_short",
                entry=current_price,
                stop=stop_price,
                tp=tp_price,
                recent_low=recent_low,
            )
            
            return TradeCandidate(
                ts=fv.ts,
                side="short",
                entry_price=current_price,
                stop_price=stop_price,
                tp_price=tp_price,
                confidence=0.7,
                ttl_sec=300,
                strategy="trend_breakout",
            )
        
        return None
    
    def _range_mean_revert(
        self,
        fv: FeatureVector,
        regime: RegimeState,
    ) -> Optional[TradeCandidate]:
        """震荡均值回归策略
        
        Args:
            fv: 特征向量
            regime: 市场状态
        
        Returns:
            TradeCandidate 或 None
        """
        # 仅在震荡 + 平静时触发
        if regime.price_regime != "RANGE":
            return None
        
        if regime.flow_regime != "CALM":
            return None
        
        # 计算均值和标准差
        prices = np.array([p for _, p in self._price_history])
        mean_price = np.mean(prices[-30:])
        std_price = np.std(prices[-30:])
        
        current_price = fv.mid
        
        # ========== Mean Revert Long (Oversold) ==========
        
        if current_price < mean_price - 1.5 * std_price:
            stop_price = current_price * 0.998   # 止损 -0.2%
            tp_price = mean_price                # 止盈：回归均值
            
            logger.info(
                "signal_range_mean_revert_long",
                entry=current_price,
                stop=stop_price,
                tp=tp_price,
                mean=mean_price,
                std=std_price,
            )
            
            return TradeCandidate(
                ts=fv.ts,
                side="long",
                entry_price=current_price,
                stop_price=stop_price,
                tp_price=tp_price,
                confidence=0.6,
                ttl_sec=600,  # 10 分钟
                strategy="range_mean_revert",
            )
        
        # ========== Mean Revert Short (Overbought) ==========
        
        if current_price > mean_price + 1.5 * std_price:
            stop_price = current_price * 1.002   # 止损 +0.2%
            tp_price = mean_price                # 止盈：回归均值
            
            logger.info(
                "signal_range_mean_revert_short",
                entry=current_price,
                stop=stop_price,
                tp=tp_price,
                mean=mean_price,
                std=std_price,
            )
            
            return TradeCandidate(
                ts=fv.ts,
                side="short",
                entry_price=current_price,
                stop_price=stop_price,
                tp_price=tp_price,
                confidence=0.6,
                ttl_sec=600,
                strategy="range_mean_revert",
            )
        
        return None
    
    def reset(self) -> None:
        """重置信号引擎状态"""
        self._price_history.clear()
        logger.info("signal_engine_reset")
