import { useEffect, useRef, useState } from 'react'
import { api, streamChat } from './api'
import Sidebar from './components/Sidebar.jsx'
import ResearchRail from './components/ResearchRail.jsx'
import Verdict from './components/Verdict.jsx'
import ProductCard from './components/ProductCard.jsx'

const LS_KEY = 'launchlens.convos.v1'
const DEFAULT_TITLE = 'New chat'
const uid = () => 'c-' + Math.random().toString(36).slice(2, 10)
const loadConvos = () => { try { return JSON.parse(localStorage.getItem(LS_KEY)) || [] } catch { return [] } }
const saveConvos = (c) => localStorage.setItem(LS_KEY, JSON.stringify(c))

const HINTS = [
  'Should I launch a stainless-steel insulated water bottle in India under ₹1,500?',
  'Is a bamboo toothbrush worth launching in the US under $5?',
  'Compare a cork yoga mat against the competition in India',
]

export default function App() {
  const [conversations, setConversations] = useState(loadConvos)
  const [activeId, setActiveId] = useState(null)
  const [turns, setTurns] = useState([])
  const [demand, setDemand] = useState([])
  const [supply, setSupply] = useState([])
  const [activity, setActivity] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [markets, setMarkets] = useState([])
  const [domain, setDomain] = useState('in')
  const [memoryFacts, setMemoryFacts] = useState([])
  const streamRef = useRef(null)

  const refreshMemory = () => api.memory().then((d) => setMemoryFacts(d.facts || [])).catch(() => {})

  useEffect(() => {
    api.marketplaces().then((m) => { setMarkets(m.marketplaces || []); setDomain(m.default || 'in') }).catch(() => {})
    refreshMemory()
    setConversations((prev) => {
      if (prev.length) { setActiveId(prev[0].id); return prev }
      const c = [{ id: uid(), title: DEFAULT_TITLE, ts: Date.now() }]
      setActiveId(c[0].id); saveConvos(c); return c
    })
  }, [])

  useEffect(() => { streamRef.current?.scrollTo(0, streamRef.current.scrollHeight) }, [turns, activity, busy])

  const newChat = () => {
    const c = { id: uid(), title: DEFAULT_TITLE, ts: Date.now() }
    const next = [c, ...conversations]
    setConversations(next); saveConvos(next)
    setActiveId(c.id); setTurns([]); setDemand([]); setSupply([]); setActivity([])
  }

  const selectConvo = async (id) => {
    setActiveId(id); setTurns([]); setDemand([]); setSupply([]); setActivity([])
    try {
      const hist = await api.history(id)
      setTurns(hist.messages.map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.content })))
    } catch { setTurns([]) }
  }

  const renameIfNew = (id, msg) => {
    setConversations((prev) => {
      const next = prev.map((c) => (c.id === id && c.title === DEFAULT_TITLE ? { ...c, title: msg.slice(0, 42) } : c))
      saveConvos(next); return next
    })
  }

  async function send(text) {
    const msg = (text ?? input).trim()
    if (!msg || busy || !activeId) return
    setInput(''); setBusy(true)
    setDemand([]); setSupply([]); setActivity([])
    renameIfNew(activeId, msg)
    setTurns((t) => [...t, { role: 'user', content: msg }, { role: 'assistant', content: '', products: [] }])

    const patch = (fn) => setTurns((t) => { const c = [...t]; const last = { ...c[c.length - 1] }; fn(last); c[c.length - 1] = last; return c })

    try {
      await streamChat({ threadId: activeId, message: msg, domain }, (ev, data) => {
        if (ev === 'research') {
          if (data.node === 'router') setActivity((a) => [...a, `intent: ${data.route} → ${data.query || '(followup)'}`])
          else if (data.side === 'demand') setDemand((d) => [...d, data.signal])
          else if (data.side === 'supply') {
            setSupply((s) => [...s, data.signal])
            if (data.signal?.products) patch((l) => { l.products = [...(l.products || []), ...data.signal.products] })
          }
        } else if (ev === 'tool') setActivity((a) => [...a, `tool: ${data.calls.join(', ')}`])
        else if (ev === 'token') patch((l) => { l.content += data.text })
        else if (ev === 'error') patch((l) => { l.content = '⚠ ' + data.message; l.error = true })
      })
    } catch (e) {
      patch((l) => { l.content = '⚠ ' + e.message + ' — is the backend on :8010?'; l.error = true })
    } finally {
      setBusy(false); setActivity([]); refreshMemory()
    }
  }

  const activeTitle = conversations.find((c) => c.id === activeId)?.title || 'LaunchLens'

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConvo}
        onNew={newChat}
        memoryFacts={memoryFacts}
        onPickMemory={(f) => setInput(`What did we conclude about ${f.product}?`)}
      />

      <main className="chat">
        <header className="chat-head">
          <div className="ch-title">{activeTitle === DEFAULT_TITLE ? 'New chat' : activeTitle}</div>
          <label className="market">
            Market
            <select value={domain} onChange={(e) => setDomain(e.target.value)}>
              {markets.map((m) => <option key={m.code} value={m.code}>amazon.{m.code} · {m.currency}</option>)}
            </select>
          </label>
        </header>

        <div className="stream" ref={streamRef}>
          {turns.length === 0 && !busy && (
            <div className="welcome">
              <div className="w-logo">🔭</div>
              <h1>Should you launch it?</h1>
              <p>Describe a product idea. LaunchLens fuses live demand (Google) with supply (Amazon) into a detailed Go / No-Go / Niche verdict — and remembers it across every chat.</p>
              <div className="w-hints">
                {HINTS.map((h) => <button key={h} onClick={() => send(h)}>{h}</button>)}
              </div>
            </div>
          )}

          {turns.map((t, i) =>
            t.role === 'user' ? (
              <div className="msg user" key={i}><div className="ubub">{t.content}</div></div>
            ) : (
              <div className="msg assistant" key={i}>
                <div className="who"><span className="who-ic">🔭</span> LaunchLens</div>
                {t.content
                  ? <Verdict content={t.content} />
                  : <div className="typing"><span /><span /><span /></div>}
                {t.products?.length > 0 && (
                  <div className="pcards">
                    {t.products.map((p, j) => <ProductCard key={p.asin || j} product={p} />)}
                  </div>
                )}
              </div>
            )
          )}
        </div>

        <div className="composer">
          <div className="composer-inner">
            <textarea
              value={input}
              placeholder="Message LaunchLens…  (Enter to send)"
              rows={1}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              disabled={busy}
            />
            <button onClick={() => send()} disabled={busy || !input.trim()} aria-label="Send">
              {busy ? '…' : '↑'}
            </button>
          </div>
          <div className="composer-foot">LaunchLens fuses SerpApi + Oxylabs · live data</div>
        </div>
      </main>

      <ResearchRail activity={activity} demand={demand} supply={supply} busy={busy} />
    </div>
  )
}
