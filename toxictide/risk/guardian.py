"""
TOXICTIDE Risk Guardian

风控守护 - 系统安全核心模块
"""

import time
from typing import Optional

import structlog

from toxictide.bus import EventBus
from toxictide.models import (
    FeatureVector,
    MarketStressIndex,
    OrderbookAnomalyReport,
    RiskDecision,
    TradeCandidate,
    VolumeAnomalyReport,
)
from toxictide.risk.reason_codes import (
    COOLDOWN_ACTIVE,
    DATA_INCONSISTENT,
    DATA_STALE,
    DAILY_LOSS_EXCEEDED,
    IMPACT_ENTRY_CAP_EXCEEDED,
    IMPACT_HARD_CAP_EXCEEDED,
    MARKET_STRESS_DANGER,
    NO_SIGNAL,
    POSITION_LIMIT_EXCEEDED,
    RISK_POSITION_SIZE_REDUCED,
    TOXIC_DANGER_LEVEL,
    TOXIC_WARN_LEVEL,
    TRADE_FREQUENCY_EXCEEDED,
)
from toxictide.risk.tilt import TiltTracker

logger = structlog.get_logger(__name__)


class RiskGuardian:
    """风控守护 - 系统安全核心

    实现多层风控检查，优先级从高到低：

    **优先级 1: 数据质量检查**
    - 数据过期（超过阈值秒数未更新）
    - Orderbook 不一致（spread <= 0）

    **优先级 2: 日亏熔断**
    - 日盈亏 < -max_daily_loss_pct → 禁止新开仓

    **优先级 3: 冷却期**
    - 连续亏损后触发冷却，期间禁止新开仓

    **优先级 4: 仓位上限**
    - position_notional >= max_position_notional → 拒绝

    **优先级 5: Impact/Toxic 检查**
    - impact > hard_cap → DENY
    - impact > entry_cap → ALLOW_WITH_REDUCTIONS（减仓）
    - toxic >= toxic_danger → DENY

    **优先级 6: Market Stress**
    - stress.level == DANGER → 拒绝新开仓

    **优先级 7: 交易频率限制**
    - trades_last_hour >= max_trades_per_hour → 拒绝

    **允许交易，但可能减仓**
    - 基于 impact/toxic/stress 调整仓位大小
    """

    def __init__(self, config: dict, bus: EventBus) -> None:
        """初始化风控守护

        Args:
            config: 配置字典
            bus: 事件总线
        """
        self._config = config
        self._bus = bus
        self._tilt = TiltTracker()
        self._cooldown_until: Optional[float] = None
        self._last_book_update_ts: float = time.time()

        logger.info("risk_guardian_initialized")

    def assess(
        self,
        candidate: Optional[TradeCandidate],
        fv: FeatureVector,
        oad: OrderbookAnomalyReport,
        vad: VolumeAnomalyReport,
        stress: MarketStressIndex,
        account: dict,
        policy: dict,
    ) -> RiskDecision:
        """评估风险并做出决策"""
        ts = fv.ts
        reasons: list[str] = []
        facts: dict[str, float] = {}

        # 无信号直接返回
        if candidate is None:
            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=[NO_SIGNAL],
                facts={},
            )

        # 优先级 1: 数据质量检查
        data_stale_threshold = 10.0
        if ts - self._last_book_update_ts > data_stale_threshold:
            reasons.append(DATA_STALE)
            facts["stale_sec"] = ts - self._last_book_update_ts

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        if fv.spread <= 0:
            reasons.append(DATA_INCONSISTENT)
            facts["spread"] = fv.spread

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        # 优先级 2: 日亏熔断
        balance = account.get("balance", 10000.0)
        daily_pnl_pct = self._tilt.daily_pnl_pct(balance)
        max_daily_loss_pct = policy.get("max_daily_loss_pct", 1.0)

        facts["daily_pnl_pct"] = daily_pnl_pct
        facts["max_daily_loss_pct"] = max_daily_loss_pct

        if daily_pnl_pct < -max_daily_loss_pct:
            reasons.append(DAILY_LOSS_EXCEEDED)

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        # 优先级 3: 冷却期
        if self._cooldown_until and ts < self._cooldown_until:
            reasons.append(COOLDOWN_ACTIVE)
            facts["cooldown_remaining_sec"] = self._cooldown_until - ts

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        # 优先级 4: 仓位上限
        position_notional = account.get("position_notional", 0.0)
        max_position_notional = policy.get("max_position_notional", 3000.0)

        facts["position_notional"] = position_notional
        facts["max_position_notional"] = max_position_notional

        if position_notional >= max_position_notional:
            reasons.append(POSITION_LIMIT_EXCEEDED)

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        # 优先级 5: Impact / Toxic 检查
        impact_bps = (
            fv.impact_buy_bps if candidate.side == "long"
            else fv.impact_sell_bps
        )
        toxic = vad.triggers.get("toxic", 0.0)

        impact_hard_cap = policy.get("impact_hard_cap_bps", 20.0)
        impact_entry_cap = policy.get("impact_entry_cap_bps", 10.0)
        toxic_danger = self._config["vad"]["toxic_danger"]

        facts["impact_bps"] = impact_bps
        facts["toxic"] = toxic
        facts["hard_cap_bps"] = impact_hard_cap
        facts["entry_cap_bps"] = impact_entry_cap
        facts["toxic_danger"] = toxic_danger

        if impact_bps > impact_hard_cap:
            reasons.append(IMPACT_HARD_CAP_EXCEEDED)

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        if toxic >= toxic_danger:
            reasons.append(TOXIC_DANGER_LEVEL)

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        # 优先级 6: Market Stress
        if stress.level == "DANGER":
            reasons.append(MARKET_STRESS_DANGER)

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        # 优先级 7: 交易频率限制
        trades_last_hour = self._tilt.trades_last_hour(ts)
        max_trades_per_hour = policy.get("max_trades_per_hour", 6)

        facts["trades_last_hour"] = trades_last_hour
        facts["max_trades_per_hour"] = max_trades_per_hour

        if trades_last_hour >= max_trades_per_hour:
            reasons.append(TRADE_FREQUENCY_EXCEEDED)

            return RiskDecision(
                ts=ts,
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=reasons,
                facts=facts,
            )

        # 允许交易，但可能减仓
        max_position = policy.get("max_position_notional", 3000.0)
        base_size = min(1000.0, max_position - position_notional)

        size_multiplier = 1.0

        if impact_bps > impact_entry_cap:
            size_multiplier *= 0.5
            reasons.append(IMPACT_ENTRY_CAP_EXCEEDED)

        toxic_warn = self._config["vad"]["toxic_warn"]
        if toxic >= toxic_warn:
            size_multiplier *= 0.7
            reasons.append(TOXIC_WARN_LEVEL)
            facts["toxic_warn"] = toxic_warn

        if stress.level == "WARN":
            size_multiplier *= 0.5

        final_size = base_size * size_multiplier

        if size_multiplier < 1.0:
            action = "ALLOW_WITH_REDUCTIONS"
            facts["original_size"] = base_size
            facts["reduced_size"] = final_size
            reasons.append(RISK_POSITION_SIZE_REDUCED)
        else:
            action = "ALLOW"

        max_slippage_bps = min(impact_bps * 1.5, 15.0)

        return RiskDecision(
            ts=ts,
            action=action,
            size_usd=final_size,
            max_slippage_bps=max_slippage_bps,
            reasons=reasons,
            facts=facts,
        )

    def trigger_cooldown(self, duration_sec: float) -> None:
        """触发冷却期"""
        self._cooldown_until = time.time() + duration_sec
        logger.warning("cooldown_triggered", duration_sec=duration_sec)

    def update_book_timestamp(self, ts: float) -> None:
        """更新最后一次盘口更新时间"""
        self._last_book_update_ts = ts

    def record_trade(self, ts: float, pnl: float) -> None:
        """记录交易"""
        self._tilt.record_trade(ts, pnl)

    @property
    def tilt_tracker(self) -> TiltTracker:
        """获取 Tilt Tracker"""
        return self._tilt
