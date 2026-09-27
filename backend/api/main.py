"""
MOR Trading System - Edge Execution API
Semi-automated trading: You call the play, Edge executes with TP/SL
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncio
import json
import os

from brokers.robinhood import RobinhoodBroker
from brokers.moomoo import MoomooBroker
from alerts.audio import AudioAlerts

app = FastAPI(title="MOR Trading System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for pending trades and positions
pending_trades: List[dict] = []
active_positions: List[dict] = []
connected_clients: List[WebSocket] = []

# Initialize brokers (lazy loaded with credentials)
robinhood = RobinhoodBroker()
moomoo = MoomooBroker()
audio = AudioAlerts()


class TradeSignal(BaseModel):
    symbol: str
    action: str  # BUY or SELL
    price: float
    quantity: int
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    broker: str = "robinhood"  # robinhood or moomoo
    source: str = "manual"  # manual, pinescript, webhook


class TradeConfirmation(BaseModel):
    trade_id: str
    approved: bool


class BrokerCredentials(BaseModel):
    broker: str
    username: str
    password: str
    mfa_code: Optional[str] = None


@app.get("/")
async def root():
    return {"status": "MOR Trading System Online", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "robinhood_connected": robinhood.is_connected,
        "moomoo_connected": moomoo.is_connected,
        "pending_trades": len(pending_trades),
        "active_positions": len(active_positions)
    }


@app.post("/auth/connect")
async def connect_broker(creds: BrokerCredentials):
    """Connect to a broker with credentials"""
    try:
        if creds.broker == "robinhood":
            success = robinhood.connect(creds.username, creds.password, creds.mfa_code)
        elif creds.broker == "moomoo":
            success = moomoo.connect(creds.username, creds.password)
        else:
            raise HTTPException(status_code=400, detail="Unknown broker")

        if success:
            await broadcast({"type": "broker_connected", "broker": creds.broker})
            return {"status": "connected", "broker": creds.broker}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/signal")
async def receive_signal(signal: TradeSignal):
    """Receive a trade signal - adds to pending for user confirmation"""
    trade = {
        "id": f"trade_{datetime.now().timestamp()}",
        "symbol": signal.symbol.upper(),
        "action": signal.action.upper(),
        "price": signal.price,
        "quantity": signal.quantity,
        "take_profit": signal.take_profit,
        "stop_loss": signal.stop_loss,
        "broker": signal.broker,
        "source": signal.source,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }

    pending_trades.append(trade)

    # Play audio alert
    audio.play_signal_alert(signal.action)

    # Broadcast to all connected dashboards
    await broadcast({"type": "new_signal", "trade": trade})

    return {"status": "pending", "trade_id": trade["id"], "message": "Awaiting confirmation"}


@app.post("/webhook/tradingview")
async def tradingview_webhook(payload: dict):
    """Webhook endpoint for TradingView/PineScript alerts"""
    try:
        signal = TradeSignal(
            symbol=payload.get("symbol", ""),
            action=payload.get("action", "BUY"),
            price=float(payload.get("price", 0)),
            quantity=int(payload.get("quantity", 1)),
            take_profit=float(payload.get("tp")) if payload.get("tp") else None,
            stop_loss=float(payload.get("sl")) if payload.get("sl") else None,
            broker=payload.get("broker", "robinhood"),
            source="pinescript"
        )
        return await receive_signal(signal)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/trade/confirm")
async def confirm_trade(confirmation: TradeConfirmation):
    """User confirms or rejects a pending trade"""
    trade = next((t for t in pending_trades if t["id"] == confirmation.trade_id), None)

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if confirmation.approved:
        # Execute the trade
        result = await execute_trade(trade)
        trade["status"] = "executed"
        trade["execution_result"] = result

        # Move to active positions
        pending_trades.remove(trade)
        active_positions.append(trade)

        audio.play_execution_alert()
        await broadcast({"type": "trade_executed", "trade": trade})

        return {"status": "executed", "result": result}
    else:
        trade["status"] = "rejected"
        pending_trades.remove(trade)
        await broadcast({"type": "trade_rejected", "trade": trade})
        return {"status": "rejected"}


async def execute_trade(trade: dict) -> dict:
    """Execute trade on the appropriate broker with TP/SL"""
    broker = robinhood if trade["broker"] == "robinhood" else moomoo

    if not broker.is_connected:
        return {"error": f"{trade['broker']} not connected"}

    try:
        # Place main order
        if trade["action"] == "BUY":
            order_result = broker.buy(
                symbol=trade["symbol"],
                quantity=trade["quantity"],
                price=trade["price"]
            )
        else:
            order_result = broker.sell(
                symbol=trade["symbol"],
                quantity=trade["quantity"],
                price=trade["price"]
            )

        # Set up TP/SL orders if specified
        if trade["take_profit"]:
            broker.set_take_profit(trade["symbol"], trade["quantity"], trade["take_profit"])

        if trade["stop_loss"]:
            broker.set_stop_loss(trade["symbol"], trade["quantity"], trade["stop_loss"])

        return {"success": True, "order": order_result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/trades/pending")
async def get_pending_trades():
    """Get all pending trades awaiting confirmation"""
    return {"trades": pending_trades}


@app.get("/positions")
async def get_positions():
    """Get all active positions"""
    positions = []

    if robinhood.is_connected:
        positions.extend(robinhood.get_positions())
    if moomoo.is_connected:
        positions.extend(moomoo.get_positions())

    return {"positions": positions, "tracked": active_positions}


@app.delete("/position/{symbol}")
async def close_position(symbol: str, broker: str = "robinhood"):
    """Close a position"""
    b = robinhood if broker == "robinhood" else moomoo
    result = b.close_position(symbol)
    await broadcast({"type": "position_closed", "symbol": symbol})
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time dashboard updates"""
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        # Send initial state
        await websocket.send_json({
            "type": "init",
            "pending_trades": pending_trades,
            "active_positions": active_positions
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


async def broadcast(message: dict):
    """Broadcast message to all connected clients"""
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
