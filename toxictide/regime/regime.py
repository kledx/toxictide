"""
TOXICTIDE Regime Classifier

市场状态分类器 - 三维状态识别
"""

from collections import deque
from typing import Literal

import numpy as np
import structlog

from toxictide.models import (
    FeatureVector,
    OrderbookAnomalyReport,
    RegimeState,
    VolumeAnomalyReport,
)

logger = structlog.get_logger(__name__)


class RegimeClassifier:
    """市场状态分类器
    
    将市场状态分类为三个维度：
    
    1. **Price Regime（价格趋势）**：
       - TREND_UP: 上升趋势（短期均线 > 长期均线 * 1.002）
       - TREND_DOWN: 下降趋势（短期均线 < 长期均线 * 0.998）
       - RANGE: 震荡盘整（介于两者之间）
    
    2. **Vol Regime（波动率）**：
       - HIGHVOL: 高波动（年化波动率 > 50%）
       - NORMALVOL: 正常波动（20% - 50%）
       - LOWVOL: 低波动（< 20%）
    
    3. **Flow Regime（流动性/毒性）**：
       - TOXIC: 毒性流，流动性极差（toxic>=0.6 或 OAD=DANGER 或 impact>20）
       - ACTIVE: 活跃，有异常但可交易（vol_z>=4 或 OAD=WARN）
       - CALM: 平静，正常状态
    
    Example:
        >>> config = {}
        >>> classifier = RegimeClassifier(config)
        >>> regime = classifier.classify(fv, oad, vad)
        >>> print(f"{regime.price_regime}/{regime.flow_regime}")
        TREND_UP/CALM
    """

    def __init__(self, config: dict) -> None:
        """初始化状态分类器
        
        Args:
            config: 配置字典
        """
        self._config = config
        
        # 价格历史（用于趋势判断）
        self._price_history: deque[tuple[float, float]] = deque(maxlen=100)  # (ts, price)
        
        logger.info("regime_classifier_initialized")
    
    def classify(
        self,
        fv: FeatureVector,
        oad: OrderbookAnomalyReport,
        vad: VolumeAnomalyReport,
    ) -> RegimeState:
        """分类市场状态
        
        Args:
            fv: 特征向量
            oad: 盘口异常报告
            vad: 成交量异常报告
        
        Returns:
            RegimeState 对象
        """
        ts = fv.ts
        
        # 记录价格历史
        self._price_history.append((ts, fv.mid))
        
        # ========== Price Regime ==========
        
        price_regime = self._classify_price_regime()
        
        # ========== Vol Regime ==========
        
        vol_regime = self._classify_vol_regime()
        
        # ========== Flow Regime ==========
        
        flow_regime = self._classify_flow_regime(fv, oad, vad)
        
        # ========== Confidence ==========
        
        # 数据点越多，置信度越高
        if len(self._price_history) >= 50:
            confidence = 0.8
        elif len(self._price_history) >= 20:
            confidence = 0.6
        else:
            confidence = 0.4
        
        return RegimeState(
            ts=ts,
            price_regime=price_regime,
            vol_regime=vol_regime,
            flow_regime=flow_regime,
            confidence=confidence,
        )
    
    def _classify_price_regime(self) -> Literal["TREND_UP", "TREND_DOWN", "RANGE"]:
        """分类价格趋势
        
        Returns:
            价格状态
        """
        if len(self._price_history) < 20:
            return "RANGE"
        
        prices = np.array([p for _, p in self._price_history])
        
        # 短期均线（最近 10 个点）
        ma_short = np.mean(prices[-10:])
        
        # 长期均线（最近 30 个点）
        ma_long = np.mean(prices[-30:]) if len(prices) >= 30 else np.mean(prices)
        
        # 趋势判定（0.2% 阈值）
        if ma_short > ma_long * 1.002:
            return "TREND_UP"
        elif ma_short < ma_long * 0.998:
            return "TREND_DOWN"
        else:
            return "RANGE"
    
    def _classify_vol_regime(self) -> Literal["HIGHVOL", "NORMALVOL", "LOWVOL"]:
        """分类波动率状态
        
        Returns:
            波动率状态
        """
        if len(self._price_history) < 20:
            return "NORMALVOL"
        
        prices = np.array([p for _, p in self._price_history])
        
        # 计算收益率
        returns = np.diff(prices) / prices[:-1]
        
        # 年化波动率（假设每个点是 1 秒）
        realized_vol = np.std(returns) * np.sqrt(252 * 24 * 3600)
        
        # 分类
        if realized_vol > 0.5:
            return "HIGHVOL"
        elif realized_vol < 0.2:
            return "LOWVOL"
        else:
            return "NORMALVOL"
    
    def _classify_flow_regime(
        self,
        fv: FeatureVector,
        oad: OrderbookAnomalyReport,
        vad: VolumeAnomalyReport,
    ) -> Literal["TOXIC", "ACTIVE", "CALM"]:
        """分类流动性/毒性状态
        
        Args:
            fv: 特征向量
            oad: 盘口异常报告
            vad: 成交量异常报告
        
        Returns:
            流动性状态
        """
        max_impact = max(fv.impact_buy_bps, fv.impact_sell_bps)
        toxic = vad.triggers.get("toxic", 0.0)
        vol_z = vad.triggers.get("vol_z", 0.0)
        
        # TOXIC: 严重异常
        if (
            toxic >= 0.6 or
            oad.level == "DANGER" or
            max_impact > 20
        ):
            return "TOXIC"
        
        # ACTIVE: 轻度异常
        if (
            vol_z >= 4 or
            oad.level == "WARN"
        ):
            return "ACTIVE"
        
        # CALM: 正常
        return "CALM"
    
    def reset(self) -> None:
        """重置分类器状态"""
        self._price_history.clear()
        logger.info("regime_classifier_reset")
