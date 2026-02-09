"""
TOXICTIDE Feature Engine

特征计算引擎 - 从 Orderbook 和 Trade Tape 提取市场微观结构特征
"""

import time

import structlog

from toxictide.features.impact import estimate_impact_bps
from toxictide.market.orderbook import OrderBook
from toxictide.market.tape import TradeTape
from toxictide.models import FeatureVector

logger = structlog.get_logger(__name__)


class FeatureEngine:
    """特征计算引擎
    
    从市场数据中提取特征向量，用于异常检测和策略决策。
    
    包含两大类特征：
    1. Orderbook 特征：spread, depth, imbalance, microprice, impact
    2. Trade 特征：volume, trades, buy/sell split, toxic score
    
    Example:
        >>> config = {"features": {"impact_size_quote_usd": 1000}}
        >>> engine = FeatureEngine(config)
        >>> fv = engine.compute(orderbook, tape, time.time())
        >>> print(f"Spread: {fv.spread_bps:.2f} bps")
    """

    def __init__(self, config: dict) -> None:
        """初始化特征引擎
        
        Args:
            config: 配置字典，需包含 features.impact_size_quote_usd
        """
        self._config = config
        self._impact_size_usd = config["features"]["impact_size_quote_usd"]
        
        # 状态跟踪（用于计算变化率）
        self._last_depth_bid = 0.0
        self._last_depth_ask = 0.0
        self._msg_count = 0
        self._last_msg_ts = time.time()
        
        logger.info(
            "feature_engine_initialized",
            impact_size_usd=self._impact_size_usd,
        )
    
    def compute(
        self,
        book: OrderBook,
        tape: TradeTape,
        ts: float,
    ) -> FeatureVector:
        """计算完整特征向量
        
        Args:
            book: OrderBook 对象
            tape: TradeTape 对象
            ts: 当前时间戳
        
        Returns:
            FeatureVector 对象
        """
        book_state = book.get_state()
        
        if not book_state.bids or not book_state.asks:
            logger.warning("empty_orderbook", ts=ts)
            # 返回空特征（所有值为 0）
            return self._empty_features(ts)
        
        # ========== Orderbook 特征 ==========
        
        # 基础价格和价差
        mid = book_state.mid
        spread = book_state.spread
        spread_bps = (spread / mid) * 10000 if mid > 0 else 0.0
        
        # Top of book
        top_bid = book_state.bids[0]
        top_ask = book_state.asks[0]
        
        # 深度计算（取前 K 档，K 通常为 20）
        levels_to_use = min(20, len(book_state.bids), len(book_state.asks))
        bids_k = book_state.bids[:levels_to_use]
        asks_k = book_state.asks[:levels_to_use]
        
        # USD 深度（价格 * 数量）
        depth_bid_k = sum(b.price * b.size for b in bids_k)
        depth_ask_k = sum(a.price * a.size for a in asks_k)
        
        # 盘口不平衡 imbalance（-1 到 1）
        # > 0 表示买盘深度更厚，< 0 表示卖盘深度更厚
        imb_k = (depth_bid_k - depth_ask_k) / (depth_bid_k + depth_ask_k + 1e-9)
        
        # Microprice（基于 top of book 的加权价格）
        bid_sz = top_bid.size
        ask_sz = top_ask.size
        micro = (
            (top_ask.price * bid_sz + top_bid.price * ask_sz) 
            / (bid_sz + ask_sz + 1e-9)
        )
        micro_minus_mid = micro - mid
        
        # Price Impact 估计
        impact_buy_bps = estimate_impact_bps(
            levels=asks_k,
            side="buy",
            qty_usd=self._impact_size_usd,
            mid=mid,
        )
        
        impact_sell_bps = estimate_impact_bps(
            levels=bids_k,
            side="sell",
            qty_usd=self._impact_size_usd,
            mid=mid,
        )
        
        # Message rate（订单簿更新速率）
        self._msg_count += 1
        time_elapsed = ts - self._last_msg_ts
        if time_elapsed > 0:
            msg_rate = self._msg_count / time_elapsed
        else:
            msg_rate = 0.0
        
        # Churn（盘口深度变动）
        churn = (
            abs(depth_bid_k - self._last_depth_bid) 
            + abs(depth_ask_k - self._last_depth_ask)
        )
        
        # 更新状态
        self._last_depth_bid = depth_bid_k
        self._last_depth_ask = depth_ask_k
        
        # ========== Trade 特征 ==========
        
        # 最近 1 分钟的交易聚合
        agg = tape.aggregate(sec=60)
        
        vol = agg.vol
        trades = agg.trades
        avg_trade = agg.avg_trade
        max_trade = agg.max_trade
        
        buy_vol = agg.buy_vol
        sell_vol = agg.sell_vol
        
        # 带符号不平衡（-1 到 1）
        # > 0 表示买方主动性更强
        signed_imb = agg.signed_imbalance
        
        # Toxic score（简化 VPIN）
        # MVP: 使用 |signed_imbalance| 作为毒性流指标
        # 未来可扩展为完整 VPIN 计算
        toxic = abs(signed_imb)
        
        # ========== 构建特征向量 ==========
        
        return FeatureVector(
            ts=ts,
            # Orderbook features
            mid=mid,
            spread=spread,
            spread_bps=spread_bps,
            top_bid_sz=top_bid.size,
            top_ask_sz=top_ask.size,
            depth_bid_k=depth_bid_k,
            depth_ask_k=depth_ask_k,
            imb_k=imb_k,
            micro_minus_mid=micro_minus_mid,
            impact_buy_bps=impact_buy_bps,
            impact_sell_bps=impact_sell_bps,
            msg_rate=msg_rate,
            churn=churn,
            # Trade features
            vol=vol,
            trades=trades,
            avg_trade=avg_trade,
            max_trade=max_trade,
            signed_imb=signed_imb,
            toxic=toxic,
        )
    
    def _empty_features(self, ts: float) -> FeatureVector:
        """返回空特征向量（当订单簿为空时）
        
        Args:
            ts: 时间戳
        
        Returns:
            全 0 的 FeatureVector
        """
        return FeatureVector(
            ts=ts,
            mid=0.0,
            spread=0.0,
            spread_bps=0.0,
            top_bid_sz=0.0,
            top_ask_sz=0.0,
            depth_bid_k=0.0,
            depth_ask_k=0.0,
            imb_k=0.0,
            micro_minus_mid=0.0,
            impact_buy_bps=9999.9,  # 无流动性
            impact_sell_bps=9999.9,
            msg_rate=0.0,
            churn=0.0,
            vol=0.0,
            trades=0,
            avg_trade=0.0,
            max_trade=0.0,
            signed_imb=0.0,
            toxic=0.0,
        )
    
    def reset(self) -> None:
        """重置内部状态"""
        self._last_depth_bid = 0.0
        self._last_depth_ask = 0.0
        self._msg_count = 0
        self._last_msg_ts = time.time()
        
        logger.info("feature_engine_reset")
