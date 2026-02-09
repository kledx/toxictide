"""
TOXICTIDE 事件总线

极简同步事件总线，用于模块间解耦通信。

特性：
- 同步 pub/sub（适合主循环单线程架构）
- 异常隔离（一个 handler 失败不影响其他）
- 类型安全（支持泛型 payload）
"""

import structlog
from collections import defaultdict
from typing import Any, Callable, TypeVar

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# 标准 Topics
TOPIC_MARKET_BOOK = "market.book"
TOPIC_MARKET_TRADES = "market.trades"
TOPIC_FEATURES = "features"
TOPIC_OAD = "oad"
TOPIC_VAD = "vad"
TOPIC_STRESS = "stress"
TOPIC_REGIME = "regime"
TOPIC_SIGNAL = "signal"
TOPIC_RISK = "risk"
TOPIC_PLAN = "plan"
TOPIC_FILL = "fill"
TOPIC_LEDGER = "ledger"
TOPIC_POSITIONS = "positions"
TOPIC_ACCOUNT = "account"

# 所有标准 topics 列表
ALL_TOPICS = [
    TOPIC_MARKET_BOOK,
    TOPIC_MARKET_TRADES,
    TOPIC_FEATURES,
    TOPIC_OAD,
    TOPIC_VAD,
    TOPIC_STRESS,
    TOPIC_REGIME,
    TOPIC_SIGNAL,
    TOPIC_RISK,
    TOPIC_PLAN,
    TOPIC_FILL,
    TOPIC_LEDGER,
    TOPIC_POSITIONS,
    TOPIC_ACCOUNT,
]


class EventBus:
    """极简同步事件总线

    提供 pub/sub 模式的模块间通信机制。

    Example:
        >>> bus = EventBus()
        >>> def handler(data):
        ...     print(f"Received: {data}")
        >>> bus.subscribe("my.topic", handler)
        >>> bus.publish("my.topic", {"key": "value"})
        Received: {'key': 'value'}
    """

    def __init__(self) -> None:
        """初始化事件总线"""
        self._subscribers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)
        self._event_count: int = 0

    def subscribe(
        self,
        topic: str,
        handler: Callable[[Any], None],
    ) -> None:
        """订阅主题

        Args:
            topic: 主题名称
            handler: 事件处理函数，接收一个 payload 参数
        """
        self._subscribers[topic].append(handler)
        logger.debug(
            "handler_subscribed",
            topic=topic,
            handler=handler.__name__,
            total_handlers=len(self._subscribers[topic]),
        )

    def unsubscribe(
        self,
        topic: str,
        handler: Callable[[Any], None],
    ) -> bool:
        """取消订阅

        Args:
            topic: 主题名称
            handler: 要取消的处理函数

        Returns:
            是否成功取消（False 表示 handler 不存在）
        """
        if topic in self._subscribers and handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)
            logger.debug(
                "handler_unsubscribed",
                topic=topic,
                handler=handler.__name__,
            )
            return True
        return False

    def publish(self, topic: str, payload: Any) -> int:
        """发布事件

        Args:
            topic: 主题名称
            payload: 事件数据

        Returns:
            成功调用的 handler 数量
        """
        handlers = self._subscribers.get(topic, [])

        if not handlers:
            logger.debug("no_handlers", topic=topic)
            return 0

        self._event_count += 1
        success_count = 0

        for handler in handlers:
            try:
                handler(payload)
                success_count += 1
            except Exception as e:
                # 一个 handler 失败不影响其他 handler
                logger.error(
                    "handler_failed",
                    topic=topic,
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True,
                )

        logger.debug(
            "event_published",
            topic=topic,
            handlers_called=success_count,
            handlers_total=len(handlers),
        )

        return success_count

    def clear(self, topic: str | None = None) -> None:
        """清空订阅

        Args:
            topic: 要清空的主题，None 表示清空所有
        """
        if topic is None:
            self._subscribers.clear()
            logger.debug("all_subscriptions_cleared")
        elif topic in self._subscribers:
            del self._subscribers[topic]
            logger.debug("topic_subscriptions_cleared", topic=topic)

    def get_subscriber_count(self, topic: str) -> int:
        """获取主题的订阅者数量

        Args:
            topic: 主题名称

        Returns:
            订阅者数量
        """
        return len(self._subscribers.get(topic, []))

    def get_topics(self) -> list[str]:
        """获取所有有订阅者的主题

        Returns:
            主题列表
        """
        return list(self._subscribers.keys())

    @property
    def event_count(self) -> int:
        """已发布的事件总数"""
        return self._event_count


# 全局单例
_default_bus: EventBus | None = None


def get_bus() -> EventBus:
    """获取全局事件总线单例

    Returns:
        全局 EventBus 实例
    """
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


def reset_bus() -> None:
    """重置全局事件总线（主要用于测试）"""
    global _default_bus
    if _default_bus is not None:
        _default_bus.clear()
    _default_bus = None
