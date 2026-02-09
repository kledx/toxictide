"""
TOXICTIDE Orchestrator

主循环调度器 - 系统核心
"""

import time

import structlog

from toxictide.bus import get_bus
from toxictide.detectors.oad import OrderbookAnomalyDetector
from toxictide.detectors.stress import compute_stress
from toxictide.detectors.vad import VolumeAnomalyDetector
from toxictide.execution.adapter_paper import PaperExecutionAdapter
from toxictide.execution.planner import ExecutionPlanner
from toxictide.explain.explain import build_explanation
from toxictide.features.feature_engine import FeatureEngine
from toxictide.ledger.ledger import Ledger
from toxictide.market.collector import PaperMarketCollector
from toxictide.market.orderbook import OrderBook
from toxictide.market.tape import TradeTape
from toxictide.models import LedgerRecord, ExecutionPlan
from toxictide.regime.regime import RegimeClassifier
from toxictide.risk.guardian import RiskGuardian
from toxictide.state import SystemState
from toxictide.strategy.signals import SignalEngine
from toxictide.position.manager import PositionManager
from toxictide.position.monitor import PositionMonitor

logger = structlog.get_logger(__name__)


class Orchestrator:
    """主循环调度器

    整合所有模块，实现完整的交易系统主循环。

    **主循环流程（1 秒 tick）：**
    1. 更新市场数据（orderbook + trades）
    2. 计算特征向量
    3. 异常检测（OAD + VAD + Stress）
    4. 市场状态分类（Regime）
    5. 生成交易信号（Signal）
    6. 风控评估（Risk Guardian）
    7. 执行规划（Execution Planner）
    8. 订单执行（Adapter）
    9. 审计记录（Ledger）
    10. 发布事件（Event Bus）

    Example:
        >>> config = load_config("config.yaml")
        >>> orch = Orchestrator(config)
        >>> orch.run()  # 启动主循环
    """

    def __init__(self, config: dict, real_collector=None) -> None:
        """初始化 Orchestrator

        Args:
            config: 配置字典
            real_collector: 可选的真实数据采集器（BinanceMarketCollectorSync）
                          如果提供，则使用真实数据；否则使用模拟数据
        """
        self._config = config
        self._bus = get_bus()
        self._state = SystemState()

        # ========== 初始化所有模块 ==========

        # 数据层 - 支持真实数据或模拟数据
        self._real_collector = real_collector  # 真实数据采集器（可选）
        self._collector = PaperMarketCollector(
            base_price=2000.0,
            volatility=0.002,  # Increased volatility for demo
            spread_bps=5.0,
            depth_levels=20,
        )
        self._orderbook = OrderBook()
        self._tape = TradeTape(window_sec=300)

        # 特征引擎
        self._feature_engine = FeatureEngine(config)

        # 异常检测
        self._oad = OrderbookAnomalyDetector(config)
        self._vad = VolumeAnomalyDetector(config)

        # Regime & Strategy
        self._regime = RegimeClassifier(config)
        self._signal_engine = SignalEngine(config)

        # 风控
        self._risk_guardian = RiskGuardian(config, self._bus)

        # 执行
        self._planner = ExecutionPlanner(config)
        self._adapter = PaperExecutionAdapter(initial_balance=10000.0)

        # 审计
        self._ledger = Ledger(log_dir="logs")

        # ========== 持仓管理（新增）==========
        self._position_manager = PositionManager()
        self._position_monitor = PositionMonitor(
            position_manager=self._position_manager,
            max_hold_time_sec=3600,  # 最大持有 1 小时
        )

        # ========== 默认 Policy ==========

        self._state.policy = {
            "max_daily_loss_pct": 1.0,
            "max_position_notional": 3000.0,
            "max_trades_per_hour": 6,
            "impact_hard_cap_bps": 20.0,
            "impact_entry_cap_bps": 10.0,
            "allowed_strategies": ["trend_breakout", "range_mean_revert"],
        }

        logger.info("orchestrator_initialized")

    def run(self) -> None:
        """启动主循环"""
        logger.info("orchestrator_started")

        try:
            while self._state.running:
                tick_start = time.time()

                if not self._state.paused:
                    self._tick()

                # 1 秒 tick
                elapsed = time.time() - tick_start
                sleep_time = max(0, 1.0 - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("keyboard_interrupt_received")
            self._state.running = False
        except Exception as e:
            logger.error("orchestrator_error", error=str(e), exc_info=True)
            raise
        finally:
            self._shutdown()

    def _tick(self) -> None:
        """单次 tick（核心逻辑）"""
        ts = time.time()

        try:
            # ========== 1. 更新市场数据 ==========

            # 根据是否有真实数据采集器选择数据源
            # 根据是否有真实数据采集器选择数据源
            if self._real_collector:
                # 使用真实数据
                book_state = self._real_collector.get_orderbook_snapshot()
                if not book_state:
                    logger.warning("no_orderbook_data_from_real_collector")
                    return

                # 获取最近的交易数据
                recent_trades = self._real_collector.get_recent_trades(max_count=100)
                for trade in recent_trades:
                    self._tape.add(trade)
            else:
                # 使用模拟数据
                book_state = self._collector.get_orderbook_snapshot()
                trade = self._collector.generate_single_trade()
                self._tape.add(trade)

            self._orderbook.apply_snapshot(book_state.bids, book_state.asks, book_state.seq)
            self._risk_guardian.update_book_timestamp(ts)

            # ========== 2. 计算特征 ==========

            fv = self._feature_engine.compute(self._orderbook, self._tape, ts)
            self._state.last_features = fv
            self._bus.publish("features", fv)

            # ========== 3. 异常检测 ==========

            oad = self._oad.detect(fv)
            vad = self._vad.detect(fv)
            stress = compute_stress(oad, vad, self._config)

            self._state.last_stress = stress

            self._bus.publish("oad", oad)
            self._bus.publish("vad", vad)
            self._bus.publish("stress", stress)

            # ========== 4. Regime ==========

            regime = self._regime.classify(fv, oad, vad)
            self._state.last_regime = regime
            self._bus.publish("regime", regime)

            # ========== 5. Signal ==========

            candidate = self._signal_engine.generate(fv, regime, self._state.policy)
            self._bus.publish("signal", candidate)

            # ========== 6. Risk ==========

            account = self._adapter.get_account_state(current_price=fv.mid)
            risk = self._risk_guardian.assess(
                candidate, fv, oad, vad, stress, account, self._state.policy
            )

            self._state.last_decision = risk
            self._bus.publish("risk", risk)

            # ========== 7. Plan ==========

            plan = self._planner.plan(risk, candidate, fv, vad)
            self._bus.publish("plan", plan)

            # ========== 8. Execute ==========

            fills = []
            if risk.action in ["ALLOW", "ALLOW_WITH_REDUCTIONS"] and plan.orders:
                fills = self._adapter.execute(plan)
                for fill in fills:
                    self._bus.publish("fill", fill)
                    # 记录到 tilt tracker（简化：pnl=0）
                    self._risk_guardian.record_trade(ts, pnl=0.0)

                # 开仓：记录到持仓管理器
                if fills and candidate:
                    position = self._position_manager.open_position(
                        candidate=candidate,
                        fills=fills,
                        size_usd=risk.size_usd,
                    )
                    logger.info("position_opened", position_id=position.position_id)

            # ========== 8.5. 持仓监控和止损执行（新增）==========

            current_price = fv.mid
            positions_to_close = self._position_monitor.check_positions(
                current_price=current_price,
                current_time=ts,
            )

            # 执行止损/止盈平仓
            for position_id, reason, close_price in positions_to_close:
                # 生成平仓计划
                position = self._position_manager.get_position(position_id)
                if not position:
                    continue

                # 创建平仓执行计划
                close_plan = ExecutionPlan(
                    ts=ts,
                    orders=[{
                        "type": "market",
                        "side": "sell" if position.side == "long" else "buy",
                        "size_usd": position.size_usd,
                        "reduce_only": True,
                    }],
                    mode="taker",
                    reasons=[f"CLOSE_{reason.upper()}"],
                )

                # 执行平仓
                close_fills = self._adapter.execute(close_plan)

                # 更新持仓状态
                closed_position = self._position_manager.close_position(
                    position_id=position_id,
                    close_price=close_price,
                    close_time=ts,
                    reason=reason,
                )

                if closed_position:
                    # 记录盈亏到风控系统
                    self._risk_guardian.record_trade(ts, pnl=closed_position.pnl or 0.0)

                    logger.info(
                        "position_closed_by_monitor",
                        position_id=position_id,
                        reason=reason,
                        pnl=closed_position.pnl,
                    )

            # ========== 9. Ledger ==========

            explain_text = build_explanation(risk)

            record = LedgerRecord(
                ts=ts,
                policy=self._state.policy,
                features=fv,
                oad=oad,
                vad=vad,
                stress=stress,
                regime=regime,
                signal=candidate,
                risk=risk,
                plan=plan,
                fills=fills,
                explain=explain_text,
            )

            self._ledger.append(record)
            self._ledger.append(record)
            self._bus.publish("ledger", record)

            # ========== 9.5. Positions ==========
            # publish active positions for UI
            active_positions = self._position_manager.get_active_positions()
            # Convert to list of dicts for JSON serialization if needed, 
            # but Pydantic models are usually handled by the bus/serializer
            self._bus.publish("positions", active_positions)

            # ========== 9.6. Account ==========
            # publish account state for UI (balance, equity, etc.)
            account_state = self._adapter.get_account_state(current_price=fv.mid)
            # logger.info("broadcasting_account_state", balance=account_state.get('balance'), pnl=account_state.get('unrealized_pnl'))
            self._bus.publish("account", account_state)

            # ========== 10. 日志 (优化版) ==========

            # 仅在以下情况记录日志：
            # 1. 有交易信号
            # 2. 风控有动作（非 DENY，或者 DENY 但不是因为 TOXIC）
            # 3. 每 10 秒一次的心跳
            
            is_important = False
            if candidate:
                is_important = True
            if risk.action != "DENY":
                is_important = True
            
            # 每 10s 强制记录一次心跳
            if int(ts) % 10 == 0 or is_important:
                logger.info(
                    "tick",
                    ts=ts,
                    stress=stress.level,
                    regime=f"{regime.price_regime}/{regime.flow_regime}",
                    signal=candidate.strategy if candidate else "none",
                    risk=risk.action,
                )

        except Exception as e:
            logger.error("tick_error", error=str(e), exc_info=True)

    def _shutdown(self) -> None:
        """优雅关闭"""
        logger.info("orchestrator_shutting_down")

        # 关闭审计日志
        self._ledger.close()

        logger.info("orchestrator_stopped")

    @property
    def state(self) -> SystemState:
        """获取系统状态"""
        return self._state
