"""
TOXICTIDE Price Impact Estimation

价格冲击估计 - 评估大单对市场价格的影响
"""

from typing import Literal

import structlog

from toxictide.models import OrderBookLevel

logger = structlog.get_logger(__name__)


def estimate_impact_bps(
    levels: list[OrderBookLevel],
    side: Literal["buy", "sell"],
    qty_usd: float,
    mid: float,
) -> float:
    """估计价格冲击（以 bps 计）
    
    计算消耗指定 USD 深度后的平均成交价格相对中间价的偏离。
    
    Args:
        levels: Orderbook 价位列表
            - 若 side="buy"，传入 asks（卖单）
            - 若 side="sell"，传入 bids（买单）
        side: 交易方向
        qty_usd: 目标成交金额（USD）
        mid: 中间价（用于计算偏离）
    
    Returns:
        价格冲击（bps），范围 [0, 9999.9]
        - 若流动性充足，返回实际冲击
        - 若流动性不足，返回 9999.9（表示无法完成）
    
    Example:
        >>> asks = [
        ...     OrderBookLevel(price=100.0, size=10.0),
        ...     OrderBookLevel(price=101.0, size=20.0),
        ... ]
        >>> impact = estimate_impact_bps(asks, "buy", 1000.0, 99.5)
        >>> print(f"Impact: {impact:.2f} bps")
    
    算法：
        1. 逐档消耗订单簿，累计 total_cost 和 consumed_usd
        2. 若流动性不足（remaining > 0），返回 9999.9
        3. 计算平均成交价：avg_price = total_cost / qty_usd
        4. 计算相对 mid 的偏离（bps）
    """
    if qty_usd <= 0:
        return 0.0
    
    if not levels:
        logger.warning("impact_empty_levels", side=side, qty_usd=qty_usd)
        return 9999.9
    
    remaining_usd = qty_usd
    total_cost = 0.0  # 总消耗（包含价格变动）
    
    for level in levels:
        if remaining_usd <= 0:
            break
        
        # 本档可提供的 USD 深度
        level_usd = level.price * level.size
        
        # 本档消耗的 USD
        consumed_usd = min(remaining_usd, level_usd)
        
        # 累计成本
        total_cost += consumed_usd
        remaining_usd -= consumed_usd
    
    # 流动性不足
    if remaining_usd > 0:
        logger.warning(
            "insufficient_liquidity",
            side=side,
            qty_usd=qty_usd,
            remaining_usd=remaining_usd,
        )
        return 9999.9
    
    # 计算平均成交价
    avg_price = total_cost / qty_usd if qty_usd > 0 else mid
    
    # 计算相对 mid 的偏离（bps）
    if side == "buy":
        # 买入：avg_price 应该 > mid（支付更高价格）
        impact_bps = ((avg_price - mid) / mid) * 10000
    else:  # sell
        # 卖出：avg_price 应该 < mid（获得更低价格）
        impact_bps = ((mid - avg_price) / mid) * 10000
    
    # 确保非负
    impact_bps = max(0.0, impact_bps)
    
    return impact_bps


def estimate_market_depth_usd(
    levels: list[OrderBookLevel],
    max_impact_bps: float,
    mid: float,
    side: Literal["buy", "sell"],
) -> float:
    """估计在指定冲击上限下的可用深度（USD）
    
    反向计算：给定最大可接受冲击，能执行多大的订单？
    
    Args:
        levels: Orderbook 价位列表
        max_impact_bps: 最大可接受冲击（bps）
        mid: 中间价
        side: 交易方向
    
    Returns:
        可用深度（USD）
    
    Example:
        >>> asks = [OrderBookLevel(price=100.0, size=10.0)]
        >>> depth = estimate_market_depth_usd(asks, 50.0, 99.5, "buy")
    """
    if max_impact_bps <= 0:
        return 0.0
    
    if not levels:
        return 0.0
    
    # 二分搜索找到最大可用 USD
    low, high = 0.0, sum(l.price * l.size for l in levels)
    tolerance = 1.0  # USD
    
    while high - low > tolerance:
        mid_qty = (low + high) / 2
        impact = estimate_impact_bps(levels, side, mid_qty, mid)
        
        if impact <= max_impact_bps:
            low = mid_qty  # 可以更大
        else:
            high = mid_qty  # 太大了
    
    return low


def estimate_slippage_bps(
    fill_price: float,
    reference_price: float,
    side: Literal["buy", "sell"],
) -> float:
    """计算实际滑点（事后分析）
    
    Args:
        fill_price: 实际成交价
        reference_price: 参考价（通常是决策时的 mid）
        side: 交易方向
    
    Returns:
        滑点（bps），正值表示不利滑点
    
    Example:
        >>> slippage = estimate_slippage_bps(100.5, 100.0, "buy")
        >>> print(f"Slippage: {slippage:.2f} bps")  # 50.0 bps
    """
    if side == "buy":
        # 买入：支付更高价格 = 正滑点
        slippage = ((fill_price - reference_price) / reference_price) * 10000
    else:
        # 卖出：获得更低价格 = 正滑点
        slippage = ((reference_price - fill_price) / reference_price) * 10000
    
    return slippage
