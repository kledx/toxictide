"""
TOXICTIDE Execution Planner

执行规划器 - Impact-aware slicing 和模式选择
"""

from typing import Literal, Optional

import structlog

from toxictide.models import (
    ExecutionPlan,
    FeatureVector,
    RiskDecision,
    TradeCandidate,
    VolumeAnomalyReport,
)

logger = structlog.get_logger(__name__)


class ExecutionPlanner:
    """执行规划器

    将风控决策和交易候选转换为具体的执行计划。

    **核心功能：**

    1. **Impact-aware Slicing**
       - 高冲击 → 分片执行（降低市场冲击）
       - 低冲击 → 单笔执行（提高效率）

    2. **模式选择**
       - CALM: maker（limit 单，赚取 rebate）
       - ACTIVE: maker 或 taker（灵活选择）
       - TOXIC: taker only（market 单，快速成交）

    3. **风控拒绝处理**
       - DENY → 空计划（reduce_only 模式）

    Example:
        >>> config = {"execution": {"slicing_threshold_bps": 10.0}}
        >>> planner = ExecutionPlanner(config)
        >>> plan = planner.plan(risk_decision, candidate, fv, vad)
        >>> print(f"Mode: {plan.mode}, Orders: {len(plan.orders)}")
    """

    def __init__(self, config: dict) -> None:
        """初始化执行规划器

        Args:
            config: 配置字典，需包含 execution.slicing_threshold_bps
        """
        self._config = config
        self._slicing_threshold = config["execution"]["slicing_threshold_bps"]

        logger.info(
            "execution_planner_initialized",
            slicing_threshold=self._slicing_threshold,
        )

    def plan(
        self,
        risk: RiskDecision,
        candidate: Optional[TradeCandidate],
        fv: FeatureVector,
        vad: VolumeAnomalyReport,
    ) -> ExecutionPlan:
        """规划执行

        Args:
            risk: 风控决策
            candidate: 交易候选（可能为 None）
            fv: 特征向量
            vad: 成交量异常报告

        Returns:
            ExecutionPlan 对象
        """
        ts = fv.ts

        # ========== 风控拒绝，返回空计划 ==========

        if risk.action == "DENY":
            return ExecutionPlan(
                ts=ts,
                orders=[],
                mode="reduce_only",
                reasons=risk.reasons,
            )

        if candidate is None:
            return ExecutionPlan(
                ts=ts,
                orders=[],
                mode="reduce_only",
                reasons=["NO_SIGNAL"],
            )

        # ========== 计算 Impact 和 Toxic ==========

        impact_bps = (
            fv.impact_buy_bps if candidate.side == "long"
            else fv.impact_sell_bps
        )
        toxic = vad.triggers.get("toxic", 0.0)

        # ========== 模式 1: High Impact → Slicing ==========

        if impact_bps >= self._slicing_threshold:
            mode: Literal["maker", "taker", "slicing", "reduce_only"] = "slicing"
            num_slices = 5
            slice_size = risk.size_usd / num_slices

            orders = []
            for i in range(num_slices):
                orders.append({
                    "type": "limit",
                    "side": candidate.side,
                    "price": candidate.entry_price,
                    "size_usd": slice_size,
                    "time_delay_sec": i * 10,  # 间隔 10 秒
                })

            logger.info(
                "execution_plan_slicing",
                num_slices=num_slices,
                slice_size=slice_size,
                impact_bps=impact_bps,
            )

            return ExecutionPlan(
                ts=ts,
                orders=orders,
                mode=mode,
                reasons=["HIGH_IMPACT_SLICING"],
            )

        # ========== 模式 2: High Toxic → Taker Only ==========

        if toxic >= 0.6:
            mode = "taker"
            orders = [{
                "type": "market",
                "side": candidate.side,
                "size_usd": risk.size_usd,
                "reduce_only": False,
            }]

            logger.info(
                "execution_plan_taker",
                toxic=toxic,
                size_usd=risk.size_usd,
            )

            return ExecutionPlan(
                ts=ts,
                orders=orders,
                mode=mode,
                reasons=["TOXIC_TAKER_ONLY"],
            )

        # ========== 模式 3: Normal → Maker ==========

        mode = "maker"
        orders = [{
            "type": "limit",
            "side": candidate.side,
            "price": candidate.entry_price,
            "size_usd": risk.size_usd,
        }]

        logger.info(
            "execution_plan_maker",
            size_usd=risk.size_usd,
            entry_price=candidate.entry_price,
        )

        return ExecutionPlan(
            ts=ts,
            orders=orders,
            mode=mode,
            reasons=["NORMAL_MAKER"],
        )
