"""
TOXICTIDE 配置管理

支持多环境配置加载、环境变量覆盖、Pydantic 验证。

配置优先级（从高到低）：
1. CLI 参数
2. 环境变量
3. 指定的配置文件
4. default.yaml
"""

import os
from pathlib import Path
from typing import Any, Literal

import structlog
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from toxictide.exceptions import ConfigNotFoundError, ConfigValidationError

logger = structlog.get_logger(__name__)

# 加载 .env 文件
load_dotenv()


# ============================================================================
# 配置 Schema (Pydantic 验证)
# ============================================================================

class MarketConfig(BaseModel):
    """市场配置"""
    symbols: list[str] = Field(default=["ETH-PERP"])
    orderbook_depth: int = Field(default=20, ge=5, le=100)
    tape_window_sec: int = Field(default=300, ge=60, le=3600)


class FeaturesConfig(BaseModel):
    """特征配置"""
    impact_size_quote_usd: float = Field(default=1000.0, gt=0)
    rolling_window_short_sec: int = Field(default=300, ge=60)
    rolling_window_long_sec: int = Field(default=3600, ge=300)


class OADConfig(BaseModel):
    """盘口异常检测配置"""
    z_warn: float = Field(default=4.0, gt=0)
    z_danger: float = Field(default=6.0, gt=0)

    @field_validator("z_danger")
    @classmethod
    def z_danger_must_be_greater_than_z_warn(cls, v: float, info) -> float:
        z_warn = info.data.get("z_warn", 4.0)
        if v <= z_warn:
            raise ValueError(f"z_danger ({v}) must be greater than z_warn ({z_warn})")
        return v


class VADConfig(BaseModel):
    """成交量异常检测配置"""
    z_warn: float = Field(default=4.0, gt=0)
    z_danger: float = Field(default=6.0, gt=0)
    toxic_warn: float = Field(default=0.6, ge=0, le=1)
    toxic_danger: float = Field(default=0.75, ge=0, le=1)

    @field_validator("z_danger")
    @classmethod
    def z_danger_must_be_greater_than_z_warn(cls, v: float, info) -> float:
        z_warn = info.data.get("z_warn", 4.0)
        if v <= z_warn:
            raise ValueError(f"z_danger ({v}) must be greater than z_warn ({z_warn})")
        return v

    @field_validator("toxic_danger")
    @classmethod
    def toxic_danger_must_be_greater_than_toxic_warn(cls, v: float, info) -> float:
        toxic_warn = info.data.get("toxic_warn", 0.6)
        if v <= toxic_warn:
            raise ValueError(
                f"toxic_danger ({v}) must be greater than toxic_warn ({toxic_warn})"
            )
        return v


class RiskConfig(BaseModel):
    """风控配置"""
    max_daily_loss_pct: float = Field(default=1.0, gt=0, le=100)
    max_leverage: float = Field(default=2.0, ge=1, le=100)
    max_position_notional: float = Field(default=3000.0, gt=0)
    impact_entry_cap_bps: float = Field(default=10.0, gt=0)
    impact_hard_cap_bps: float = Field(default=20.0, gt=0)

    @field_validator("impact_hard_cap_bps")
    @classmethod
    def impact_hard_cap_must_be_greater_than_entry_cap(cls, v: float, info) -> float:
        entry_cap = info.data.get("impact_entry_cap_bps", 10.0)
        if v <= entry_cap:
            raise ValueError(
                f"impact_hard_cap_bps ({v}) must be greater than "
                f"impact_entry_cap_bps ({entry_cap})"
            )
        return v


class ExecutionConfig(BaseModel):
    """执行配置"""
    mode: Literal["paper", "real"] = Field(default="paper")
    slicing_threshold_bps: float = Field(default=10.0, gt=0)


class LoggingConfig(BaseModel):
    """日志配置"""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    format: Literal["json", "console"] = Field(default="json")


