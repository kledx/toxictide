#!/usr/bin/env python3
"""
TOXICTIDE 主入口（静默版本）

日志输出到文件，终端只显示 CLI 交互界面
"""

import sys
import logging
from pathlib import Path

import structlog

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config, get_config_dict
from toxictide.ui.cli import CLI

# 创建 logs 目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 配置 structlog 输出到文件
log_file = log_dir / "system.log"

# 配置标准 logging 输出到文件
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(message)s'
)

# 配置 structlog 使用文件输出
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=open(log_file, "a")),
)

logger = structlog.get_logger(__name__)


def main():
    """主函数"""
    try:
        # 清屏（可选）
        # import os
        # os.system('cls' if os.name == 'nt' else 'clear')

        # 加载配置
        config_obj = load_config()
        config = get_config_dict(config_obj)

        # 初始化 Orchestrator（日志会输出到文件）
        orchestrator = Orchestrator(config)

        # 启动 CLI（终端只显示这个）
        cli = CLI(orchestrator)
        cli.start()

        # 运行主循环
        orchestrator.run()

    except KeyboardInterrupt:
        print("\n\n👋 系统正在关闭...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        logger.error("fatal_error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
