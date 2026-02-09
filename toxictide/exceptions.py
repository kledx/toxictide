"""
TOXICTIDE 自定义异常层次

定义了完整的异常继承体系，用于精确的错误处理和传播。
"""


class ToxicTideException(Exception):
    """TOXICTIDE 基础异常类

    所有项目特定异常的基类。
    """
    pass


# ============================================================================
# 数据层异常
# ============================================================================

class DataException(ToxicTideException):
    """数据层异常基类

    用于市场数据相关的所有异常。
    """
    pass


class OrderbookInconsistentError(DataException):
    """盘口数据不一致异常

    当 orderbook 数据违反约束时抛出（如 spread < 0, 排序错误等）。
    """
    pass


class ConnectionLostError(DataException):
    """连接断开异常

    当市场数据连接丢失时抛出。
    """
    pass


class DataStaleError(DataException):
    """数据过期异常

    当数据超过可接受的延迟阈值时抛出。
    """
    pass


class SequenceError(DataException):
    """序列号错误异常

    当 orderbook 序列号跳跃或回退时抛出。
    """
    pass


# ============================================================================
# 风控层异常
# ============================================================================

class RiskException(ToxicTideException):
    """风控层异常基类

    用于风险管理相关的所有异常。
    """
    pass


class DailyLossExceededError(RiskException):
    """日亏超限异常

    当日盈亏超过最大允许损失时抛出。
    """
    pass


class PositionLimitError(RiskException):
    """仓位超限异常

    当仓位超过最大允许值时抛出。
    """
    pass


class CooldownActiveError(RiskException):
    """冷却期激活异常

    当系统处于冷却期无法交易时抛出。
    """
    pass


class ImpactExceededError(RiskException):
    """冲击成本超限异常

    当价格冲击超过允许阈值时抛出。
    """
    pass


class ToxicFlowError(RiskException):
    """毒性流异常

    当检测到高毒性流时抛出。
    """
    pass


# ============================================================================
# 执行层异常
# ============================================================================

class ExecutionException(ToxicTideException):
    """执行层异常基类

    用于订单执行相关的所有异常。
    """
    pass


class OrderRejectedError(ExecutionException):
    """订单被拒绝异常

    当订单被交易所或内部系统拒绝时抛出。
    """
    pass


class InsufficientBalanceError(ExecutionException):
    """余额不足异常

    当账户余额不足以执行订单时抛出。
    """
    pass


class OrderTimeoutError(ExecutionException):
    """订单超时异常

    当订单执行超时时抛出。
    """
    pass


# ============================================================================
# 配置层异常
# ============================================================================

class ConfigException(ToxicTideException):
    """配置层异常基类

    用于配置相关的所有异常。
    """
    pass


class ConfigValidationError(ConfigException):
    """配置验证失败异常

    当配置文件验证失败时抛出。
    """
    pass


class ConfigNotFoundError(ConfigException):
    """配置文件未找到异常

    当指定的配置文件不存在时抛出。
    """
    pass
