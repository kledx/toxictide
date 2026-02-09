"""
TOXICTIDE Rolling Statistics 测试
"""

import time

import pytest

from toxictide.utils.rolling import RollingMAD


class TestRollingMAD:
    """测试 RollingMAD"""

    def setup_method(self):
        """每个测试前初始化"""
        self.rolling = RollingMAD(window_sec=300)

    def test_initialization(self):
        """测试初始化"""
        assert self.rolling.window_sec == 300

    def test_update_and_median(self):
        """测试更新和中位数计算"""
        ts = time.time()
        
        self.rolling.update("price", 100.0, ts)
        self.rolling.update("price", 102.0, ts + 1)
        self.rolling.update("price", 101.0, ts + 2)
        
        median = self.rolling.median("price")
        assert median == 101.0

    def test_mad_calculation(self):
        """测试 MAD 计算"""
        ts = time.time()
        
        # 添加对称分布的数据
        values = [100.0, 102.0, 104.0, 106.0, 108.0]
        for i, v in enumerate(values):
            self.rolling.update("price", v, ts + i)
        
        mad = self.rolling.mad("price")
        assert mad > 0  # MAD 应该大于 0

    def test_zscore_no_variation(self):
        """测试无变化时的 z-score"""
        ts = time.time()
        
        # 所有值相同
        for i in range(5):
            self.rolling.update("price", 100.0, ts + i)
        
        z = self.rolling.zscore("price")
        assert z == 0.0  # MAD 为 0 时，z-score 应为 0

    def test_zscore_with_outlier(self):
        """测试异常值的 z-score"""
        ts = time.time()
        
        # 添加正常值
        for i in range(10):
            self.rolling.update("price", 100.0, ts + i)
        
        # 添加异常值
        self.rolling.update("price", 150.0, ts + 10)
        
        z = self.rolling.zscore("price")
        assert z > 4.0  # 异常值应有高 z-score

    def test_window_cleanup(self):
        """测试窗口清理"""
        ts = time.time()
        
        # 添加过期数据
        self.rolling.update("price", 100.0, ts - 400)  # 400 秒前
        
        # 添加新数据
        self.rolling.update("price", 200.0, ts)
        
        # 过期数据应被清理
        assert self.rolling.count("price") == 1

    def test_multiple_metrics(self):
        """测试多个指标"""
        ts = time.time()
        
        self.rolling.update("price", 100.0, ts)
        self.rolling.update("volume", 50.0, ts)
        
        assert self.rolling.median("price") == 100.0
        assert self.rolling.median("volume") == 50.0

    def test_empty_metric(self):
        """测试空指标"""
        assert self.rolling.median("nonexistent") == 0.0
        assert self.rolling.mad("nonexistent") == 0.0
        assert self.rolling.zscore("nonexistent") == 0.0
        assert self.rolling.count("nonexistent") == 0

    def test_mean_and_std(self):
        """测试均值和标准差（辅助函数）"""
        ts = time.time()
        
        values = [10.0, 20.0, 30.0]
        for i, v in enumerate(values):
            self.rolling.update("metric", v, ts + i)
        
        mean = self.rolling.mean("metric")
        assert mean == pytest.approx(20.0)
        
        std = self.rolling.std("metric")
        assert std > 0

    def test_clear_specific_metric(self):
        """测试清空特定指标"""
        ts = time.time()
        
        self.rolling.update("price", 100.0, ts)
        self.rolling.update("volume", 50.0, ts)
        
        self.rolling.clear("price")
        
        assert self.rolling.count("price") == 0
        assert self.rolling.count("volume") == 1

    def test_clear_all(self):
        """测试清空所有"""
        ts = time.time()
        
        self.rolling.update("price", 100.0, ts)
        self.rolling.update("volume", 50.0, ts)
        
        self.rolling.clear()
        
        assert self.rolling.count("price") == 0
        assert self.rolling.count("volume") == 0
