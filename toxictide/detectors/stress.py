"""
TOXICTIDE Market Stress Index

市场压力综合指数 - 综合 OAD 和 VAD 的结果
"""

import structlog

from toxictide.models import (
    MarketStressIndex,
    OrderbookAnomalyReport,
    VolumeAnomalyReport,
)

logger = structlog.get_logger(__name__)


def compute_stress(
    oad: OrderbookAnomalyReport,
    vad: VolumeAnomalyReport,
    config: dict,
) -> MarketStressIndex:
    """计算市场压力综合指数
    
    综合 OAD（盘口异常）和 VAD（成交量异常）的检测结果，
    计算加权综合分数和最终风险等级。
    
    Args:
        oad: 盘口异常报告
        vad: 成交量异常报告
        config: 配置字典
    
    Returns:
        MarketStressIndex 对象
    
    算法：
        1. 提取各组件得分
        2. 加权计算综合分数
        3. 取 OAD 和 VAD 中的最高风险等级
    
    Example:
        >>> stress = compute_stress(oad_report, vad_report, config)
        >>> if stress.level == "DANGER":
        ...     print("市场压力极高，暂停交易")
    """
    
    # ========== 提取组件得分 ==========
    
    oad_score = oad.score
    vad_score = vad.score
    
    # 从 triggers 中提取关键指标
    spread_z = oad.triggers.get("spread_z", 0.0)
    impact_buy_z = oad.triggers.get("impact_buy_z", 0.0)
    impact_sell_z = oad.triggers.get("impact_sell_z", 0.0)
    impact_z = max(impact_buy_z, impact_sell_z)
    
    toxic = vad.triggers.get("toxic", 0.0)
    vol_z = vad.triggers.get("vol_z", 0.0)
    
    components = {
        "oad_score": oad_score,
        "vad_score": vad_score,
        "spread_z": spread_z,
        "impact_z": impact_z,
        "toxic": toxic,
        "vol_z": vol_z,
    }
    
    # ========== 计算综合分数 ==========
    
    # 加权组合
    score = (
        oad_score * 0.5 +     # OAD 权重 50%
        vad_score * 0.3 +     # VAD 权重 30%
        toxic * 5.0           # Toxic 权重（放大 5 倍）
    )
    
    # ========== 判定风险等级 ==========
    
    # 取 OAD 和 VAD 中的最高风险等级
    levels_priority = {"OK": 0, "WARN": 1, "DANGER": 2}
    
    max_level = max(
        oad.level,
        vad.level,
        key=lambda x: levels_priority[x]
    )
    
    # ========== 记录日志 ==========
    
    if max_level != "OK":
        logger.warning(
            "market_stress_elevated",
            level=max_level,
            score=score,
            oad_level=oad.level,
            vad_level=vad.level,
            components=components,
        )
    
    return MarketStressIndex(
        ts=oad.ts,
        level=max_level,
        score=score,
        components=components,
    )
