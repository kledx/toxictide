"""
TOXICTIDE - 初始化测试

验证项目基础设施正常工作
"""

import pytest


def test_project_structure():
    """测试项目结构存在"""
    import os

    base_dir = os.path.dirname(os.path.dirname(__file__))

    # 验证核心目录存在
    assert os.path.isdir(os.path.join(base_dir, "market"))
    assert os.path.isdir(os.path.join(base_dir, "features"))
    assert os.path.isdir(os.path.join(base_dir, "detectors"))
    assert os.path.isdir(os.path.join(base_dir, "risk"))
    assert os.path.isdir(os.path.join(base_dir, "execution"))


def test_config_files():
    """测试配置文件存在"""
    import os

    base_dir = os.path.dirname(os.path.dirname(__file__))
    config_dir = os.path.join(base_dir, "config")

    assert os.path.isfile(os.path.join(config_dir, "default.yaml"))
    assert os.path.isfile(os.path.join(config_dir, "dev.yaml"))
    assert os.path.isfile(os.path.join(config_dir, "test.yaml"))


def test_basic_imports():
    """测试基本 Python 导入"""
    # 这些导入应该成功（即使模块为空）
    import toxictide
    import toxictide.market
    import toxictide.features
    import toxictide.detectors


def test_environment():
    """测试 Python 版本"""
    import sys

    # 确保 Python 3.10+
    assert sys.version_info >= (3, 10), "需要 Python 3.10 或更高版本"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
