"""
TOXICTIDE Reason Codes 测试
"""

import pytest

from toxictide.risk.reason_codes import (
    DAILY_LOSS_EXCEEDED,
    DATA_STALE,
    IMPACT_HARD_CAP_EXCEEDED,
    format_reason,
)


class TestReasonCodes:
    """测试 Reason Codes"""

    def test_format_daily_loss_exceeded(self):
        """测试日亏超限格式化"""
        facts = {
            "daily_pnl_pct": -1.5,
            "max_daily_loss_pct": 1.0,
        }
        
        text = format_reason(DAILY_LOSS_EXCEEDED, facts)
        
        assert "-1.50%" in text
        assert "-1.00%" in text

    def test_format_data_stale(self):
        """测试数据过期格式化"""
        facts = {"stale_sec": 15.5}
        
        text = format_reason(DATA_STALE, facts)
        
        assert "15.5" in text

    def test_format_impact_hard_cap(self):
        """测试冲击硬上限格式化"""
        facts = {
            "impact_bps": 25.0,
            "hard_cap_bps": 20.0,
        }
        
        text = format_reason(IMPACT_HARD_CAP_EXCEEDED, facts)
        
        assert "25.00" in text
        assert "20.00" in text

    def test_format_unknown_code(self):
        """测试未知编码"""
        text = format_reason("UNKNOWN_CODE", {})
        
        assert text == "UNKNOWN_CODE"
