#!/usr/bin/env python3
"""
币安执行适配器 - REST API 交易
"""

import time
import hashlib
import hmac
import requests
import structlog
from typing import Optional
from urllib.parse import urlencode

from toxictide.models import ExecutionPlan, Fill
from toxictide.execution.adapter_base import IExecutionAdapter

logger = structlog.get_logger()


class BinanceExecutionAdapter(IExecutionAdapter):
    """币安执行适配器"""

    def __init__(self, api_key: str, api_secret: str, symbol: str = "ETHUSDT", testnet: bool = True):
        """
        初始化适配器

        Args:
            api_key: API 密钥
            api_secret: API 密钥对应的 Secret
            symbol: 交易对符号
            testnet: 是否使用测试网
        """
        self._api_key = api_key
        self._api_secret = api_secret
        self.symbol = symbol
        self._testnet = testnet

        # API Base URL
        if testnet:
            self._base_url = "https://testnet.binance.vision"
        else:
            self._base_url = "https://api.binance.com"

        # 账户状态缓存
        self._balance = 0.0
        self._position_size = 0.0
        self._position_notional = 0.0

        logger.info("binance_adapter_init", symbol=symbol, testnet=testnet)

    def _sign_request(self, params: dict) -> dict:
        """签名请求参数"""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, endpoint: str, params: dict = None, signed: bool = False) -> dict:
        """发送请求"""
        url = f"{self._base_url}{endpoint}"
        headers = {"X-MBX-APIKEY": self._api_key}

        if params is None:
            params = {}

        if signed:
            params = self._sign_request(params)

        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, params=params, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error("binance_request_error",
                       method=method,
                       endpoint=endpoint,
                       error=str(e),
                       exc_info=True)
            raise

    def execute(self, plan: ExecutionPlan) -> list[Fill]:
        """执行交易计划"""

        if not plan.orders:
            return []

        fills = []

        for order_spec in plan.orders:
            try:
                fill = self._execute_single_order(order_spec, plan.ts)
                if fill:
                    fills.append(fill)

            except Exception as e:
                logger.error("order_execution_failed",
                           order=order_spec,
                           error=str(e),
                           exc_info=True)

        return fills

    def _execute_single_order(self, order_spec: dict, ts: float) -> Optional[Fill]:
        """执行单个订单"""

        order_type = order_spec["type"]
        side = "BUY" if order_spec["side"] == "long" else "SELL"
        size_usd = order_spec["size_usd"]

        # 获取当前价格估算数量
        ticker = self._request("GET", "/api/v3/ticker/price", {"symbol": self.symbol})
        current_price = float(ticker["price"])

        quantity = size_usd / current_price

        # 币安数量精度（ETH 最小 0.001）
        quantity = round(quantity, 3)

        if quantity < 0.001:
            logger.warning("order_too_small", quantity=quantity, min_qty=0.001)
            return None

        # 构造订单参数
        params = {
            "symbol": self.symbol,
            "side": side,
            "quantity": quantity
        }

        # 订单类型
        if order_type == "market":
            params["type"] = "MARKET"
        else:  # limit
            params["type"] = "LIMIT"
            params["timeInForce"] = "GTC"
            params["price"] = order_spec["price"]

        # 发送订单
        logger.info("placing_order", params=params)

        result = self._request("POST", "/api/v3/order", params, signed=True)

        # 解析成交
        executed_qty = float(result.get("executedQty", 0))
        if executed_qty == 0:
            logger.warning("order_not_filled", order_id=result.get("orderId"))
            return None

        # 计算平均成交价
        fills_data = result.get("fills", [])
        total_cost = sum(float(f["price"]) * float(f["qty"]) for f in fills_data)
        total_qty = sum(float(f["qty"]) for f in fills_data)
        avg_price = total_cost / total_qty if total_qty > 0 else current_price

        # 计算手续费
        total_fee = sum(float(f["commission"]) for f in fills_data)

        fill = Fill(
            ts=ts,
            order_id=str(result["orderId"]),
            price=avg_price,
            size=executed_qty,
            fee=total_fee,
            side="buy" if side == "BUY" else "sell"
        )

        logger.info("order_filled",
                   order_id=fill.order_id,
                   price=fill.price,
                   size=fill.size,
                   fee=fill.fee)

        # 更新仓位
        if side == "BUY":
            self._position_size += executed_qty
        else:
            self._position_size -= executed_qty

        self._position_notional = abs(self._position_size * avg_price)

        return fill

    def get_account_state(self) -> dict:
        """获取账户状态"""

        try:
            account = self._request("GET", "/api/v3/account", signed=True)

            # 获取 USDT 余额
            for balance in account.get("balances", []):
                if balance["asset"] == "USDT":
                    self._balance = float(balance["free"]) + float(balance["locked"])
                    break

            return {
                "balance": self._balance,
                "position_size": self._position_size,
                "position_notional": self._position_notional,
                "unrealized_pnl": 0.0  # 现货无未实现盈亏
            }

        except Exception as e:
            logger.error("get_account_error", error=str(e), exc_info=True)
            return {
                "balance": self._balance,
                "position_size": self._position_size,
                "position_notional": self._position_notional,
                "unrealized_pnl": 0.0
            }

    def close_all_positions(self) -> list[Fill]:
        """平掉所有仓位"""

        if abs(self._position_size) < 0.001:
            logger.info("no_position_to_close")
            return []

        # 构造平仓订单
        side = "SELL" if self._position_size > 0 else "BUY"
        quantity = abs(self._position_size)

        params = {
            "symbol": self.symbol,
            "side": side,
            "type": "MARKET",
            "quantity": round(quantity, 3)
        }

        try:
            result = self._request("POST", "/api/v3/order", params, signed=True)

            executed_qty = float(result.get("executedQty", 0))
            fills_data = result.get("fills", [])
            total_cost = sum(float(f["price"]) * float(f["qty"]) for f in fills_data)
            total_qty = sum(float(f["qty"]) for f in fills_data)
            avg_price = total_cost / total_qty if total_qty > 0 else 0

            fill = Fill(
                ts=time.time(),
                order_id=str(result["orderId"]),
                price=avg_price,
                size=executed_qty,
                fee=sum(float(f["commission"]) for f in fills_data),
                side="sell" if side == "SELL" else "buy"
            )

            self._position_size = 0.0
            self._position_notional = 0.0

            logger.info("position_closed", fill=fill)

            return [fill]

        except Exception as e:
            logger.error("close_position_error", error=str(e), exc_info=True)
            return []


if __name__ == "__main__":
    # 测试脚本
    import os
    from dotenv import load_dotenv

    load_dotenv()

    print("=== 币安适配器测试 ===")
    print()

    api_key = os.getenv("BINANCE_TESTNET_API_KEY")
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET")

    if not api_key or not api_secret:
        print("❌ 请先设置环境变量：")
        print("   BINANCE_TESTNET_API_KEY")
        print("   BINANCE_TESTNET_API_SECRET")
        print()
        print("或创建 .env 文件并添加：")
        print("   BINANCE_TESTNET_API_KEY=your_key_here")
        print("   BINANCE_TESTNET_API_SECRET=your_secret_here")
        exit(1)

    adapter = BinanceExecutionAdapter(
        api_key=api_key,
        api_secret=api_secret,
        symbol="ETHUSDT",
        testnet=True
    )

    print("测试 1: 获取账户状态")
    account = adapter.get_account_state()
    print(f"  余额: ${account['balance']:.2f}")
    print(f"  仓位: {account['position_size']:.4f} ETH")
    print(f"  仓位价值: ${account['position_notional']:.2f}")
    print()

    print("✅ 测试完成")
