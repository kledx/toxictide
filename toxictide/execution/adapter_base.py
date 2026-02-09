"""
TOXICTIDE Execution Adapter Base

执行适配器基础接口
"""

from abc import ABC, abstractmethod
from typing import Protocol

from toxictide.models import ExecutionPlan, Fill


class IExecutionAdapter(Protocol):
    """执行适配器接口

    定义所有执行适配器必须实现的方法。

    支持多种实现：
    - PaperExecutionAdapter: 纸面交易（模拟）
    - RealExecutionAdapter: 真实交易所
    - BacktestAdapter: 历史回测

    Example:
        >>> adapter = PaperExecutionAdapter()
        >>> fills = adapter.execute(execution_plan)
        >>> account = adapter.get_account_state()
    """

    def execute(self, plan: ExecutionPlan) -> list[Fill]:
        """执行交易计划

        Args:
            plan: ExecutionPlan 对象，包含订单列表

        Returns:
            Fill 列表（成交记录）

        Raises:
            ExecutionException: 执行失败时抛出
        """
        ...

    def get_account_state(self) -> dict:
        """获取账户状态

        Returns:
            账户状态字典，包含：
            - balance: 账户余额
            - position_size: 持仓数量（正=long, 负=short）
            - position_notional: 持仓名义价值（绝对值）
            - unrealized_pnl: 未实现盈亏
        """
        ...

    def close_all_positions(self) -> list[Fill]:
        """平掉所有仓位

        用于紧急情况或策略结束时清仓。

        Returns:
            Fill 列表
        """
        ...
