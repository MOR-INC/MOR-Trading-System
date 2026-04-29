"""
Robinhood Broker Integration
Uses robin_stocks library for API access
"""
import robin_stocks.robinhood as rh
from typing import Optional, List
import os


class RobinhoodBroker:
    def __init__(self):
        self.is_connected = False
        self._username = None

    def connect(self, username: str, password: str, mfa_code: Optional[str] = None) -> bool:
        """Authenticate with Robinhood"""
        try:
            if mfa_code:
                login = rh.login(username, password, mfa_code=mfa_code)
            else:
                login = rh.login(username, password)

            self.is_connected = True
            self._username = username
            return True
        except Exception as e:
            print(f"Robinhood login failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Logout from Robinhood"""
        rh.logout()
        self.is_connected = False

    def get_account_info(self) -> dict:
        """Get account profile and buying power"""
        if not self.is_connected:
            return {"error": "Not connected"}

        profile = rh.profiles.load_account_profile()
        return {
            "buying_power": float(profile.get("buying_power", 0)),
            "cash": float(profile.get("cash", 0)),
            "portfolio_value": float(profile.get("portfolio_cash", 0))
        }

    def get_positions(self) -> List[dict]:
        """Get all current positions"""
        if not self.is_connected:
            return []

        positions = rh.account.get_open_stock_positions()
        result = []

        for pos in positions:
            instrument = rh.stocks.get_instrument_by_url(pos["instrument"])
            symbol = instrument.get("symbol", "UNKNOWN")
            quantity = float(pos.get("quantity", 0))
            avg_cost = float(pos.get("average_buy_price", 0))

            # Get current price
            quote = rh.stocks.get_latest_price(symbol)
            current_price = float(quote[0]) if quote else 0

            result.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": quantity * current_price,
                "unrealized_pl": (current_price - avg_cost) * quantity,
                "unrealized_pl_pct": ((current_price / avg_cost) - 1) * 100 if avg_cost > 0 else 0,
                "broker": "robinhood"
            })

        return result

    def get_quote(self, symbol: str) -> dict:
        """Get current quote for a symbol"""
        if not self.is_connected:
            return {"error": "Not connected"}

        quote = rh.stocks.get_stock_quote_by_symbol(symbol)
        return {
            "symbol": symbol,
            "price": float(quote.get("last_trade_price", 0)),
            "bid": float(quote.get("bid_price", 0)),
            "ask": float(quote.get("ask_price", 0)),
            "volume": int(quote.get("volume", 0))
        }

    def buy(self, symbol: str, quantity: int, price: Optional[float] = None) -> dict:
        """Place a buy order"""
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            if price:
                # Limit order
                order = rh.orders.order_buy_limit(
                    symbol=symbol,
                    quantity=quantity,
                    limitPrice=price,
                    timeInForce="gfd"
                )
            else:
                # Market order
                order = rh.orders.order_buy_market(
                    symbol=symbol,
                    quantity=quantity,
                    timeInForce="gfd"
                )

            return {
                "success": True,
                "order_id": order.get("id"),
                "state": order.get("state"),
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
            if price:
                order = rh.orders.order_sell_limit(
                    symbol=symbol,
                    quantity=quantity,
                    limitPrice=price,
                    timeInForce="gfd"
                )
            else:
                order = rh.orders.order_sell_market(
                    symbol=symbol,
                    quantity=quantity,
                    timeInForce="gfd"
                )

            return {
                "success": True,
                "order_id": order.get("id"),
                "state": order.get("state"),
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
            order = rh.orders.order_sell_stop_loss(
                symbol=symbol,
                quantity=quantity,
                stopPrice=stop_price,
                timeInForce="gtc"
            )
            return {
                "success": True,
                "order_id": order.get("id"),
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

    def cancel_order(self, order_id: str) -> dict:
        """Cancel a pending order"""
        if not self.is_connected:
            return {"error": "Not connected"}

        try:
            result = rh.orders.cancel_stock_order(order_id)
            return {"success": True, "cancelled": order_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
