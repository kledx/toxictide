"""
TOXICTIDE 异常测试
"""

import pytest

from toxictide.exceptions import (
    ToxicTideException,
    DataException,
    OrderbookInconsistentError,
    ConnectionLostError,
    DataStaleError,
    SequenceError,
    RiskException,
    DailyLossExceededError,
    PositionLimitError,
    CooldownActiveError,
    ImpactExceededError,
    ToxicFlowError,
    ExecutionException,
    OrderRejectedError,
    InsufficientBalanceError,
    OrderTimeoutError,
    ConfigException,
    ConfigValidationError,
    ConfigNotFoundError,
)


class TestExceptionHierarchy:
    """测试异常继承层次"""

    def test_base_exception(self):
        """测试基础异常"""
        exc = ToxicTideException("test error")
        assert str(exc) == "test error"
        assert isinstance(exc, Exception)

    def test_data_exceptions_inherit_from_base(self):
        """测试数据异常继承自基类"""
        exceptions = [
            DataException("data error"),
            OrderbookInconsistentError("orderbook error"),
            ConnectionLostError("connection error"),
            DataStaleError("stale error"),
            SequenceError("sequence error"),
        ]

        for exc in exceptions:
            assert isinstance(exc, ToxicTideException)
            assert isinstance(exc, DataException) or type(exc) == DataException

    def test_risk_exceptions_inherit_from_base(self):
        """测试风控异常继承自基类"""
        exceptions = [
            RiskException("risk error"),
            DailyLossExceededError("daily loss error"),
            PositionLimitError("position error"),
            CooldownActiveError("cooldown error"),
            ImpactExceededError("impact error"),
            ToxicFlowError("toxic error"),
        ]

        for exc in exceptions:
            assert isinstance(exc, ToxicTideException)

    def test_execution_exceptions_inherit_from_base(self):
        """测试执行异常继承自基类"""
        exceptions = [
            ExecutionException("execution error"),
            OrderRejectedError("order rejected"),
            InsufficientBalanceError("insufficient balance"),
            OrderTimeoutError("timeout"),
        ]

        for exc in exceptions:
            assert isinstance(exc, ToxicTideException)
            assert isinstance(exc, ExecutionException) or type(exc) == ExecutionException

    def test_config_exceptions_inherit_from_base(self):
        """测试配置异常继承自基类"""
        exceptions = [
            ConfigException("config error"),
            ConfigValidationError("validation error"),
            ConfigNotFoundError("not found"),
        ]

        for exc in exceptions:
            assert isinstance(exc, ToxicTideException)

    def test_exception_can_be_raised_and_caught(self):
        """测试异常可以被抛出和捕获"""
        with pytest.raises(OrderbookInconsistentError):
            raise OrderbookInconsistentError("Negative spread detected")

        # 可以用父类捕获
        with pytest.raises(DataException):
            raise OrderbookInconsistentError("Negative spread detected")

        with pytest.raises(ToxicTideException):
            raise OrderbookInconsistentError("Negative spread detected")
