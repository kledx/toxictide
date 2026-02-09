#!/usr/bin/env python3
"""
实时市场数据采集器 - 币安 WebSocket
"""

import asyncio
import json
import time
import structlog
import websockets
from typing import Optional, Callable
from collections import deque

from toxictide.models import OrderBookLevel, OrderBookState, Trade

logger = structlog.get_logger()


class BinanceMarketCollector:
    """币安市场数据采集器（WebSocket）"""

    def __init__(self, symbol: str = "ETHUSDT", testnet: bool = False):
        """
        初始化采集器

        Args:
            symbol: 交易对符号（如 "ETHUSDT"）
            testnet: 是否使用测试网（注意：测试网不提供 WebSocket 数据，建议使用主网）
        """
        self.symbol = symbol.lower()
        self._testnet = testnet

        # WebSocket URLs - 使用币安合约（Futures）端点
        # 官方文档：https://developers.binance.com/docs/zh-CN/derivatives/usds-margined-futures/websocket-market-streams
        # Base URL: wss://fstream.binance.com
        # 组合流格式: /stream?streams=<stream1>/<stream2>
        if self._testnet:
            self._ws_base = "wss://stream.binancefuture.com"
        else:
            self._ws_base = "wss://fstream.binance.com"

        # 数据缓冲
        self._orderbook_snapshot: Optional[OrderBookState] = None
        self._trade_buffer: deque = deque(maxlen=1000)

        # 连接状态
        self._connected = False
        self._ws_task: Optional[asyncio.Task] = None

        # 序列号
        self._last_update_id = 0

        logger.info("binance_collector_init", symbol=symbol, testnet=testnet)

    async def start(self):
        """启动 WebSocket 连接"""
        self._ws_task = asyncio.create_task(self._run_websocket())

        # 等待初始快照
        max_wait = 10
        waited = 0
        while not self._orderbook_snapshot and waited < max_wait:
            await asyncio.sleep(0.5)
            waited += 0.5

        if self._orderbook_snapshot:
            logger.info("binance_collector_ready", symbol=self.symbol)
            self._connected = True
        else:
            logger.error("binance_collector_timeout", symbol=self.symbol)

    async def stop(self):
        """停止 WebSocket 连接"""
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        self._connected = False
        logger.info("binance_collector_stopped", symbol=self.symbol)

    async def _run_websocket(self):
        """运行 WebSocket 主循环"""

        # 正确的组合流格式（根据币安官方文档）
        # 现货: wss://stream.binance.com:9443/stream?streams=<stream1>/<stream2>
        streams = f"{self.symbol}@depth20@100ms/{self.symbol}@trade"
        ws_url = f"{self._ws_base}/stream?streams={streams}"

        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    logger.info("binance_ws_connected", url=ws_url)

                    async for message in ws:
                        try:
                            msg = json.loads(message)

                            # 组合流的响应格式：{"stream":"...", "data":{...}}
                            if "data" not in msg:
                                continue

                            data = msg["data"]

                            # 处理深度数据
                            if "e" in data and data["e"] == "depthUpdate":
                                self._handle_depth_update(data)

                            # 处理交易数据
                            elif "e" in data and data["e"] == "trade":
                                self._handle_trade(data)

                        except Exception as e:
                            logger.error("binance_ws_message_error",
                                       error=str(e),
                                       exc_info=True)

            except Exception as e:
                logger.error("binance_ws_error",
                           error=str(e),
                           exc_info=True)
                await asyncio.sleep(5)  # 重连延迟

    def _handle_depth_update(self, data: dict):
        """处理深度更新"""

        try:
            # 提取盘口数据
            bids_data = data.get("b", [])
            asks_data = data.get("a", [])
            update_id = data.get("u", 0)

            # 转换为 OrderBookLevel
            bids = [
                OrderBookLevel(price=float(price), size=float(qty))
                for price, qty in bids_data
            ]
            asks = [
                OrderBookLevel(price=float(price), size=float(qty))
                for price, qty in asks_data
            ]

            # 确保排序
            bids.sort(key=lambda x: x.price, reverse=True)
            asks.sort(key=lambda x: x.price)

            # 创建快照
            self._orderbook_snapshot = OrderBookState(
                ts=time.time(),
                bids=bids[:20],  # 取前 20 档
                asks=asks[:20],
                seq=update_id
            )

            self._last_update_id = update_id

        except Exception as e:
            logger.error("depth_update_error",
                       error=str(e),
                       exc_info=True)

    def _handle_trade(self, data: dict):
        """处理交易数据"""

        try:
            # 提取价格和数量
            price = float(data["p"])
            size = float(data["q"])

            # 跳过无效数据（币安偶尔会发送 price=0 或 size=0 的数据）
            if price <= 0 or size <= 0:
                logger.debug("invalid_trade_data_skipped", price=price, size=size)
                return

            trade = Trade(
                ts=data["T"] / 1000.0,  # 毫秒转秒
                price=price,
                size=size,
                side="buy" if data["m"] is False else "sell"  # m=true 表示卖方是 maker
            )

            self._trade_buffer.append(trade)

        except Exception as e:
            logger.error("trade_parse_error",
                       error=str(e),
                       exc_info=True)

    def get_orderbook_snapshot(self) -> Optional[OrderBookState]:
        """获取最新盘口快照"""
        return self._orderbook_snapshot

    def get_recent_trades(self, max_count: int = 100) -> list[Trade]:
        """获取最近的交易"""
        return list(self._trade_buffer)[-max_count:]

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected


