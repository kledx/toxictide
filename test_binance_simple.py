#!/usr/bin/env python3
"""
极简版本 - 直接测试币安主网 WebSocket 连接
"""

import asyncio
import json
import websockets


async def test_binance_websocket():
    """测试币安主网 WebSocket"""

    print("=== 币安合约 WebSocket 连接测试 ===")
    print()
    print("📡 连接到：wss://fstream.binance.com/stream")
    print("📊 订阅流：ethusdt@depth20@100ms")
    print("💡 说明：U本位永续合约数据（公开免费）")
    print()

    # 币安合约的正确格式（根据官方文档）
    # Base URL: wss://fstream.binance.com
    # 组合流: /stream?streams=<stream1>/<stream2>
    url = "wss://fstream.binance.com/stream?streams=ethusdt@depth20@100ms"

    try:
        print("⏳ 正在连接...")
        async with websockets.connect(url) as websocket:
            print("✅ 连接成功！")
            print()
            print("正在接收数据（10条后自动停止）...")
            print()

            count = 0
            while count < 10:
                message = await websocket.recv()
                msg = json.loads(message)

                # 组合流的响应格式：{"stream":"...", "data":{...}}
                if "data" in msg:
                    data = msg["data"]

                    if "e" in data and data["e"] == "depthUpdate":
                        count += 1

                        # 提取盘口数据
                        bids = data.get("b", [])
                        asks = data.get("a", [])

                        if bids and asks:
                            best_bid = float(bids[0][0])
                            best_ask = float(asks[0][0])
                            spread = best_ask - best_bid
                            mid = (best_bid + best_ask) / 2

                            print(f"#{count:2d} | 价格: ${mid:.2f} | 价差: ${spread:.2f} | "
                                  f"买: ${best_bid:.2f} | 卖: ${best_ask:.2f}")

            print()
            print("✅ 测试成功！接收到 10 条市场数据")
            print()
            print("📊 说明：")
            print("  - WebSocket 连接正常")
            print("  - 能够接收实时盘口数据")
            print("  - 价格数据在持续更新")

    except Exception as e:
        print(f"❌ 连接失败：{e}")
        print()
        print("可能的原因：")
        print("  1. 网络连接问题")
        print("  2. 防火墙阻止 WebSocket（端口 9443）")
        print("  3. 代理设置问题")


if __name__ == "__main__":
    asyncio.run(test_binance_websocket())
