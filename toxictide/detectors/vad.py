"""
TOXICTIDE Volume Anomaly Detector (VAD)

成交量异常检测器 - 检测交易流的异常模式
"""

from typing import Literal

import numpy as np
import structlog

from toxictide.models import FeatureVector, VolumeAnomalyReport
from toxictide.utils.rolling import RollingMAD

logger = structlog.get_logger(__name__)


class VolumeAnomalyDetector:
    """成交量异常检测器
    
    使用 Median + MAD 稳健统计检测以下异常：
    1. **Volume Burst** - 成交量爆发
    2. **Volume Drought** - 成交量干涸
    3. **Whale Trade** - 鲸鱼交易（单笔大额交易）
    4. **Toxic Flow** - 毒性流（买卖严重不平衡）
    
    输出三级告警：
    - **OK**: 正常状态
    - **WARN**: 轻度异常（z-score >= 4 或 toxic >= 0.6）
    - **DANGER**: 严重异常（z-score >= 6 或 toxic >= 0.75）
    
    Example:
        >>> config = {"vad": {"z_warn": 4.0, "z_danger": 6.0, 
        ...                   "toxic_warn": 0.6, "toxic_danger": 0.75}}
        >>> vad = VolumeAnomalyDetector(config)
        >>> report = vad.detect(feature_vector)
        >>> print(report.events)  # {"burst": False, "drought": False, "whale": False}
    """

    def __init__(self, config: dict) -> None:
        """初始化 VAD
        
        Args:
            config: 配置字典，需包含 vad 配置项
        """
        self._config = config
        self._z_warn = config["vad"]["z_warn"]
        self._z_danger = config["vad"]["z_danger"]
        self._toxic_warn = config["vad"]["toxic_warn"]
        self._toxic_danger = config["vad"]["toxic_danger"]
        
        # 滚动统计（5 分钟窗口）
        self._rolling = RollingMAD(window_sec=300)
        
        logger.info(
            "vad_initialized",
            z_warn=self._z_warn,
            z_danger=self._z_danger,
            toxic_warn=self._toxic_warn,
            toxic_danger=self._toxic_danger,
        )
    
    def detect(self, fv: FeatureVector) -> VolumeAnomalyReport:
        """检测成交量异常
        
        Args:
            fv: 特征向量
        
        Returns:
            VolumeAnomalyReport 对象
        """
        ts = fv.ts
        
        # ========== 更新滚动统计 ==========
        
        # 对成交量使用 log 变换（处理重尾分布）
        log_vol = np.log1p(fv.vol)  # log(1 + vol)
        
        self._rolling.update("log_vol", log_vol, ts)
        self._rolling.update("trades", float(fv.trades), ts)
        self._rolling.update("max_trade", fv.max_trade, ts)
        self._rolling.update("toxic", fv.toxic, ts)
        
        # ========== 计算 z-scores ==========
        
        vol_z = self._rolling.zscore("log_vol")
        trades_z = self._rolling.zscore("trades")
        max_trade_z = self._rolling.zscore("max_trade")
        
        # ========== 检测事件 ==========
        
        # Volume Burst: 成交量显著高于正常水平
        burst = vol_z >= self._z_warn
        
        # Volume Drought: 成交量极低或无交易
        drought = fv.vol < 0.01 or vol_z < -2.0
        
        # Whale Trade: 出现异常大的单笔交易
        whale = max_trade_z >= self._z_warn
        
        # ========== 记录触发器 ==========
        
        triggers = {
            "vol_z": vol_z,
            "trades_z": trades_z,
            "max_trade_z": max_trade_z,
            "signed_imb": fv.signed_imb,
            "toxic": fv.toxic,
        }
        
        events = {
            "burst": burst,
            "drought": drought,
            "whale": whale,
        }
        
        # ========== 计算综合分数 ==========
        
        score = (
            vol_z * 0.5 +           # 成交量权重 50%
            max_trade_z * 0.3 +     # 大单权重 30%
            fv.toxic * 10.0         # 毒性流权重（放大 10 倍）
        )
        
        # ========== 判定告警等级 ==========
        
        if score >= self._z_danger or fv.toxic >= self._toxic_danger:
            level: Literal["OK", "WARN", "DANGER"] = "DANGER"
        elif score >= self._z_warn or fv.toxic >= self._toxic_warn:
            level = "WARN"
        else:
            level = "OK"
        
        # ========== 记录日志 ==========
        
        if level != "OK" or any(events.values()):
            logger.warning(
                "volume_anomaly_detected",
                level=level,
                score=score,
                events=events,
                triggers=triggers,
            )
        
        return VolumeAnomalyReport(
            ts=ts,
            level=level,
            score=score,
            triggers=triggers,
            events=events,
        )
    
    def reset(self) -> None:
        """重置检测器状态"""
        self._rolling.clear()
        logger.info("vad_reset")