# 同步包装器（用于主循环）
class BinanceMarketCollectorSync:
    """同步包装器 - 在后台线程运行异步采集器"""

    def __init__(self, symbol: str = "ETHUSDT", testnet: bool = False):
        self._collector = BinanceMarketCollector(symbol, testnet)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[asyncio.Task] = None

    def start(self):
        """启动采集器（同步）"""
        # 在新线程中运行事件循环
        import threading

        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._collector.start())
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

        # 等待连接就绪
        max_wait = 10
        waited = 0
        while not self._collector.is_connected() and waited < max_wait:
            time.sleep(0.5)
            waited += 0.5

        logger.info("binance_sync_collector_ready")

    def stop(self):
        """停止采集器"""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._collector.stop(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)

    def get_orderbook_snapshot(self) -> Optional[OrderBookState]:
        """获取盘口快照"""
        return self._collector.get_orderbook_snapshot()

    def get_recent_trades(self, max_count: int = 100) -> list[Trade]:
        """获取最近交易"""
        return self._collector.get_recent_trades(max_count)

    def is_connected(self) -> bool:
        """连接状态"""
        return self._collector.is_connected()


if __name__ == "__main__":
    # 测试脚本
    import sys

    print("=== 币安市场数据采集测试 ===")
    print()
    print("📡 数据源：币安主网（公开免费数据）")
    print("🔗 WebSocket：wss://stream.binance.com:9443/ws")
    print()
    print("测试内容：")
    print("  1. 连接到币安 WebSocket")
    print("  2. 接收 ETH-USDT 盘口数据")
    print("  3. 接收实时交易数据")
    print("  4. 每 5 秒显示一次数据")
    print()
    print("按 Ctrl+C 停止测试")
    print()

    print("⏳ 正在连接...")
    collector = BinanceMarketCollectorSync(symbol="ETHUSDT", testnet=False)

    try:
        collector.start()

        # 额外等待一下确保连接稳定
        time.sleep(2)

        if not collector.is_connected():
            print("❌ 连接失败！")
            print()
            print("可能的原因：")
            print("  1. 网络连接问题（请检查是否能访问 binance.com）")
            print("  2. 防火墙阻止 WebSocket 连接")
            print("  3. 代理设置问题")
            print()
            print("💡 建议：")
            print("  - 检查网络连接")
            print("  - 尝试访问 https://www.binance.com 确认可以访问")
            print("  - 如果使用代理，请配置正确")
            sys.exit(1)

        print("✅ 已连接到币安主网")
        print()

        count = 0
        while True:
            time.sleep(5)
            count += 1

            print(f"--- 数据更新 #{count} ---")

            # 显示盘口
            book = collector.get_orderbook_snapshot()
            if book:
                print(f"盘口时间: {time.strftime('%H:%M:%S', time.localtime(book.ts))}")
                print(f"最优买价: ${book.bids[0].price:.2f} x {book.bids[0].size:.4f}")
                print(f"最优卖价: ${book.asks[0].price:.2f} x {book.asks[0].size:.4f}")
                print(f"价差: {book.spread:.2f} ({book.spread / book.mid * 10000:.2f} bps)")

            # 显示交易
            trades = collector.get_recent_trades(max_count=5)
            if trades:
                print(f"\n最近 5 笔交易:")
                for t in trades[-5:]:
                    side_icon = "🟢" if t.side == "buy" else "🔴"
                    print(f"  {side_icon} ${t.price:.2f} x {t.size:.4f}")

            print()

    except KeyboardInterrupt:
        print("\n正在停止...")
        collector.stop()
        print("已停止")
