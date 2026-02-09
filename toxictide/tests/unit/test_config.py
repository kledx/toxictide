"""
TOXICTIDE 配置管理测试
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from toxictide.config_loader import (
    load_config,
    get_config_dict,
    AppConfig,
    MarketConfig,
    RiskConfig,
    OADConfig,
    VADConfig,
    _deep_merge,
    _parse_env_value,
)
from toxictide.exceptions import ConfigValidationError


class TestConfigModels:
    """测试配置模型"""

    def test_market_config_defaults(self):
        """测试市场配置默认值"""
        config = MarketConfig()
        assert config.symbols == ["ETH-PERP"]
        assert config.orderbook_depth == 20
        assert config.tape_window_sec == 300

    def test_market_config_validation(self):
        """测试市场配置验证"""
        with pytest.raises(ValueError):
            MarketConfig(orderbook_depth=1)  # 太小

        with pytest.raises(ValueError):
            MarketConfig(orderbook_depth=200)  # 太大

    def test_oad_config_z_danger_greater_than_z_warn(self):
        """测试 OAD 配置 z_danger > z_warn"""
        with pytest.raises(ValueError, match="z_danger"):
            OADConfig(z_warn=6.0, z_danger=4.0)  # danger < warn

    def test_vad_config_validation(self):
        """测试 VAD 配置验证"""
        # z_danger > z_warn
        with pytest.raises(ValueError):
            VADConfig(z_warn=6.0, z_danger=4.0)

        # toxic_danger > toxic_warn
        with pytest.raises(ValueError):
            VADConfig(toxic_warn=0.8, toxic_danger=0.6)

    def test_risk_config_validation(self):
        """测试风控配置验证"""
        # impact_hard_cap > impact_entry_cap
        with pytest.raises(ValueError):
            RiskConfig(impact_entry_cap_bps=20.0, impact_hard_cap_bps=10.0)

    def test_app_config_defaults(self):
        """测试应用配置默认值"""
        config = AppConfig()
        assert config.environment == "dev"
        assert config.execution.mode == "paper"
        assert config.logging.level == "INFO"


class TestDeepMerge:
    """测试深度合并"""

    def test_simple_merge(self):
        """测试简单合并"""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """测试嵌套合并"""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}
        result = _deep_merge(base, override)

        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_override_non_dict(self):
        """测试覆盖非字典值"""
        base = {"a": {"nested": 1}}
        override = {"a": "string_value"}
        result = _deep_merge(base, override)

        assert result == {"a": "string_value"}


class TestParseEnvValue:
    """测试环境变量值解析"""

    def test_parse_bool_true(self):
        """测试解析布尔值 True"""
        assert _parse_env_value("true") is True
        assert _parse_env_value("True") is True
        assert _parse_env_value("yes") is True
        assert _parse_env_value("1") is True

    def test_parse_bool_false(self):
        """测试解析布尔值 False"""
        assert _parse_env_value("false") is False
        assert _parse_env_value("False") is False
        assert _parse_env_value("no") is False
        assert _parse_env_value("0") is False

    def test_parse_int(self):
        """测试解析整数"""
        assert _parse_env_value("42") == 42
        assert _parse_env_value("-10") == -10

    def test_parse_float(self):
        """测试解析浮点数"""
        assert _parse_env_value("3.14") == 3.14
        assert _parse_env_value("-2.5") == -2.5

    def test_parse_list(self):
        """测试解析列表"""
        result = _parse_env_value("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_string(self):
        """测试解析字符串"""
        assert _parse_env_value("hello") == "hello"


class TestLoadConfig:
    """测试配置加载"""

    def test_load_default_config(self):
        """测试加载默认配置"""
        config = load_config(environment="dev")
        assert isinstance(config, AppConfig)
        assert config.environment == "dev"

    def test_load_test_environment(self):
        """测试加载测试环境配置"""
        config = load_config(environment="test")
        assert config.environment == "test"
        assert config.logging.level == "WARNING"

    def test_env_variable_override(self):
        """测试环境变量覆盖"""
        with patch.dict(os.environ, {"TOXICTIDE_EXECUTION_MODE": "real"}):
            config = load_config(environment="dev")
            assert config.execution.mode == "real"

    def test_get_config_dict(self):
        """测试配置转字典"""
        config = AppConfig()
        config_dict = get_config_dict(config)

        assert isinstance(config_dict, dict)
        assert "environment" in config_dict
        assert "market" in config_dict
        assert "risk" in config_dict


class TestConfigValidation:
    """测试配置验证错误处理"""

    def test_invalid_execution_mode(self):
        """测试无效的执行模式"""
        with pytest.raises(ValueError):
            AppConfig(execution={"mode": "invalid"})

    def test_invalid_log_level(self):
        """测试无效的日志级别"""
        with pytest.raises(ValueError):
            AppConfig(logging={"level": "INVALID"})
