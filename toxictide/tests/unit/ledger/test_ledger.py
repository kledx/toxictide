"""
TOXICTIDE Ledger 测试
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from toxictide.ledger.ledger import Ledger, read_ledger
from toxictide.models import (
    ExecutionPlan,
    FeatureVector,
    LedgerRecord,
    MarketStressIndex,
    OrderbookAnomalyReport,
    RegimeState,
    RiskDecision,
    VolumeAnomalyReport,
)


class TestLedger:
    """测试 Ledger"""

    def setup_method(self):
        """每个测试前初始化"""
        self.temp_dir = tempfile.mkdtemp()

    def _create_minimal_record(self) -> LedgerRecord:
        """创建最小化的 LedgerRecord"""
        return LedgerRecord(
            ts=time.time(),
            policy={},
            features=FeatureVector(
                ts=time.time(),
                mid=2000.0,
                spread=1.0,
                spread_bps=5.0,
                top_bid_sz=10.0,
                top_ask_sz=10.0,
                depth_bid_k=50000.0,
                depth_ask_k=50000.0,
                imb_k=0.0,
                micro_minus_mid=0.0,
                impact_buy_bps=5.0,
                impact_sell_bps=5.0,
                msg_rate=10.0,
                churn=1000.0,
                vol=100.0,
                trades=10,
                avg_trade=10.0,
                max_trade=20.0,
                signed_imb=0.0,
                toxic=0.3,
            ),
            oad=OrderbookAnomalyReport(
                ts=time.time(),
                level="OK",
                score=0.0,
                triggers={},
                liquidity_state="THICK",
            ),
            vad=VolumeAnomalyReport(
                ts=time.time(),
                level="OK",
                score=0.0,
                triggers={},
                events={},
            ),
            stress=MarketStressIndex(
                ts=time.time(),
                level="OK",
                score=0.0,
                components={},
            ),
            regime=RegimeState(
                ts=time.time(),
                price_regime="RANGE",
                vol_regime="NORMALVOL",
                flow_regime="CALM",
                confidence=0.8,
            ),
            signal=None,
            risk=RiskDecision(
                ts=time.time(),
                action="DENY",
                size_usd=0.0,
                max_slippage_bps=0.0,
                reasons=["NO_SIGNAL"],
                facts={},
            ),
            plan=ExecutionPlan(
                ts=time.time(),
                orders=[],
                mode="reduce_only",
                reasons=[],
            ),
            fills=[],
            explain="无信号",
        )

    def test_initialization(self):
        """测试初始化"""
        ledger = Ledger(log_dir=self.temp_dir)

        assert ledger.log_path.exists()
        assert ledger.log_path.parent == Path(self.temp_dir)

        ledger.close()

    def test_append_single_record(self):
        """测试追加单条记录"""
        ledger = Ledger(log_dir=self.temp_dir)
        record = self._create_minimal_record()

        ledger.append(record)
        ledger.close()

        # 验证文件内容
        with open(ledger.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 1

        # 验证 JSON 格式
        data = json.loads(lines[0])
        assert "ts" in data
        assert "policy" in data
        assert "features" in data

    def test_append_multiple_records(self):
        """测试追加多条记录"""
        ledger = Ledger(log_dir=self.temp_dir)

        for _ in range(5):
            record = self._create_minimal_record()
            ledger.append(record)

        ledger.close()

        with open(ledger.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 5

    def test_context_manager(self):
        """测试上下文管理器"""
        with Ledger(log_dir=self.temp_dir) as ledger:
            record = self._create_minimal_record()
            ledger.append(record)

        # 文件应该自动关闭
        assert ledger._file.closed

    def test_read_ledger(self):
        """测试读取日志"""
        ledger = Ledger(log_dir=self.temp_dir)

        records_written = []
        for _ in range(3):
            record = self._create_minimal_record()
            records_written.append(record)
            ledger.append(record)

        ledger.close()

        # 读取日志
        records_read = read_ledger(str(ledger.log_path))

        assert len(records_read) == 3
        assert all(isinstance(r, LedgerRecord) for r in records_read)

    def test_log_path_property(self):
        """测试 log_path 属性"""
        ledger = Ledger(log_dir=self.temp_dir)

        assert isinstance(ledger.log_path, Path)
        assert "session_" in ledger.log_path.name
        assert ledger.log_path.suffix == ".jsonl"

        ledger.close()

    def test_directory_creation(self):
        """测试目录自动创建"""
        non_existent_dir = Path(self.temp_dir) / "subdir" / "logs"

        ledger = Ledger(log_dir=str(non_existent_dir))

        assert non_existent_dir.exists()

        ledger.close()
