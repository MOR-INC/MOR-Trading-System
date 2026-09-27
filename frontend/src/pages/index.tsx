import { useState, useEffect, useCallback, useRef } from 'react'
import { TrendingUp, TrendingDown, Bell, DollarSign, Activity, Volume2, VolumeX, Check, X, Zap } from 'lucide-react'

interface Trade {
  id: string
  symbol: string
  action: 'BUY' | 'SELL'
  price: number
  quantity: number
  take_profit?: number
  stop_loss?: number
  broker: string
  source: string
  status: string
  created_at: string
}

interface Position {
  symbol: string
  quantity: number
  avg_cost: number
  current_price: number
  market_value: number
  unrealized_pl: number
  unrealized_pl_pct: number
  broker: string
}

export default function Dashboard() {
  const [pendingTrades, setPendingTrades] = useState<Trade[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [connected, setConnected] = useState(false)
  const [audioEnabled, setAudioEnabled] = useState(true)
  const [brokerStatus, setBrokerStatus] = useState({ robinhood: false, moomoo: false })
  const wsRef = useRef<WebSocket | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const playAlert = useCallback((type: 'signal' | 'execute' | 'profit' | 'loss') => {
    if (!audioEnabled) return

    const sounds: Record<string, string> = {
      signal: '/sounds/signal.mp3',
      execute: '/sounds/execute.mp3',
      profit: '/sounds/profit.mp3',
      loss: '/sounds/loss.mp3'
    }

    if (audioRef.current) {
      audioRef.current.src = sounds[type]
      audioRef.current.play().catch(() => {})
    }
  }, [audioEnabled])

  useEffect(() => {
    audioRef.current = new Audio()
    audioRef.current.volume = 0.7

    const ws = new WebSocket('ws://localhost:8000/ws')
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      console.log('Connected to Edge')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'init':
          setPendingTrades(data.pending_trades || [])
          setPositions(data.active_positions || [])
          break
        case 'new_signal':
          setPendingTrades(prev => [...prev, data.trade])
          playAlert('signal')
          break
        case 'trade_executed':
          setPendingTrades(prev => prev.filter(t => t.id !== data.trade.id))
          setPositions(prev => [...prev, data.trade])
          playAlert('execute')
          break
        case 'trade_rejected':
          setPendingTrades(prev => prev.filter(t => t.id !== data.trade.id))
          break
        case 'broker_connected':
          setBrokerStatus(prev => ({ ...prev, [data.broker]: true }))
          break
      }
    }

    ws.onclose = () => {
      setConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [playAlert])

  const confirmTrade = async (tradeId: string, approved: boolean) => {
    try {
      await fetch('http://localhost:8000/trade/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trade_id: tradeId, approved })
      })
    } catch (error) {
      console.error('Failed to confirm trade:', error)
    }
  }

  const totalPL = positions.reduce((sum, p) => sum + p.unrealized_pl, 0)
  const totalValue = positions.reduce((sum, p) => sum + p.market_value, 0)

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-gradient-to-r from-yellow-400 to-yellow-600 flex items-center justify-center">
            <Zap className="w-7 h-7 text-black" />
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-yellow-400 to-yellow-200 bg-clip-text text-transparent">
              MOR TRADING SYSTEM
            </h1>
            <p className="text-gray-400">Edge Execution Dashboard</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setAudioEnabled(!audioEnabled)}
            className={`p-3 rounded-lg ${audioEnabled ? 'bg-mor-gold/20 text-mor-gold' : 'bg-gray-800 text-gray-500'}`}
          >
            {audioEnabled ? <Volume2 /> : <VolumeX />}
          </button>

          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
            {connected ? 'LIVE' : 'OFFLINE'}
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <DollarSign className="w-5 h-5" />
            <span>Portfolio Value</span>
          </div>
          <div className="text-2xl font-bold">${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <Activity className="w-5 h-5" />
            <span>Unrealized P/L</span>
          </div>
          <div className={`text-2xl font-bold ${totalPL >= 0 ? 'profit' : 'loss'}`}>
            {totalPL >= 0 ? '+' : ''}{totalPL.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
          </div>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <Bell className="w-5 h-5" />
            <span>Pending Signals</span>
          </div>
          <div className="text-2xl font-bold text-mor-gold">{pendingTrades.length}</div>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <Zap className="w-5 h-5" />
            <span>Brokers</span>
          </div>
          <div className="flex gap-2 mt-1">
            <span className={`px-2 py-1 rounded text-xs ${brokerStatus.robinhood ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
              RH
            </span>
            <span className={`px-2 py-1 rounded text-xs ${brokerStatus.moomoo ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
              MOO
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Pending Trades */}
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Bell className="text-mor-gold" />
            Pending Signals
          </h2>

          {pendingTrades.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No pending signals - you'll hear an alert when one arrives
            </div>
          ) : (
            <div className="space-y-4">
              {pendingTrades.map((trade) => (
                <div
                  key={trade.id}
                  className="trade-pending p-4 rounded-lg bg-mor-dark border border-mor-gold/30"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${trade.action === 'BUY' ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                        {trade.action === 'BUY' ? (
                          <TrendingUp className="w-5 h-5 text-green-400" />
                        ) : (
                          <TrendingDown className="w-5 h-5 text-red-400" />
                        )}
                      </div>
                      <div>
                        <div className="font-bold text-lg">{trade.symbol}</div>
                        <div className="text-sm text-gray-400">{trade.broker.toUpperCase()}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">{trade.quantity} shares</div>
                      <div className="text-gray-400">@ ${trade.price.toFixed(2)}</div>
                    </div>
                  </div>

                  <div className="flex gap-4 text-sm mb-4">
                    {trade.take_profit && (
                      <div className="text-green-400">TP: ${trade.take_profit.toFixed(2)}</div>
                    )}
                    {trade.stop_loss && (
                      <div className="text-red-400">SL: ${trade.stop_loss.toFixed(2)}</div>
                    )}
                    <div className="text-gray-500">via {trade.source}</div>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => confirmTrade(trade.id, true)}
                      className="btn-confirm flex-1 flex items-center justify-center gap-2"
                    >
                      <Check className="w-5 h-5" /> EXECUTE
                    </button>
                    <button
                      onClick={() => confirmTrade(trade.id, false)}
                      className="btn-reject flex-1 flex items-center justify-center gap-2"
                    >
                      <X className="w-5 h-5" /> REJECT
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Positions */}
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Activity className="text-mor-green" />
            Active Positions
          </h2>

          {positions.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No active positions
            </div>
          ) : (
            <div className="space-y-3">
              {positions.map((pos, idx) => (
                <div key={idx} className="p-4 rounded-lg bg-mor-dark border border-gray-800">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold">{pos.symbol}</div>
                      <div className="text-sm text-gray-400">
                        {pos.quantity} @ ${pos.avg_cost.toFixed(2)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={pos.unrealized_pl >= 0 ? 'profit font-bold' : 'loss font-bold'}>
                        {pos.unrealized_pl >= 0 ? '+' : ''}${pos.unrealized_pl.toFixed(2)}
                      </div>
                      <div className={`text-sm ${pos.unrealized_pl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pos.unrealized_pl_pct >= 0 ? '+' : ''}{pos.unrealized_pl_pct.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick Trade Panel */}
      <div className="glass-card p-6 mt-6">
        <h2 className="text-xl font-bold mb-4">Quick Manual Signal</h2>
        <QuickTradeForm />
      </div>
    </div>
  )
}

function QuickTradeForm() {
  const [symbol, setSymbol] = useState('')
  const [action, setAction] = useState<'BUY' | 'SELL'>('BUY')
  const [quantity, setQuantity] = useState('')
  const [price, setPrice] = useState('')
  const [tp, setTp] = useState('')
  const [sl, setSl] = useState('')
  const [broker, setBroker] = useState('robinhood')

  const submitSignal = async () => {
    if (!symbol || !quantity || !price) return

    try {
      await fetch('http://localhost:8000/signal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          action,
          price: parseFloat(price),
          quantity: parseInt(quantity),
          take_profit: tp ? parseFloat(tp) : null,
          stop_loss: sl ? parseFloat(sl) : null,
          broker,
          source: 'manual'
        })
      })

      setSymbol('')
      setQuantity('')
      setPrice('')
      setTp('')
      setSl('')
    } catch (error) {
      console.error('Failed to submit signal:', error)
    }
  }

  return (
    <div className="grid grid-cols-7 gap-4">
      <input
        type="text"
        placeholder="Symbol"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value.toUpperCase())}
        className="bg-mor-dark border border-gray-700 rounded-lg px-4 py-2 focus:border-mor-gold focus:outline-none"
      />

      <select
        value={action}
        onChange={(e) => setAction(e.target.value as 'BUY' | 'SELL')}
        className="bg-mor-dark border border-gray-700 rounded-lg px-4 py-2 focus:border-mor-gold focus:outline-none"
      >
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>

      <input
        type="number"
        placeholder="Qty"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className="bg-mor-dark border border-gray-700 rounded-lg px-4 py-2 focus:border-mor-gold focus:outline-none"
      />

      <input
        type="number"
        placeholder="Price"
        value={price}
        onChange={(e) => setPrice(e.target.value)}
        className="bg-mor-dark border border-gray-700 rounded-lg px-4 py-2 focus:border-mor-gold focus:outline-none"
      />

      <input
        type="number"
        placeholder="TP"
        value={tp}
        onChange={(e) => setTp(e.target.value)}
        className="bg-mor-dark border border-gray-700 rounded-lg px-4 py-2 focus:border-mor-gold focus:outline-none"
      />

      <input
        type="number"
        placeholder="SL"
        value={sl}
        onChange={(e) => setSl(e.target.value)}
        className="bg-mor-dark border border-gray-700 rounded-lg px-4 py-2 focus:border-mor-gold focus:outline-none"
      />

      <button onClick={submitSignal} className="btn-confirm">
        SEND SIGNAL
      </button>
    </div>
  )
}
