"""
TOXICTIDE 事件总线测试
"""

import pytest

from toxictide.bus import (
    EventBus,
    get_bus,
    reset_bus,
    TOPIC_FEATURES,
    TOPIC_RISK,
    ALL_TOPICS,
)


class TestEventBus:
    """测试 EventBus"""

    def setup_method(self):
        """每个测试前重置"""
        self.bus = EventBus()
        self.received_events: list = []

    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        def handler(data):
            self.received_events.append(data)

        self.bus.subscribe("test.topic", handler)
        self.bus.publish("test.topic", {"key": "value"})

        assert len(self.received_events) == 1
        assert self.received_events[0] == {"key": "value"}

    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        results = []

        def handler1(data):
            results.append(("handler1", data))

        def handler2(data):
            results.append(("handler2", data))

        self.bus.subscribe("test.topic", handler1)
        self.bus.subscribe("test.topic", handler2)
        self.bus.publish("test.topic", "test_data")

        assert len(results) == 2
        assert ("handler1", "test_data") in results
        assert ("handler2", "test_data") in results

    def test_publish_to_nonexistent_topic(self):
        """测试发布到不存在的主题"""
        result = self.bus.publish("nonexistent", "data")
        assert result == 0  # 没有 handler 被调用

    def test_handler_exception_does_not_affect_others(self):
        """测试一个 handler 异常不影响其他 handler"""
        results = []

        def failing_handler(data):
            raise ValueError("Handler failed")

        def success_handler(data):
            results.append(data)

        self.bus.subscribe("test.topic", failing_handler)
        self.bus.subscribe("test.topic", success_handler)

        # 应该不会抛出异常
        count = self.bus.publish("test.topic", "data")

        # success_handler 应该被调用
        assert len(results) == 1
        assert results[0] == "data"
        # 只有 1 个成功
        assert count == 1

    def test_unsubscribe(self):
        """测试取消订阅"""
        def handler(data):
            self.received_events.append(data)

        self.bus.subscribe("test.topic", handler)
        self.bus.publish("test.topic", "event1")

        result = self.bus.unsubscribe("test.topic", handler)
        assert result is True

        self.bus.publish("test.topic", "event2")

        # 只有取消订阅前的事件
        assert len(self.received_events) == 1
        assert self.received_events[0] == "event1"

    def test_unsubscribe_nonexistent(self):
        """测试取消不存在的订阅"""
        def handler(data):
            pass

        result = self.bus.unsubscribe("nonexistent", handler)
        assert result is False

    def test_clear_specific_topic(self):
        """测试清空特定主题"""
        def handler(data):
            self.received_events.append(data)

        self.bus.subscribe("topic1", handler)
        self.bus.subscribe("topic2", handler)

        self.bus.clear("topic1")

        self.bus.publish("topic1", "data1")
        self.bus.publish("topic2", "data2")

        # 只有 topic2 的事件
        assert len(self.received_events) == 1
        assert self.received_events[0] == "data2"

    def test_clear_all_topics(self):
        """测试清空所有主题"""
        def handler(data):
            self.received_events.append(data)

        self.bus.subscribe("topic1", handler)
        self.bus.subscribe("topic2", handler)

        self.bus.clear()

        self.bus.publish("topic1", "data1")
        self.bus.publish("topic2", "data2")

        assert len(self.received_events) == 0

    def test_get_subscriber_count(self):
        """测试获取订阅者数量"""
        def handler1(data):
            pass

        def handler2(data):
            pass

        assert self.bus.get_subscriber_count("test.topic") == 0

        self.bus.subscribe("test.topic", handler1)
        assert self.bus.get_subscriber_count("test.topic") == 1

        self.bus.subscribe("test.topic", handler2)
        assert self.bus.get_subscriber_count("test.topic") == 2

    def test_get_topics(self):
        """测试获取所有主题"""
        def handler(data):
            pass

        assert self.bus.get_topics() == []

        self.bus.subscribe("topic1", handler)
        self.bus.subscribe("topic2", handler)

        topics = self.bus.get_topics()
        assert "topic1" in topics
        assert "topic2" in topics

    def test_event_count(self):
        """测试事件计数"""
        def handler(data):
            pass

        self.bus.subscribe("test.topic", handler)

        assert self.bus.event_count == 0

        self.bus.publish("test.topic", "data1")
        assert self.bus.event_count == 1

        self.bus.publish("test.topic", "data2")
        assert self.bus.event_count == 2

    def test_standard_topics_defined(self):
        """测试标准主题已定义"""
        assert TOPIC_FEATURES == "features"
        assert TOPIC_RISK == "risk"
        assert len(ALL_TOPICS) == 12


class TestGlobalBus:
    """测试全局事件总线"""

    def setup_method(self):
        """每个测试前重置全局 bus"""
        reset_bus()

    def teardown_method(self):
        """每个测试后重置全局 bus"""
        reset_bus()

    def test_get_bus_returns_singleton(self):
        """测试 get_bus 返回单例"""
        bus1 = get_bus()
        bus2 = get_bus()
        assert bus1 is bus2

    def test_reset_bus(self):
        """测试重置全局 bus"""
        bus1 = get_bus()
        reset_bus()
        bus2 = get_bus()
        assert bus1 is not bus2

    def test_global_bus_functionality(self):
        """测试全局 bus 功能"""
        results = []

        def handler(data):
            results.append(data)

        bus = get_bus()
        bus.subscribe("global.topic", handler)
        bus.publish("global.topic", "global_data")

        assert len(results) == 1
        assert results[0] == "global_data"
