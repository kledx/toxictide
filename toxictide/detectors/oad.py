"""
TOXICTIDE Orderbook Anomaly Detector (OAD)

盘口异常检测器 - 基于稳健统计检测 orderbook 的异常状态
"""

from typing import Literal

import structlog

from toxictide.models import FeatureVector, OrderbookAnomalyReport
from toxictide.utils.rolling import RollingMAD

logger = structlog.get_logger(__name__)


class OrderbookAnomalyDetector:
    """盘口异常检测器
    
    使用 Median + MAD 稳健统计方法检测以下异常：
    1. **Spread 异常** - 价差突然扩大
    2. **Impact 异常** - 价格冲击过高（流动性枯竭）
    3. **Message Rate 异常** - 订单簿更新频率异常
    4. **Liquidity Gap** - 流动性断层（深度突然变浅）
    
    输出三级告警：
    - **OK**: 正常状态
    - **WARN**: 轻度异常（z-score >= 4）
    - **DANGER**: 严重异常（z-score >= 6 或检测到 gap）
    
    Example:
        >>> config = {"oad": {"z_warn": 4.0, "z_danger": 6.0}}
        >>> oad = OrderbookAnomalyDetector(config)
        >>> report = oad.detect(feature_vector)
        >>> print(report.level)  # "OK", "WARN", or "DANGER"
    """

    def __init__(self, config: dict) -> None:
        """初始化 OAD
        
        Args:
            config: 配置字典，需包含 oad.z_warn, oad.z_danger
        """
        self._config = config
        self._z_warn = config["oad"]["z_warn"]
        self._z_danger = config["oad"]["z_danger"]
        
        # 短窗口（5 分钟）- 快速响应
        self._rolling_short = RollingMAD(window_sec=300)
        
        # 长窗口（1 小时）- 稳定基线
        self._rolling_long = RollingMAD(window_sec=3600)
        
        logger.info(
            "oad_initialized",
            z_warn=self._z_warn,
            z_danger=self._z_danger,
        )
    
    def detect(self, fv: FeatureVector) -> OrderbookAnomalyReport:
        """检测盘口异常
        
        Args:
            fv: 特征向量
        
        Returns:
            OrderbookAnomalyReport 对象
        """
        ts = fv.ts
        
        # ========== 更新滚动统计 ==========
        
        # 短窗口（用于计算 z-score）
        self._rolling_short.update("spread_bps", fv.spread_bps, ts)
        self._rolling_short.update("impact_buy", fv.impact_buy_bps, ts)
        self._rolling_short.update("impact_sell", fv.impact_sell_bps, ts)
        self._rolling_short.update("msg_rate", fv.msg_rate, ts)
        
        # 长窗口（用于检测 gap）
        self._rolling_long.update("depth_bid", fv.depth_bid_k, ts)
        self._rolling_long.update("depth_ask", fv.depth_ask_k, ts)
        
        # ========== 计算 z-scores ==========
        
        spread_z = self._rolling_short.zscore("spread_bps")
        impact_buy_z = self._rolling_short.zscore("impact_buy")
        impact_sell_z = self._rolling_short.zscore("impact_sell")
        msg_rate_z = self._rolling_short.zscore("msg_rate")
        
        # ========== 检测流动性断层（Gap） ==========
        
        depth_bid_median = self._rolling_long.median("depth_bid")
        depth_ask_median = self._rolling_long.median("depth_ask")
        
        gap_flag = False
        
        # 若当前深度跌破长期中位数的 50%，认为是 gap
        if depth_bid_median > 0 and fv.depth_bid_k < 0.5 * depth_bid_median:
            gap_flag = True
            logger.warning(
                "liquidity_gap_detected",
                side="bid",
                current=fv.depth_bid_k,
                median=depth_bid_median,
            )
        
        if depth_ask_median > 0 and fv.depth_ask_k < 0.5 * depth_ask_median:
            gap_flag = True
            logger.warning(
                "liquidity_gap_detected",
                side="ask",
                current=fv.depth_ask_k,
                median=depth_ask_median,
            )
        
        # ========== 记录所有触发器（用于可解释性） ==========
        
        triggers = {
            "spread_z": spread_z,
            "impact_buy_z": impact_buy_z,
            "impact_sell_z": impact_sell_z,
            "msg_rate_z": msg_rate_z,
            "gap_flag": 1.0 if gap_flag else 0.0,
        }
        
        # ========== 计算综合分数 ==========
        
        # 加权组合
        score = (
            spread_z * 0.3 +                          # 价差权重 30%
            max(impact_buy_z, impact_sell_z) * 0.4 +  # 冲击权重 40%
            msg_rate_z * 0.2 +                        # 消息速率权重 20%
            (10.0 if gap_flag else 0.0)               # Gap 直接加 10 分
        )
        
        # ========== 判定告警等级 ==========
        
        if score >= self._z_danger or gap_flag:
            level: Literal["OK", "WARN", "DANGER"] = "DANGER"
        elif score >= self._z_warn:
            level = "WARN"
        else:
            level = "OK"
        
        # ========== 判定流动性状态 ==========
        
        max_impact = max(fv.impact_buy_bps, fv.impact_sell_bps)
        
        if max_impact > 20 or fv.toxic > 0.75:
            liquidity_state: Literal["THICK", "THIN", "TOXIC"] = "TOXIC"
        elif max_impact > 10:
            liquidity_state = "THIN"
        else:
            liquidity_state = "THICK"
        
        # ========== 记录日志 ==========
        
        if level != "OK":
            logger.warning(
                "orderbook_anomaly_detected",
                level=level,
                score=score,
                triggers=triggers,
                liquidity_state=liquidity_state,
            )
        
        return OrderbookAnomalyReport(
            ts=ts,
            level=level,
            score=score,
            triggers=triggers,
            liquidity_state=liquidity_state,
        )
    
    def reset(self) -> None:
        """重置检测器状态"""
        self._rolling_short.clear()
        self._rolling_long.clear()
        logger.info("oad_reset")
