"""
TOXICTIDE System State

全局状态管理
"""

from typing import Optional

from toxictide.models import (
    FeatureVector,
    MarketStressIndex,
    RegimeState,
    RiskDecision,
)


class SystemState:
    """系统全局状态

    用于模块间状态共享和 UI 显示。

    **状态字段：**
    - running: 系统是否运行
    - paused: 是否暂停交易
    - policy: 当前策略配置
    - last_features: 最新市场特征
    - last_stress: 最新市场压力指数
    - last_regime: 最新市场状态
    - last_decision: 最新风控决策

    Example:
        >>> state = SystemState()
        >>> state.running = True
        >>> state.policy = {"max_daily_loss_pct": 1.0}
    """

    def __init__(self) -> None:
        """初始化系统状态"""
        self.running: bool = True
        self.paused: bool = False

        # 策略配置
        self.policy: dict = {}

        # 最新状态（用于 UI 显示）
        self.last_features: Optional[FeatureVector] = None
        self.last_stress: Optional[MarketStressIndex] = None
        self.last_regime: Optional[RegimeState] = None
        self.last_decision: Optional[RiskDecision] = None
