"""
TOXICTIDE 数据模型

使用 Pydantic BaseModel 定义所有核心数据结构，提供：
- 自动类型验证
- 字段约束检查
- JSON 序列化/反序列化
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# 市场数据模型
# ============================================================================

class OrderBookLevel(BaseModel):
    """订单簿单个价位

    Attributes:
        price: 价格（必须 > 0）
        size: 数量（必须 > 0）
    """
    price: float = Field(gt=0, description="价格")
    size: float = Field(gt=0, description="数量")

    model_config = {"frozen": True}


class OrderBookState(BaseModel):
    """订单簿状态快照

    Attributes:
        ts: 时间戳
        bids: 买盘（必须价格降序）
        asks: 卖盘（必须价格升序）
        seq: 序列号
    """
    ts: float = Field(description="时间戳")
    bids: list[OrderBookLevel] = Field(description="买盘列表（价格降序）")
    asks: list[OrderBookLevel] = Field(description="卖盘列表（价格升序）")
    seq: int = Field(ge=0, description="序列号")

    @field_validator("bids")
    @classmethod
    def bids_must_be_descending(cls, v: list[OrderBookLevel]) -> list[OrderBookLevel]:
        """验证买盘价格降序排列"""
        if len(v) < 2:
            return v
        prices = [level.price for level in v]
        if prices != sorted(prices, reverse=True):
            raise ValueError("Bids must be in descending price order")
        return v

    @field_validator("asks")
    @classmethod
    def asks_must_be_ascending(cls, v: list[OrderBookLevel]) -> list[OrderBookLevel]:
        """验证卖盘价格升序排列"""
        if len(v) < 2:
            return v
        prices = [level.price for level in v]
        if prices != sorted(prices):
            raise ValueError("Asks must be in ascending price order")
        return v

    @model_validator(mode="after")
    def spread_must_be_positive(self) -> "OrderBookState":
        """验证 spread >= 0"""
        if self.bids and self.asks:
            best_bid = self.bids[0].price
            best_ask = self.asks[0].price
            if best_ask <= best_bid:
                raise ValueError(
                    f"Negative spread: best_ask ({best_ask}) <= best_bid ({best_bid})"
                )
        return self

    @property
    def mid(self) -> float:
        """中间价"""
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0].price + self.asks[0].price) / 2

    @property
    def spread(self) -> float:
        """买卖价差"""
        if not self.bids or not self.asks:
            return 0.0
        return self.asks[0].price - self.bids[0].price

    @property
    def spread_bps(self) -> float:
        """买卖价差（基点）"""
        mid = self.mid
        if mid == 0:
            return 0.0
        return (self.spread / mid) * 10000


class Trade(BaseModel):
    """单笔交易

    Attributes:
        ts: 时间戳
        price: 成交价格
        size: 成交数量
        side: 成交方向（buy/sell/unknown）
    """
    ts: float = Field(description="时间戳")
    price: float = Field(gt=0, description="成交价格")
    size: float = Field(gt=0, description="成交数量")
    side: Literal["buy", "sell", "unknown"] = Field(description="成交方向")

    model_config = {"frozen": True}


# ============================================================================
# 特征模型
# ============================================================================

class FeatureVector(BaseModel):
    """特征向量

    包含从 orderbook 和 trades 计算得到的所有特征。
    """
    ts: float = Field(description="时间戳")

    # Orderbook 特征
    mid: float = Field(description="中间价")
    spread: float = Field(description="买卖价差")
    spread_bps: float = Field(description="买卖价差（基点）")
    top_bid_sz: float = Field(ge=0, description="买一档数量")
    top_ask_sz: float = Field(ge=0, description="卖一档数量")
    depth_bid_k: float = Field(ge=0, description="买盘深度（USD）")
    depth_ask_k: float = Field(ge=0, description="卖盘深度（USD）")
    imb_k: float = Field(ge=-1, le=1, description="深度不平衡 (-1, 1)")
    micro_minus_mid: float = Field(description="微观价格 - 中间价")
    impact_buy_bps: float = Field(ge=0, description="买入冲击（基点）")
    impact_sell_bps: float = Field(ge=0, description="卖出冲击（基点）")
    msg_rate: float = Field(ge=0, description="消息速率")
    churn: float = Field(ge=0, description="深度变化率")

    # Trade 特征
    vol: float = Field(ge=0, description="成交量")
    trades: int = Field(ge=0, description="成交笔数")
    avg_trade: float = Field(ge=0, description="平均成交量")
    max_trade: float = Field(ge=0, description="最大单笔成交量")
    signed_imb: float = Field(ge=-1, le=1, description="带符号不平衡 (-1, 1)")
    toxic: float = Field(ge=0, le=1, description="毒性流指标 [0, 1]")

    model_config = {"frozen": True}


# ============================================================================
# 异常检测模型
# ============================================================================

class OrderbookAnomalyReport(BaseModel):
    """盘口异常检测报告

    OAD (Orderbook Anomaly Detector) 的输出。
    """
    ts: float = Field(description="时间戳")
    level: Literal["OK", "WARN", "DANGER"] = Field(description="异常级别")
    score: float = Field(description="异常分数")
    triggers: dict[str, float] = Field(description="触发器详情")
    liquidity_state: Literal["THICK", "THIN", "TOXIC"] = Field(description="流动性状态")

    model_config = {"frozen": True}


class VolumeAnomalyReport(BaseModel):
    """成交量异常检测报告

    VAD (Volume Anomaly Detector) 的输出。
    """
    ts: float = Field(description="时间戳")
    level: Literal["OK", "WARN", "DANGER"] = Field(description="异常级别")
    score: float = Field(description="异常分数")
    triggers: dict[str, float] = Field(description="触发器详情")
    events: dict[str, bool] = Field(description="事件标志（burst, drought, whale）")

    model_config = {"frozen": True}


class MarketStressIndex(BaseModel):
    """市场压力指数

    综合 OAD 和 VAD 的压力指数。
    """
    ts: float = Field(description="时间戳")
    level: Literal["OK", "WARN", "DANGER"] = Field(description="压力级别")
    score: float = Field(description="压力分数")
    components: dict[str, float] = Field(description="组件分数")

    model_config = {"frozen": True}


# ============================================================================
# 市场状态模型
# ============================================================================

class RegimeState(BaseModel):
    """市场状态

    Regime/Flow 分类器的输出。
    """
    ts: float = Field(description="时间戳")
    price_regime: Literal["TREND_UP", "TREND_DOWN", "RANGE"] = Field(
        description="价格趋势状态"
    )
    vol_regime: Literal["HIGHVOL", "NORMALVOL", "LOWVOL"] = Field(
        description="波动率状态"
    )
    flow_regime: Literal["TOXIC", "ACTIVE", "CALM"] = Field(
        description="流动性/毒性状态"
    )
    confidence: float = Field(ge=0, le=1, description="置信度 [0, 1]")

    model_config = {"frozen": True}


# ============================================================================
# 策略模型
# ============================================================================

class TradeCandidate(BaseModel):
    """交易候选

    Signal Engine 生成的交易候选。
    """
    ts: float = Field(description="时间戳")
    side: Literal["long", "short"] = Field(description="交易方向")
    entry_price: float = Field(gt=0, description="入场价格")
    stop_price: float = Field(gt=0, description="止损价格")
    tp_price: Optional[float] = Field(default=None, gt=0, description="止盈价格")
    confidence: float = Field(ge=0, le=1, description="置信度 [0, 1]")
    ttl_sec: int = Field(gt=0, description="有效期（秒）")
    strategy: str = Field(description="策略名称")

    model_config = {"frozen": True}


# ============================================================================
# 风控模型
# ============================================================================

class RiskDecision(BaseModel):
    """风控决策

    Risk Guardian 的决策输出。
    """
    ts: float = Field(description="时间戳")
    action: Literal["ALLOW", "ALLOW_WITH_REDUCTIONS", "DENY"] = Field(
        description="决策动作"
    )
    size_usd: float = Field(ge=0, description="允许的仓位大小（USD）")
    max_slippage_bps: float = Field(ge=0, description="最大允许滑点（基点）")
    cooldown_until_ts: Optional[float] = Field(
        default=None, description="冷却期结束时间戳"
    )
    reasons: list[str] = Field(description="决策原因编码列表")
    facts: dict[str, Any] = Field(description="决策依据的事实数据")

    model_config = {"frozen": True}


# ============================================================================
# 执行模型
# ============================================================================

class ExecutionPlan(BaseModel):
    """执行计划

    Execution Planner 的输出。
    """
    ts: float = Field(description="时间戳")
    orders: list[dict[str, Any]] = Field(description="订单列表")
    mode: Literal["maker", "taker", "slicing", "reduce_only"] = Field(
        description="执行模式"
    )
    reasons: list[str] = Field(description="计划原因")

    model_config = {"frozen": True}


class Fill(BaseModel):
    """成交回执

    订单成交的详细信息。
    """
    ts: float = Field(description="时间戳")
    order_id: str = Field(description="订单 ID")
    price: float = Field(gt=0, description="成交价格")
    size: float = Field(gt=0, description="成交数量")
    fee: float = Field(ge=0, description="手续费")
    side: Literal["buy", "sell"] = Field(description="成交方向")

    model_config = {"frozen": True}


# ============================================================================
# 审计模型
# ============================================================================

class LedgerRecord(BaseModel):
    """审计日志记录

    每次决策的完整快照，用于回放和审计。
    """
    ts: float = Field(description="时间戳")
    policy: dict[str, Any] = Field(description="当时的策略配置")
    features: FeatureVector = Field(description="特征向量")
    oad: OrderbookAnomalyReport = Field(description="盘口异常报告")
    vad: VolumeAnomalyReport = Field(description="成交量异常报告")
    stress: MarketStressIndex = Field(description="市场压力指数")
    regime: RegimeState = Field(description="市场状态")
    signal: Optional[TradeCandidate] = Field(description="交易信号")
    risk: RiskDecision = Field(description="风控决策")
    plan: ExecutionPlan = Field(description="执行计划")
    fills: list[Fill] = Field(description="成交列表")
    explain: str = Field(description="人类可读的决策解释")

    model_config = {"frozen": True}


# ============================================================================
# 持仓管理模型
# ============================================================================

class Position(BaseModel):
    """持仓记录

    Attributes:
        position_id: 唯一标识符
        side: 方向（long/short）
        entry_price: 入场价格
        entry_time: 入场时间
        size: 持仓数量
        size_usd: 持仓价值（USD）
        stop_price: 止损价格
        tp_price: 止盈价格（可选）
        strategy: 策略名称
        is_open: 是否仍持仓
        close_price: 平仓价格（仅当 is_open=False）
        close_time: 平仓时间（仅当 is_open=False）
        close_reason: 平仓原因（stop_loss/take_profit/manual）
        pnl: 已实现盈亏（仅当 is_open=False）
    """
    position_id: str = Field(description="持仓唯一标识符")
    side: Literal["long", "short"] = Field(description="方向")
    entry_price: float = Field(gt=0, description="入场价格")
    entry_time: float = Field(description="入场时间戳")
    size: float = Field(gt=0, description="持仓数量")
    size_usd: float = Field(gt=0, description="持仓价值 USD")
    stop_price: float = Field(gt=0, description="止损价格")
    tp_price: Optional[float] = Field(default=None, description="止盈价格")
    strategy: str = Field(description="策略名称")
    is_open: bool = Field(default=True, description="是否仍持仓")
    close_price: Optional[float] = Field(default=None, description="平仓价格")
    close_time: Optional[float] = Field(default=None, description="平仓时间")
    close_reason: Optional[Literal["stop_loss", "take_profit", "manual", "ttl_expired"]] = Field(
        default=None, description="平仓原因"
    )
    pnl: Optional[float] = Field(default=None, description="已实现盈亏")

    model_config = {"frozen": False}  # 允许修改（平仓时需要更新字段）

    def unrealized_pnl(self, current_price: float) -> float:
        """计算未实现盈亏

        Args:
            current_price: 当前市场价格

        Returns:
            未实现盈亏（USD）
        """
        if not self.is_open:
            return self.pnl or 0.0

        if self.side == "long":
            return (current_price - self.entry_price) * self.size
        else:  # short
            return (self.entry_price - current_price) * self.size

    def close(self, close_price: float, close_time: float, reason: str) -> None:
        """平仓

        Args:
            close_price: 平仓价格
            close_time: 平仓时间
            reason: 平仓原因
        """
        self.is_open = False
        self.close_price = close_price
        self.close_time = close_time
        self.close_reason = reason
        self.pnl = self.unrealized_pnl(close_price)

    model_config = {"frozen": False}
