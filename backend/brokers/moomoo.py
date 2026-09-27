"""
Moomoo (Futu) Broker Integration
Uses futu-api library for API access
"""
from typing import Optional, List
import os

# Note: futu-api requires OpenD gateway running locally
# Download from: https://www.moomoo.com/download


class MoomooBroker:
    def __init__(self):
        self.is_connected = False
        self._ctx = None
        self._trd_ctx = None

    def connect(self, username: str, password: str) -> bool:
        """
        Connect to Moomoo via OpenD gateway
        Note: OpenD must be running on localhost:11111
        """
        try:
            from futu import OpenQuoteContext, OpenSecTradeContext, TrdEnv, TrdMarket

            # Quote context for market data
            self._ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

            # Trade context for order execution (paper trading by default)
            self._trd_ctx = OpenSecTradeContext(
                host='127.0.0.1',
                port=11111,
                trd_env=TrdEnv.SIMULATE  # Use REAL for live trading
            )

            self.is_connected = True
            return True
        except Exception as e:
            print(f"Moomoo connection failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Close Moomoo connections"""
        if self._ctx:
            self._ctx.close()
        if self._trd_ctx:
            self._trd_ctx.close()
        self.is_connected = False

    def get_positions(self) -> List[dict]:
        """Get all current positions"""
        if not self.is_connected:
            return []

        try:
            from futu import RET_OK

            ret, data = self._trd_ctx.position_list_query()
            if ret != RET_OK:
                return []

            result = []
            for _, row in data.iterrows():
                result.append({
                    "symbol": row["code"].split(".")[-1],  # Remove market prefix
                    "quantity": float(row["qty"]),
                    "avg_cost": float(row["cost_price"]),
                    "current_price": float(row["market_val"]) / float(row["qty"]) if row["qty"] > 0 else 0,
                    "market_value": float(row["market_val"]),
                    "unrealized_pl": float(row["pl_val"]),
                    "unrealized_pl_pct": float(row["pl_ratio"]) * 100,
                    "broker": "moomoo"
                })

            return result
        except Exception as e:
            print(f"Error getting Moomoo positions: {e}")
            return []

    def get_quote(self, symbol: str) -> dict:
        """Get current quote for a symbol"""
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            from futu import RET_OK

            # Moomoo uses format like "US.AAPL"
            code = f"US.{symbol}"
            ret, data = self._ctx.get_stock_quote([code])

            if ret != RET_OK:
                return {"error": "Failed to get quote"}

            row = data.iloc[0]
            return {
                "symbol": symbol,
                "price": float(row["last_price"]),
                "bid": float(row["bid_price"]),
                "ask": float(row["ask_price"]),
                "volume": int(row["volume"])
            }
        except Exception as e:
            return {"error": str(e)}

    def buy(self, symbol: str, quantity: int, price: Optional[float] = None) -> dict:
        """Place a buy order"""
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            from futu import RET_OK, TrdSide, OrderType

            code = f"US.{symbol}"

            if price:
                order_type = OrderType.NORMAL  # Limit order
            else:
                order_type = OrderType.MARKET
                price = 0

            ret, data = self._trd_ctx.place_order(
                price=price,
                qty=quantity,
                code=code,
                trd_side=TrdSide.BUY,
                order_type=order_type
            )

            if ret != RET_OK:
                return {"success": False, "error": str(data)}

            return {
                "success": True,
                "order_id": str(data["order_id"].iloc[0]),
                "symbol": symbol,
                "quantity": quantity,
                "side": "buy"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sell(self, symbol: str, quantity: int, price: Optional[float] = None) -> dict:
        """Place a sell order"""
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            from futu import RET_OK, TrdSide, OrderType

            code = f"US.{symbol}"

            if price:
                order_type = OrderType.NORMAL
            else:
                order_type = OrderType.MARKET
                price = 0

            ret, data = self._trd_ctx.place_order(
                price=price,
                qty=quantity,
                code=code,
                trd_side=TrdSide.SELL,
                order_type=order_type
            )

            if ret != RET_OK:
                return {"success": False, "error": str(data)}

            return {
                "success": True,
                "order_id": str(data["order_id"].iloc[0]),
                "symbol": symbol,
                "quantity": quantity,
                "side": "sell"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_take_profit(self, symbol: str, quantity: int, target_price: float) -> dict:
        """Set a take-profit limit sell order"""
        return self.sell(symbol, quantity, target_price)

    def set_stop_loss(self, symbol: str, quantity: int, stop_price: float) -> dict:
        """Set a stop-loss order"""
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            from futu import RET_OK, TrdSide, OrderType

            code = f"US.{symbol}"

            ret, data = self._trd_ctx.place_order(
                price=stop_price,
                qty=quantity,
                code=code,
                trd_side=TrdSide.SELL,
                order_type=OrderType.STOP,
                aux_price=stop_price
            )

            if ret != RET_OK:
                return {"success": False, "error": str(data)}

            return {
                "success": True,
                "order_id": str(data["order_id"].iloc[0]),
                "type": "stop_loss",
                "stop_price": stop_price
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_position(self, symbol: str) -> dict:
        """Close entire position for a symbol"""
        positions = self.get_positions()
        pos = next((p for p in positions if p["symbol"] == symbol), None)

        if not pos:
            return {"error": f"No position found for {symbol}"}

        return self.sell(symbol, int(pos["quantity"]))
