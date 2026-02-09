"""
TOXICTIDE Risk Decision Reason Codes

统一的风控拒绝原因编码系统
"""

# ========== 数据质量异常 ==========

DATA_INCONSISTENT = "DATA_INCONSISTENT"
"""数据不一致（spread < 0 或排序错误）"""

DATA_STALE = "DATA_STALE"
"""数据过期（超过 N 秒未更新）"""

CONNECTION_LOST = "CONNECTION_LOST"
"""连接断开，暂停新开仓"""

# ========== 熔断机制 ==========

DAILY_LOSS_EXCEEDED = "DAILY_LOSS_EXCEEDED"
"""日亏超限"""

COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"
"""冷却期激活"""

# ========== 仓位限制 ==========

POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
"""仓位超限"""

LEVERAGE_LIMIT_EXCEEDED = "LEVERAGE_LIMIT_EXCEEDED"
"""杠杆超限"""

# ========== 市场条件 ==========

IMPACT_HARD_CAP_EXCEEDED = "IMPACT_HARD_CAP_EXCEEDED"
"""冲击成本过高（硬上限）"""

IMPACT_ENTRY_CAP_EXCEEDED = "IMPACT_ENTRY_CAP_EXCEEDED"
"""冲击成本偏高（入场上限），已减仓"""

TOXIC_DANGER_LEVEL = "TOXIC_DANGER_LEVEL"
"""毒性流过高"""

TOXIC_WARN_LEVEL = "TOXIC_WARN_LEVEL"
"""毒性流偏高，已减仓"""

MARKET_STRESS_DANGER = "MARKET_STRESS_DANGER"
"""市场压力指数 DANGER，暂停新开仓"""

# ========== 行为约束 ==========

TRADE_FREQUENCY_EXCEEDED = "TRADE_FREQUENCY_EXCEEDED"
"""交易频率超限"""

# ========== 仓位调整 ==========

RISK_POSITION_SIZE_REDUCED = "RISK_POSITION_SIZE_REDUCED"
"""基于市场条件，仓位已调整"""

RISK_LEVERAGE_REDUCED = "RISK_LEVERAGE_REDUCED"
"""基于风险评估，杠杆已降低"""

# ========== 其他 ==========

NO_SIGNAL = "NO_SIGNAL"
"""无交易信号"""


def format_reason(code: str, facts: dict) -> str:
    """格式化原因说明
    
    Args:
        code: 原因编码
        facts: 事实数据字典
    
    Returns:
        人类可读的解释文本
    
    Example:
        >>> facts = {"daily_pnl_pct": -1.5, "max_daily_loss_pct": 1.0}
        >>> text = format_reason(DAILY_LOSS_EXCEEDED, facts)
        >>> print(text)
        日亏超限（当前 -1.50% < 阈值 -1.00%）
    """
    # 安全地获取数值，避免格式化错误
    def safe_format(key, default=0, fmt='.2f'):
        """安全格式化 - 确保总是返回数字"""
        try:
            val = facts.get(key, default)
            if isinstance(val, (int, float)):
                return format(val, fmt)
            return str(default)
        except:
            return str(default)

    messages = {
        DATA_INCONSISTENT: "市场数据不一致（spread < 0 或排序错误）",

        DATA_STALE: f"数据过期（超过 {safe_format('stale_sec', 0, '.1f')} 秒未更新）",

        CONNECTION_LOST: "连接断开，暂停新开仓",

        DAILY_LOSS_EXCEEDED: (
            f"日亏超限（当前 {safe_format('daily_pnl_pct', 0, '.2f')}% "
            f"< 阈值 -{safe_format('max_daily_loss_pct', 0, '.2f')}%）"
        ),

        COOLDOWN_ACTIVE: (
            f"冷却期激活（剩余 {safe_format('cooldown_remaining_sec', 0, '.0f')} 秒）"
        ),

        POSITION_LIMIT_EXCEEDED: (
            f"仓位超限（当前 ${safe_format('position_notional', 0, '.0f')} "
            f"> 上限 ${safe_format('max_position_notional', 0, '.0f')}）"
        ),

        LEVERAGE_LIMIT_EXCEEDED: (
            f"杠杆超限（当前 {safe_format('leverage', 0, '.1f')}x "
            f"> 上限 {safe_format('max_leverage', 0, '.1f')}x）"
        ),

        IMPACT_HARD_CAP_EXCEEDED: (
            f"冲击成本过高（{safe_format('impact_bps', 0, '.2f')} bps "
            f"> 硬上限 {safe_format('hard_cap_bps', 0, '.2f')} bps）"
        ),

        IMPACT_ENTRY_CAP_EXCEEDED: (
            f"冲击成本偏高（{safe_format('impact_bps', 0, '.2f')} bps "
            f"> 入场上限 {safe_format('entry_cap_bps', 0, '.2f')} bps），已减仓"
        ),

        TOXIC_DANGER_LEVEL: (
            f"毒性流过高（toxic={safe_format('toxic', 0, '.2f')} "
            f">= {safe_format('toxic_danger', 0, '.2f')}）"
        ),

        TOXIC_WARN_LEVEL: (
            f"毒性流偏高（toxic={safe_format('toxic', 0, '.2f')} "
            f">= {safe_format('toxic_warn', 0, '.2f')}），已减仓"
        ),

        MARKET_STRESS_DANGER: "市场压力指数 DANGER，暂停新开仓",

        TRADE_FREQUENCY_EXCEEDED: (
            f"交易频率超限（{safe_format('trades_last_hour', 0, '.0f')} "
            f"> {safe_format('max_trades_per_hour', 0, '.0f')}）"
        ),

        RISK_POSITION_SIZE_REDUCED: (
            f"基于市场条件，仓位已从 ${safe_format('original_size', 0, '.2f')} "
            f"降至 ${safe_format('reduced_size', 0, '.2f')}"
        ),

        RISK_LEVERAGE_REDUCED: (
            f"基于风险评估，杠杆已从 {safe_format('original_leverage', 0, '.1f')}x "
            f"降至 {safe_format('reduced_leverage', 0, '.1f')}x"
        ),

        NO_SIGNAL: "无交易信号",
    }
    
    return messages.get(code, code)
