"""
TOXICTIDE Math Utils 测试
"""

import pytest

from toxictide.utils.math import (
    bps_to_decimal,
    clip,
    decimal_to_bps,
    safe_divide,
)


class TestSafeDivide:
    """测试 safe_divide"""

    def test_normal_division(self):
        """测试正常除法"""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(100, 4) == 25.0

    def test_divide_by_zero(self):
        """测试除零返回默认值"""
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=999.0) == 999.0

    def test_negative_numbers(self):
        """测试负数"""
        assert safe_divide(-10, 2) == -5.0
        assert safe_divide(10, -2) == -5.0


class TestClip:
    """测试 clip"""

    def test_within_range(self):
        """测试在范围内的值"""
        assert clip(5.0, 0.0, 10.0) == 5.0

    def test_below_min(self):
        """测试小于最小值"""
        assert clip(-5.0, 0.0, 10.0) == 0.0

    def test_above_max(self):
        """测试大于最大值"""
        assert clip(15.0, 0.0, 10.0) == 10.0

    def test_equal_to_bounds(self):
        """测试等于边界值"""
        assert clip(0.0, 0.0, 10.0) == 0.0
        assert clip(10.0, 0.0, 10.0) == 10.0


class TestBpsConversion:
    """测试基点转换"""

    def test_bps_to_decimal(self):
        """测试 bps 转小数"""
        assert bps_to_decimal(100) == 0.01
        assert bps_to_decimal(50) == 0.005
        assert bps_to_decimal(10000) == 1.0

    def test_decimal_to_bps(self):
        """测试小数转 bps"""
        assert decimal_to_bps(0.01) == 100.0
        assert decimal_to_bps(0.005) == 50.0
        assert decimal_to_bps(1.0) == 10000.0

    def test_round_trip(self):
        """测试往返转换"""
        original = 123.45
        assert decimal_to_bps(bps_to_decimal(original)) == pytest.approx(original)
