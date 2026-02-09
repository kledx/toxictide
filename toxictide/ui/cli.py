"""
TOXICTIDE CLI

命令行界面
"""

import threading

import structlog

from toxictide.app import Orchestrator
from toxictide.explain.explain import build_explanation

logger = structlog.get_logger(__name__)


class CLI:
    """命令行界面

    简单、直观的交互式命令行界面。

    **支持命令：**
    - /status - 显示系统状态
    - /pause - 暂停交易
    - /resume - 恢复交易
    - /why - 显示最后决策解释
    - /quit - 退出系统

    Example:
        >>> orch = Orchestrator(config)
        >>> cli = CLI(orch)
        >>> cli.start()
        >>> # 在另一个线程中监听用户输入
    """

    def __init__(self, orchestrator: Orchestrator) -> None:
        """初始化 CLI

        Args:
            orchestrator: Orchestrator 实例
        """
        self._orch = orchestrator
        self._thread = None

        logger.info("cli_initialized")

    def start(self) -> None:
        """启动 CLI（后台线程）"""
        self._thread = threading.Thread(target=self._input_loop, daemon=True)
        self._thread.start()

        logger.info("cli_started")

    def _input_loop(self) -> None:
        """输入循环（在后台线程运行）"""
        print("\n" + "=" * 60)
        print("TOXICTIDE 交易系统已启动")
        print("=" * 60)
        print("\n可用命令:")
        print("  /status  - 显示系统状态")
        print("  /pause   - 暂停交易")
        print("  /resume  - 恢复交易")
        print("  /why     - 显示最后决策解释")
        print("  /quit    - 退出系统")
        print("\n输入命令并按回车...")
        print("=" * 60 + "\n")

        while self._orch.state.running:
            try:
                cmd = input("> ").strip()
                if cmd:
                    self._handle_command(cmd)
            except EOFError:
                break
            except Exception as e:
                logger.error("cli_input_error", error=str(e))

    def _handle_command(self, cmd: str) -> None:
        """处理命令

        Args:
            cmd: 用户输入的命令
        """
        if cmd == "/status":
            self._show_status()

        elif cmd == "/pause":
            self._orch.state.paused = True
            print("⏸️  系统已暂停")

        elif cmd == "/resume":
            self._orch.state.paused = False
            print("▶️  系统已恢复")

        elif cmd == "/quit":
            self._orch.state.running = False
            print("👋 系统正在关闭...")

        elif cmd == "/why":
            self._show_last_decision()

        else:
            print(f"❓ 未知命令: {cmd}")
            print("   输入 /status, /pause, /resume, /why, 或 /quit")

    def _show_status(self) -> None:
        """显示系统状态"""
        state = self._orch.state

        print("\n" + "=" * 60)
        print("📊 系统状态")
        print("=" * 60)

        # 运行状态
        status = "运行中" if not state.paused else "已暂停"
        print(f"状态: {status}")

        # 市场压力
        if state.last_stress:
            stress_emoji = {
                "OK": "🟢",
                "WARN": "🟡",
                "DANGER": "🔴",
            }
            emoji = stress_emoji.get(state.last_stress.level, "⚪")
            print(f"市场压力: {emoji} {state.last_stress.level}")

        # 市场状态
        if state.last_regime:
            print(f"市场状态: {state.last_regime.price_regime} / {state.last_regime.flow_regime}")

        # 价格信息（安全格式化）
        if state.last_features:
            try:
                mid = float(state.last_features.mid)
                spread_bps = float(state.last_features.spread_bps)
                print(f"价格: ${mid:.2f}")
                print(f"价差: {spread_bps:.2f} bps")
            except (ValueError, TypeError, AttributeError):
                print(f"价格: {state.last_features.mid}")
                print(f"价差: {state.last_features.spread_bps} bps")

        print("=" * 60 + "\n")

    def _show_last_decision(self) -> None:
        """显示最后一次决策"""
        state = self._orch.state

        if state.last_decision is None:
            print("\n暂无决策记录\n")
            return

        print("\n" + "=" * 60)
        print("🔍 最后决策")
        print("=" * 60)

        explanation = build_explanation(state.last_decision)
        print(explanation)

        print("=" * 60 + "\n")
