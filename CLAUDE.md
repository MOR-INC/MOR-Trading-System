# MOR Trading System

Semi-automated trading platform: You call the play, Edge executes with TP/SL.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DASHBOARD (Next.js)                  │
│  - Real-time trade signals with audio alerts            │
│  - One-click execution approval                         │
│  - Position monitoring with P/L                         │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket
┌──────────────────────────▼──────────────────────────────┐
│                   EDGE API (FastAPI)                    │
│  - Signal processing from TradingView/PineScript        │
│  - Trade execution with TP/SL management                │
│  - Multi-broker support                                 │
├────────────────────┬────────────────────────────────────┤
│  Robinhood Broker  │  Moomoo Broker                     │
│  (robin_stocks)    │  (futu-api)                        │
└────────────────────┴────────────────────────────────────┘
```

## Quick Start

```bash
# Copy environment config
cp config/.env.example config/.env

# Edit with your broker credentials
nano config/.env

# Start everything
chmod +x scripts/start.sh
./scripts/start.sh
```

## Workflow

1. **Signal Arrives** (via TradingView webhook, PineScript, or manual entry)
2. **Audio Alert Plays** - you hear the signal
3. **Review on Dashboard** - see symbol, price, TP/SL
4. **You Approve or Reject** - one click
5. **Edge Executes** - places order with TP/SL on your broker

## PineScript Integration

See `scripts/pinescript_alert_template.pine` for TradingView webhook setup.

Webhook URL: `http://YOUR_SERVER:8000/webhook/tradingview`

## API Endpoints

- `POST /signal` - Submit manual trade signal
- `POST /webhook/tradingview` - TradingView webhook
- `POST /trade/confirm` - Approve/reject pending trade
- `GET /trades/pending` - List pending signals
- `GET /positions` - Get active positions
- `POST /auth/connect` - Connect broker

## Files

- `backend/api/main.py` - FastAPI server
- `backend/brokers/robinhood.py` - Robinhood integration
- `backend/brokers/moomoo.py` - Moomoo integration
- `frontend/src/pages/index.tsx` - Dashboard UI
