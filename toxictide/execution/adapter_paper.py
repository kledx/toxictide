"""
TOXICTIDE Paper Execution Adapter

纸面交易适配器 - 模拟订单执行（无需真实交易所）
"""

import json
import os
import random
import time

import structlog

from toxictide.exceptions import ExecutionException
from toxictide.models import ExecutionPlan, Fill

logger = structlog.get_logger(__name__)


class PaperExecutionAdapter:
    """纸面交易适配器

    模拟订单执行，用于开发、测试和回测。

    **模拟功能：**
    - 订单成交（100% 成交率）
    - 滑点（1-5 bps 随机）
    - 手续费（taker 0.05%, maker 0.02%）
    - 账户状态维护
    - 成交历史记录

    **不模拟：**
    - 订单簿匹配
    - 部分成交
    - 订单拒绝
    - 网络延迟

    Example:
        >>> adapter = PaperExecutionAdapter(initial_balance=10000.0)
        >>> fills = adapter.execute(execution_plan)
        >>> account = adapter.get_account_state()
        >>> print(f"Balance: ${account['balance']:.2f}")
    """

    def __init__(self, initial_balance: float = 10000.0) -> None:
        """初始化纸面交易适配器

        Args:
            initial_balance: 初始余额
        """
        self._balance = initial_balance
        self._position_size = 0.0  # 正=long, 负=short
        self._position_entry_price = 0.0
        self._fills: list[Fill] = []

        logger.info(
            "paper_adapter_initialized",
            initial_balance=initial_balance,
        )

        # 状态持久化文件路径
        # 优先使用 data/ 目录（用于 Docker 挂载持久化），否则使用当前目录
        if os.path.exists("data") and os.path.isdir("data"):
            self._state_file = "data/paper_account.json"
        else:
            self._state_file = "paper_account.json"

        try:
            self._load_state()
        except Exception as e:
            logger.error("load_paper_state_failed", error=str(e))


    def execute(self, plan: ExecutionPlan) -> list[Fill]:
        """执行交易计划（模拟）

        Args:
            plan: ExecutionPlan 对象

        Returns:
            Fill 列表
        """
        if not plan.orders:
            logger.debug("no_orders_to_execute")
            return []

        fills = []

        for order in plan.orders:
            try:
                fill = self._execute_single_order(order, plan.ts)
                fills.append(fill)
                self._fills.append(fill)
            except Exception as e:
                logger.error(
                    "order_execution_failed",
                    order=order,
                    error=str(e),
                )
                raise ExecutionException(f"Order execution failed: {e}")

        logger.info(
            "execution_completed",
            fills_count=len(fills),
            mode=plan.mode,
        )

        return fills

    def _execute_single_order(self, order: dict, ts: float) -> Fill:
        """执行单个订单（模拟）

        Args:
            order: 订单字典
            ts: 时间戳

        Returns:
            Fill 对象
        """
        order_type = order["type"]
        side = order["side"]
        size_usd = order["size_usd"]

        # 模拟滑点
        base_price = order.get("price", 2000.0)
        slippage_bps = random.uniform(1, 5)

        if side == "long":
            # 做多：买入，支付更高价格
            fill_price = base_price * (1 + slippage_bps / 10000)
        else:
            # 做空：卖出，获得更低价格
            fill_price = base_price * (1 - slippage_bps / 10000)

        # 计算 size (coins)
        size_coins = size_usd / fill_price

        # 手续费（假设 0.05% taker, 0.02% maker）
        if order_type == "market":
            fee_rate = 0.0005  # 0.05%
        else:  # limit
            fee_rate = 0.0002  # 0.02%

        fee = size_usd * fee_rate

        # 创建 Fill
        fill = Fill(
            ts=ts,
            order_id=f"paper_{int(ts * 1000)}_{random.randint(1000, 9999)}",
            price=fill_price,
            size=size_coins,
            fee=fee,
            side="buy" if side == "long" else "sell",
        )

        # 更新仓位
        if side == "long":
            self._position_size += size_coins
            self._position_entry_price = fill_price
        else:
            self._position_size -= size_coins
            self._position_entry_price = fill_price

        # 扣除手续费
        self._balance -= fee

        logger.debug(
            "order_filled",
            fill_price=fill_price,
            size_coins=size_coins,
            fee=fee,
            slippage_bps=slippage_bps,
        )

        self._save_state()

        return fill


    def get_account_state(self, current_price: float = 0.0) -> dict:
        """获取账户状态

        Args:
            current_price: 当前市场价格（用于计算未实现盈亏）

        Returns:
            账户状态字典
        """
        unrealized_pnl = 0.0
        if self._position_size != 0 and current_price > 0:
            if self._position_size > 0:
                unrealized_pnl = (current_price - self._position_entry_price) * self._position_size
            else:
                unrealized_pnl = (self._position_entry_price - current_price) * abs(self._position_size)

        return {
            "balance": self._balance,
            "position_size": self._position_size,
            "position_notional": abs(self._position_size * self._position_entry_price),
            "unrealized_pnl": unrealized_pnl,
        }

    def close_all_positions(self) -> list[Fill]:
        """平掉所有仓位

        Returns:
            Fill 列表
        """
        if self._position_size == 0:
            logger.debug("no_positions_to_close")
            return []

        # 创建平仓订单
        side = "short" if self._position_size > 0 else "long"
        size_usd = abs(self._position_size * self._position_entry_price)

        order = {
            "type": "market",
            "side": side,
            "size_usd": size_usd,
            "price": self._position_entry_price,
        }

        fill = self._execute_single_order(order, time.time())

        logger.info("all_positions_closed", fill=fill)

        return [fill]

    @property
    def fills_history(self) -> list[Fill]:
        """获取成交历史"""
        return self._fills

    def reset(self, initial_balance: float = 10000.0) -> None:
        """重置适配器状态

        Args:
            initial_balance: 重置后的初始余额
        """
        self._balance = initial_balance
        self._position_size = 0.0
        self._position_entry_price = 0.0
        self._fills.clear()

        logger.info("paper_adapter_reset", initial_balance=initial_balance)
        self._save_state()

    def _load_state(self) -> None:
        """加载账户状态"""
        if not os.path.exists(self._state_file):
            return

        with open(self._state_file, "r") as f:
            data = json.load(f)
            self._balance = data.get("balance", self._balance)
            self._position_size = data.get("position_size", 0.0)
            self._position_entry_price = data.get("position_entry_price", 0.0)
            logger.info("paper_state_loaded", balance=self._balance, position_size=self._position_size)

    def _save_state(self) -> None:
        """保存账户状态"""
        data = {
            "balance": self._balance,
            "position_size": self._position_size,
            "position_entry_price": self._position_entry_price,
            "updated_at": time.time(),
        }
        # 确保目录存在
        dir_name = os.path.dirname(self._state_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(self._state_file, "w") as f:
            json.dump(data, f, indent=2)

