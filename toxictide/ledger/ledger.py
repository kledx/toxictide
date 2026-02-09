"""
TOXICTIDE Ledger

审计日志系统 - JSONL 格式持久化每次决策
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from toxictide.models import LedgerRecord

logger = structlog.get_logger(__name__)


class Ledger:
    """审计日志系统

    以 JSONL 格式记录每次交易决策的完整快照，包括：
    - Policy（策略配置）
    - Features（市场特征）
    - OAD/VAD/Stress（异常检测结果）
    - Regime（市场状态）
    - Signal（交易信号）
    - Risk（风控决策）
    - Plan（执行计划）
    - Fills（成交记录）
    - Explain（可读解释）

    **文件组织：**
    - 按日期分文件：logs/session_YYYYMMDD.jsonl
    - 每条记录一行 JSON
    - 追加模式（append）

    **用途：**
    - 完整审计追踪（监管合规）
    - 决策回放与复现
    - 性能分析与优化
    - 策略回测验证

    Example:
        >>> ledger = Ledger(log_dir="logs")
        >>> ledger.append(ledger_record)
        >>> ledger.close()
    """

    def __init__(self, log_dir: str = "logs") -> None:
        """初始化审计日志

        Args:
            log_dir: 日志目录路径
        """
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

        # 按日期分文件
        date_str = datetime.now().strftime("%Y%m%d")
        self._log_path = self._log_dir / f"session_{date_str}.jsonl"

        # 追加模式打开文件
        self._file = open(self._log_path, "a", encoding="utf-8")

        logger.info(
            "ledger_initialized",
            log_path=str(self._log_path),
        )

    def append(self, record: LedgerRecord) -> None:
        """追加审计记录

        Args:
            record: LedgerRecord 对象
        """
        try:
            # 序列化为 JSON（单行）
            json_str = record.model_dump_json()

            # 写入文件
            self._file.write(json_str + "\n")
            self._file.flush()

            logger.debug("ledger_record_appended", ts=record.ts)

        except Exception as e:
            logger.error(
                "ledger_append_failed",
                error=str(e),
                exc_info=True,
            )

    def close(self) -> None:
        """关闭日志文件"""
        if self._file and not self._file.closed:
            self._file.close()
            logger.info("ledger_closed", log_path=str(self._log_path))

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()

    @property
    def log_path(self) -> Path:
        """获取当前日志文件路径"""
        return self._log_path


def read_ledger(log_path: str) -> list[LedgerRecord]:
    """读取审计日志文件

    Args:
        log_path: 日志文件路径

    Returns:
        LedgerRecord 列表

    Example:
        >>> records = read_ledger("logs/session_20240101.jsonl")
        >>> for record in records:
        ...     print(record.risk.action)
    """
    records = []

    with open(log_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                record = LedgerRecord(**data)
                records.append(record)
            except Exception as e:
                logger.warning(
                    "ledger_read_line_failed",
                    line_num=line_num,
                    error=str(e),
                )

    logger.info("ledger_read_completed", records_count=len(records))

    return records
