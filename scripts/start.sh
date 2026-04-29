#!/bin/bash
# MOR Trading System - Startup Script

echo "=========================================="
echo "  MOR TRADING SYSTEM - EDGE EXECUTION"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Start Backend
echo -e "${YELLOW}Starting Edge API Server...${NC}"
cd backend
pip install -r requirements.txt > /dev/null 2>&1
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Start Frontend
echo -e "${YELLOW}Starting Dashboard...${NC}"
cd frontend
npm install > /dev/null 2>&1
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}=========================================="
echo "  SYSTEM ONLINE"
echo "=========================================="
echo ""
echo "  Dashboard:  http://localhost:3000"
echo "  API:        http://localhost:8000"
echo "  Webhook:    http://localhost:8000/webhook/tradingview"
echo ""
echo "  Press Ctrl+C to stop"
echo -e "==========================================${NC}"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
