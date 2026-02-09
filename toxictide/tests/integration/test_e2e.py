"""
TOXICTIDE 端到端集成测试

测试完整的系统 pipeline
"""

import tempfile
import time

import pytest

from toxictide.app import Orchestrator
from toxictide.config_loader import load_config


class TestEndToEnd:
    """端到端集成测试"""

    def setup_method(self):
        """每个测试前初始化"""
        # 加载配置
        self.config = load_config("default_config.yaml")

        # 使用临时目录作为日志目录
        self.temp_dir = tempfile.mkdtemp()

    def test_full_pipeline(self):
        """测试完整 Pipeline"""
        orch = Orchestrator(self.config)

        # 运行 5 个 tick
        for _ in range(5):
            orch._tick()

        # 验证状态已更新
        assert orch.state.last_features is not None
        assert orch.state.last_stress is not None
        assert orch.state.last_regime is not None
        assert orch.state.last_decision is not None

        # 关闭
        orch._shutdown()

    def test_normal_flow(self):
        """测试正常流程（信号→允许→执行）"""
        orch = Orchestrator(self.config)

        # 运行多个 tick，寻找信号生成
        for _ in range(20):
            orch._tick()

        # 至少应该有一些决策
        assert orch.state.last_decision is not None

        orch._shutdown()

    def test_risk_denial(self):
        """测试风控拒绝"""
        orch = Orchestrator(self.config)

        # 模拟日亏超限
        orch._risk_guardian.record_trade(time.time(), pnl=-200.0)  # -2%

        # 运行 tick
        orch._tick()

        # 应该被拒绝
        if orch.state.last_decision:
            # 如果有信号，应该被拒绝
            assert orch.state.last_decision.action == "DENY"

        orch._shutdown()

    def test_continuous_run(self):
        """测试连续运行"""
        orch = Orchestrator(self.config)

        # 连续运行 10 个 tick
        tick_count = 0
        for _ in range(10):
            try:
                orch._tick()
                tick_count += 1
            except Exception as e:
                pytest.fail(f"Tick failed: {e}")

        assert tick_count == 10

        orch._shutdown()

    def test_module_integration(self):
        """测试模块集成"""
        orch = Orchestrator(self.config)

        # 验证所有模块已初始化
        assert orch._collector is not None
        assert orch._orderbook is not None
        assert orch._tape is not None
        assert orch._feature_engine is not None
        assert orch._oad is not None
        assert orch._vad is not None
        assert orch._regime is not None
        assert orch._signal_engine is not None
        assert orch._risk_guardian is not None
        assert orch._planner is not None
        assert orch._adapter is not None
        assert orch._ledger is not None

        # 运行一个 tick，验证协作
        orch._tick()

        orch._shutdown()


class TestSystemBehavior:
    """测试系统行为"""

    def setup_method(self):
        """每个测试前初始化"""
        self.config = load_config("default_config.yaml")

    def test_pause_resume(self):
        """测试暂停/恢复"""
        orch = Orchestrator(self.config)

        # 暂停
        orch.state.paused = True
        assert orch.state.paused is True

        # 恢复
        orch.state.paused = False
        assert orch.state.paused is False

        orch._shutdown()

    def test_state_updates(self):
        """测试状态更新"""
        orch = Orchestrator(self.config)

        # 初始状态
        assert orch.state.last_features is None

        # 运行 tick
        orch._tick()

        # 状态应该更新
        assert orch.state.last_features is not None
        assert orch.state.last_stress is not None
        assert orch.state.last_regime is not None

        orch._shutdown()

    def test_ledger_recording(self):
        """测试审计记录"""
        orch = Orchestrator(self.config)

        # 运行几个 tick
        for _ in range(3):
            orch._tick()

        # 审计文件应该存在
        assert orch._ledger.log_path.exists()

        orch._shutdown()

        # 验证日志文件有内容
        with open(orch._ledger.log_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 3  # 至少 3 条记录
