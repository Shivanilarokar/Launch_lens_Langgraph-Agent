import { useCallback, useEffect, useRef, useState } from 'react'
import { api, streamChat } from './api'
import Sidebar from './components/Sidebar.jsx'
import Turn from './components/Turn.jsx'
import ContextPanel from './components/ContextPanel.jsx'
import Ticker from './components/Ticker.jsx'
import MarketBoard from './components/MarketBoard.jsx'

const HINTS = [
  'Should I launch a stainless-steel insulated water bottle in India under ₹1,500?',
  'What about the US market?',
  'Pull the reviews of the top seller and name the main complaint',
  'Where would a ₹1,299 price sit vs competitors?',
]

export default function App() {
  const [threads, setThreads] = useState([])
  const [activeThread, setActiveThread] = useState('demo')
  const [turns, setTurns] = useState([])
  const [memState, setMemState] = useState(null)
  const [busy, setBusy] = useState(false)
  const [input, setInput] = useState('')
  const [live, setLive] = useState(true)
  const [lastMs, setLastMs] = useState(null)
  const [markets, setMarkets] = useState([])
  const [domain, setDomain] = useState('in')
  const feedRef = useRef(null)

  const refreshThreads = useCallback(async () => {
    try {
      const data = await api.threads()
      setThreads(data.threads.length ? data.threads : ['demo'])
    } catch {
      setThreads(['demo'])
    }
  }, [])

  const loadThread = useCallback(async (threadId) => {
    setActiveThread(threadId)
    try {
      const [hist, st] = await Promise.all([api.history(threadId), api.state(threadId)])
      setTurns(hist.messages.map((m) => ({ role: m.role === 'user' ? 'user' : 'agent', content: m.content })))
      setMemState(st)
    } catch {
      setTurns([])
      setMemState(null)
    }
  }, [])

  useEffect(() => {
    api.health().then((h) => setLive(!h.mock_mode)).catch(() => {})
    api.marketplaces().then((m) => {
      setMarkets(m.marketplaces)
      setDomain(m.default)
    }).catch(() => {})
    refreshThreads()
    loadThread('demo')
  }, [refreshThreads, loadThread])

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight })
  }, [turns, busy])

  const send = async (text) => {
    const message = (text || input).trim()
    if (!message || busy) return
    setInput('')
    setBusy(true)
    setTurns((t) => [
      ...t,
      { role: 'user', content: message },
      { role: 'agent', content: '', toolCalls: [], products: [], demand: [], supply: [], streaming: true },
    ])
    const t0 = performance.now()
    const patch = (fn) =>
      setTurns((t) => {
        const c = [...t]
        const last = { ...c[c.length - 1] }
        fn(last)
        c[c.length - 1] = last
        return c
      })

    try {
      await streamChat({ threadId: activeThread, message, domain }, (ev, data) => {
        if (ev === 'research') {
          if (data.node === 'router') patch((l) => { l.route = data.route })
          else if (data.side === 'demand') patch((l) => { l.demand = [...l.demand, data.signal] })
          else if (data.side === 'supply') patch((l) => {
            l.supply = [...l.supply, data.signal]
            if (data.signal?.products) l.products = [...l.products, ...data.signal.products]
          })
        } else if (ev === 'tool') {
          patch((l) => { l.toolCalls = [...l.toolCalls, ...data.calls.map((n) => ({ name: n }))] })
        } else if (ev === 'token') {
          patch((l) => { l.content += data.text })
        } else if (ev === 'final') {
          patch((l) => { l.streaming = false })
        } else if (ev === 'error') {
          patch((l) => { l.content = `error: ${data.message}`; l.error = true; l.streaming = false })
        }
      })
    } catch (err) {
      patch((l) => { l.content = `error: ${err.message} (is the backend running on :8010?)`; l.error = true; l.streaming = false })
    } finally {
      setBusy(false)
      setLastMs(Math.round(performance.now() - t0))
      try { setMemState(await api.state(activeThread)) } catch { /* ignore */ }
      refreshThreads()
    }
  }

  // every product seen in this thread feeds the ticker + market board
  const tickerItems = []
  const seen = new Set()
  for (const t of turns) {
    for (const p of t.products || []) {
      if (p.asin && p.price != null && !seen.has(p.asin)) {
        seen.add(p.asin)
        tickerItems.push(p)
      }
    }
  }

  return (
    <div className="layout">
      <Sidebar
        threads={threads}
        activeThread={activeThread}
        onSelect={loadThread}
        onCreate={(id) => {
          setThreads((t) => (t.includes(id) ? t : [...t, id]))
          loadThread(id)
        }}
        live={live}
      />

      <main className="chat-col">
        <div className="topbar">
          <div className="thread-id-block">
            <span className="thread-label">Thread</span>
            <span className="thread-name">{activeThread}</span>
          </div>
          <label className="market-select">
            <span className="market-label">Market</span>
            <select value={domain} onChange={(e) => setDomain(e.target.value)}>
              {markets.map((m) => (
                <option key={m.code} value={m.code}>amazon.{m.code} ({m.currency})</option>
              ))}
            </select>
          </label>
          <Ticker items={tickerItems} />
        </div>

        <div className="feed" ref={feedRef}>
          {turns.length === 0 && !busy ? (
            <div className="empty-state">
              <div className="masthead">
                <h2>Should you <em>launch it?</em></h2>
                <p className="mast-sub">
                  Describe a product idea. LaunchLens fuses live demand (Google) with supply
                  (Amazon) into a Go / No-Go / Niche verdict — and remembers the conversation.
                </p>
              </div>
              <div className="hints">
                {HINTS.map((h) => (
                  <button key={h} className="hint" onClick={() => send(h)}>{h}</button>
                ))}
              </div>
            </div>
          ) : (
            turns.map((turn, i) => <Turn key={i} turn={turn} />)
          )}
        </div>

        <div className="composer">
          <form onSubmit={(e) => { e.preventDefault(); send() }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
              }}
              placeholder="Describe a product idea and market…  (Enter to send, Shift+Enter = new line)"
              rows={2}
              disabled={busy}
              autoFocus
            />
            <button type="submit" disabled={busy || !input.trim()}>Ask</button>
          </form>
        </div>

        <div className="statusbar">
          <span className={`sb-mode ${live ? 'live' : 'mock'}`}>{live ? 'Live' : 'Mock'}</span>
          <span className="sb-item">Thread {activeThread}</span>
          <span className="sb-item">Messages {memState?.message_count ?? 0} of 12</span>
          <span className="sb-item">Checkpoints {memState?.checkpoints ?? 0}</span>
          <span className="sb-spacer" />
          {lastMs != null && <span className="sb-item">Last turn {(lastMs / 1000).toFixed(1)}s</span>}
          <span className="sb-item">{busy ? 'Researching…' : 'Idle'}</span>
        </div>
      </main>

      <aside className="boardcol">
        <MarketBoard products={tickerItems} />
        <ContextPanel state={memState} />
      </aside>
    </div>
  )
}
