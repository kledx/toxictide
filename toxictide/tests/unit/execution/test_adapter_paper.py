"""
TOXICTIDE Paper Execution Adapter 测试
"""

import time

import pytest

from toxictide.execution.adapter_paper import PaperExecutionAdapter
from toxictide.models import ExecutionPlan


class TestPaperExecutionAdapter:
    """测试 PaperExecutionAdapter"""

    def setup_method(self):
        """每个测试前初始化"""
        self.adapter = PaperExecutionAdapter(initial_balance=10000.0)

    def test_initialization(self):
        """测试初始化"""
        account = self.adapter.get_account_state()

        assert account["balance"] == 10000.0
        assert account["position_size"] == 0.0

    def test_execute_single_order(self):
        """测试执行单个订单"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )

        fills = self.adapter.execute(plan)

        assert len(fills) == 1
        assert fills[0].side == "buy"
        assert fills[0].size > 0
        assert fills[0].fee > 0

    def test_execute_multiple_orders(self):
        """测试执行多个订单"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[
                {"type": "limit", "side": "long", "price": 2000.0, "size_usd": 500.0},
                {"type": "limit", "side": "long", "price": 2000.0, "size_usd": 500.0},
            ],
            mode="slicing",
            reasons=[],
        )

        fills = self.adapter.execute(plan)

        assert len(fills) == 2

    def test_slippage_simulation(self):
        """测试滑点模拟"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )

        fills = self.adapter.execute(plan)

        # 做多应该有正滑点（支付更高价格）
        assert fills[0].price > 2000.0
        assert fills[0].price < 2010.0  # 滑点应该在合理范围

    def test_fee_calculation_maker(self):
        """测试 maker 手续费"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )

        fills = self.adapter.execute(plan)

        # Maker 手续费 0.02%
        expected_fee = 1000.0 * 0.0002
        assert fills[0].fee == pytest.approx(expected_fee, rel=0.01)

    def test_fee_calculation_taker(self):
        """测试 taker 手续费"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "market",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="taker",
            reasons=[],
        )

        fills = self.adapter.execute(plan)

        # Taker 手续费 0.05%
        expected_fee = 1000.0 * 0.0005
        assert fills[0].fee == pytest.approx(expected_fee, rel=0.01)

    def test_position_update_long(self):
        """测试做多仓位更新"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )

        self.adapter.execute(plan)
        account = self.adapter.get_account_state()

        assert account["position_size"] > 0  # 持有多头
        assert account["position_notional"] > 0

    def test_position_update_short(self):
        """测试做空仓位更新"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "short",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )

        self.adapter.execute(plan)
        account = self.adapter.get_account_state()

        assert account["position_size"] < 0  # 持有空头

    def test_balance_deduction(self):
        """测试余额扣除手续费"""
        initial_balance = self.adapter.get_account_state()["balance"]

        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )

        fills = self.adapter.execute(plan)
        final_balance = self.adapter.get_account_state()["balance"]

        # 余额应该减少（手续费）
        assert final_balance < initial_balance
        assert initial_balance - final_balance == pytest.approx(fills[0].fee)

    def test_close_all_positions(self):
        """测试平仓"""
        # 先开仓
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )
        self.adapter.execute(plan)

        # 平仓
        fills = self.adapter.close_all_positions()

        assert len(fills) == 1
        assert fills[0].side == "sell"  # 平多头应该是卖出

        # 仓位应该归零
        account = self.adapter.get_account_state()
        assert account["position_size"] == pytest.approx(0.0, abs=0.0001)

    def test_close_all_no_position(self):
        """测试无仓位时平仓"""
        fills = self.adapter.close_all_positions()

        assert len(fills) == 0

    def test_empty_plan(self):
        """测试空计划"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[],
            mode="reduce_only",
            reasons=[],
        )

        fills = self.adapter.execute(plan)

        assert len(fills) == 0

    def test_fills_history(self):
        """测试成交历史"""
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[
                {"type": "limit", "side": "long", "price": 2000.0, "size_usd": 500.0},
                {"type": "limit", "side": "long", "price": 2000.0, "size_usd": 500.0},
            ],
            mode="slicing",
            reasons=[],
        )

        self.adapter.execute(plan)

        history = self.adapter.fills_history
        assert len(history) == 2

    def test_reset(self):
        """测试重置"""
        # 执行一些交易
        plan = ExecutionPlan(
            ts=time.time(),
            orders=[{
                "type": "limit",
                "side": "long",
                "price": 2000.0,
                "size_usd": 1000.0,
            }],
            mode="maker",
            reasons=[],
        )
        self.adapter.execute(plan)

        # 重置
        self.adapter.reset(initial_balance=20000.0)

        account = self.adapter.get_account_state()
        assert account["balance"] == 20000.0
        assert account["position_size"] == 0.0
        assert len(self.adapter.fills_history) == 0