class AppConfig(BaseModel):
    """应用总配置"""
    environment: Literal["dev", "test", "prod"] = Field(default="dev")
    market: MarketConfig = Field(default_factory=MarketConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    oad: OADConfig = Field(default_factory=OADConfig)
    vad: VADConfig = Field(default_factory=VADConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# ============================================================================
# 配置加载器
# ============================================================================

def _get_config_dir() -> Path:
    """获取配置目录路径"""
    # 首先检查环境变量
    config_dir = os.getenv("TOXICTIDE_CONFIG_DIR")
    if config_dir:
        return Path(config_dir)

    # 默认使用 toxictide/config/
    return Path(__file__).parent / "config"


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """加载 YAML 文件"""
    if not path.exists():
        raise ConfigNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    return content or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深度合并两个字典

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的字典
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """应用环境变量覆盖

    支持的环境变量格式：TOXICTIDE_<SECTION>_<KEY>
    例如：TOXICTIDE_EXECUTION_MODE=real
    """
    env_prefix = "TOXICTIDE_"

    for key, value in os.environ.items():
        if not key.startswith(env_prefix):
            continue

        # 解析环境变量名
        parts = key[len(env_prefix):].lower().split("_")
        if len(parts) < 2:
            continue

        section = parts[0]
        field = "_".join(parts[1:])

        # 应用覆盖
        if section in config:
            if isinstance(config[section], dict):
                # 尝试转换类型
                config[section][field] = _parse_env_value(value)
                logger.debug(
                    "env_override_applied",
                    env_var=key,
                    section=section,
                    field=field,
                    value=value,
                )

    return config


def _parse_env_value(value: str) -> Any:
    """解析环境变量值为适当的类型"""
    # 布尔值
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False

    # 数字
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # 列表（逗号分隔）
    if "," in value:
        return [v.strip() for v in value.split(",")]

    return value


def load_config(
    environment: str | None = None,
    config_path: Path | str | None = None,
) -> AppConfig:
    """加载配置

    Args:
        environment: 环境名称（dev/test/prod），如果未指定则从环境变量或默认值获取
        config_path: 自定义配置文件路径

    Returns:
        验证后的 AppConfig 对象

    Raises:
        ConfigNotFoundError: 配置文件不存在
        ConfigValidationError: 配置验证失败
    """
    config_dir = _get_config_dir()

    # 1. 加载默认配置
    default_path = config_dir / "default.yaml"
    if default_path.exists():
        config = _load_yaml_file(default_path)
        logger.debug("default_config_loaded", path=str(default_path))
    else:
        config = {}
        logger.warning("default_config_not_found", path=str(default_path))

    # 2. 确定环境
    if environment is None:
        environment = os.getenv("TOXICTIDE_ENVIRONMENT", "dev")

    # 3. 加载环境配置
    env_path = config_dir / f"{environment}.yaml"
    if env_path.exists():
        env_config = _load_yaml_file(env_path)
        config = _deep_merge(config, env_config)
        logger.debug("env_config_loaded", environment=environment, path=str(env_path))

    # 4. 加载自定义配置（如果指定）
    if config_path:
        custom_path = Path(config_path)
        custom_config = _load_yaml_file(custom_path)
        config = _deep_merge(config, custom_config)
        logger.debug("custom_config_loaded", path=str(custom_path))

    # 5. 应用环境变量覆盖
    config = _apply_env_overrides(config)

    # 6. Pydantic 验证
    try:
        app_config = AppConfig(**config)
        logger.info(
            "config_loaded",
            environment=app_config.environment,
            execution_mode=app_config.execution.mode,
        )
        return app_config
    except Exception as e:
        raise ConfigValidationError(f"Config validation failed: {e}") from e


def get_config_dict(config: AppConfig) -> dict[str, Any]:
    """将配置对象转换为字典

    Args:
        config: AppConfig 对象

    Returns:
        配置字典
    """
    return config.model_dump()
