"""
TOXICTIDE Stress Index 测试
"""

import time

import pytest

from toxictide.detectors.stress import compute_stress
from toxictide.models import (
    OrderbookAnomalyReport,
    VolumeAnomalyReport,
)


class TestComputeStress:
    """测试 compute_stress"""

    def _create_oad_report(
        self,
        level: str = "OK",
        score: float = 0.0,
    ) -> OrderbookAnomalyReport:
        """创建 OAD 报告"""
        return OrderbookAnomalyReport(
            ts=time.time(),
            level=level,
            score=score,
            triggers={
                "spread_z": 0.0,
                "impact_buy_z": 0.0,
                "impact_sell_z": 0.0,
                "msg_rate_z": 0.0,
                "gap_flag": 0.0,
            },
            liquidity_state="THICK",
        )

    def _create_vad_report(
        self,
        level: str = "OK",
        score: float = 0.0,
        toxic: float = 0.3,
    ) -> VolumeAnomalyReport:
        """创建 VAD 报告"""
        return VolumeAnomalyReport(
            ts=time.time(),
            level=level,
            score=score,
            triggers={
                "vol_z": 0.0,
                "trades_z": 0.0,
                "max_trade_z": 0.0,
                "signed_imb": 0.0,
                "toxic": toxic,
            },
            events={
                "burst": False,
                "drought": False,
                "whale": False,
            },
        )

    def test_both_ok(self):
        """测试双 OK"""
        oad = self._create_oad_report("OK", 1.0)
        vad = self._create_vad_report("OK", 1.0)
        
        stress = compute_stress(oad, vad, {})
        
        assert stress.level == "OK"

    def test_oad_warn(self):
        """测试 OAD WARN"""
        oad = self._create_oad_report("WARN", 5.0)
        vad = self._create_vad_report("OK", 1.0)
        
        stress = compute_stress(oad, vad, {})
        
        assert stress.level == "WARN"

    def test_vad_warn(self):
        """测试 VAD WARN"""
        oad = self._create_oad_report("OK", 1.0)
        vad = self._create_vad_report("WARN", 5.0)
        
        stress = compute_stress(oad, vad, {})
        
        assert stress.level == "WARN"

    def test_oad_danger(self):
        """测试 OAD DANGER"""
        oad = self._create_oad_report("DANGER", 10.0)
        vad = self._create_vad_report("OK", 1.0)
        
        stress = compute_stress(oad, vad, {})
        
        assert stress.level == "DANGER"

    def test_vad_danger(self):
        """测试 VAD DANGER"""
        oad = self._create_oad_report("OK", 1.0)
        vad = self._create_vad_report("DANGER", 10.0)
        
        stress = compute_stress(oad, vad, {})
        
        assert stress.level == "DANGER"

    def test_max_level_selection(self):
        """测试取最高风险等级"""
        # OAD WARN, VAD DANGER → 应该是 DANGER
        oad = self._create_oad_report("WARN", 5.0)
        vad = self._create_vad_report("DANGER", 10.0)
        
        stress = compute_stress(oad, vad, {})
        
        assert stress.level == "DANGER"

    def test_score_calculation(self):
        """测试综合分数计算"""
        oad = self._create_oad_report("OK", 2.0)
        vad = self._create_vad_report("OK", 1.0, toxic=0.5)
        
        stress = compute_stress(oad, vad, {})
        
        # score = 2.0 * 0.5 + 1.0 * 0.3 + 0.5 * 5.0
        #       = 1.0 + 0.3 + 2.5 = 3.8
        assert stress.score == pytest.approx(3.8)

    def test_components_recorded(self):
        """测试组件得分记录"""
        oad = self._create_oad_report("OK", 2.0)
        oad.triggers["spread_z"] = 3.0
        oad.triggers["impact_buy_z"] = 4.0
        
        vad = self._create_vad_report("OK", 1.0, toxic=0.5)
        vad.triggers["vol_z"] = 2.0
        
        stress = compute_stress(oad, vad, {})
        
        assert "oad_score" in stress.components
        assert "vad_score" in stress.components
        assert "spread_z" in stress.components
        assert "impact_z" in stress.components
        assert "toxic" in stress.components
        assert "vol_z" in stress.components
        
        assert stress.components["oad_score"] == 2.0
        assert stress.components["vad_score"] == 1.0
        assert stress.components["spread_z"] == 3.0
        assert stress.components["impact_z"] == 4.0  # max(4.0, 0.0)
        assert stress.components["toxic"] == 0.5
        assert stress.components["vol_z"] == 2.0

    def test_high_toxic_impact(self):
        """测试高毒性流的影响"""
        oad = self._create_oad_report("OK", 0.0)
        vad = self._create_vad_report("OK", 0.0, toxic=0.8)
        
        stress = compute_stress(oad, vad, {})
        
        # toxic * 5.0 = 0.8 * 5.0 = 4.0
        assert stress.score >= 4.0
