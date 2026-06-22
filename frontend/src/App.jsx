import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getMarkets, streamChat } from "./api";

const newThread = () => "web-" + Math.random().toString(36).slice(2, 9);

function verdictBadge(text) {
  const m = text.match(/VERDICT:\s*(GO|NO-GO|NICHE)/i);
  if (!m) return null;
  const v = m[1].toUpperCase();
  const cls = v === "NO-GO" ? "verdict-NOGO" : v === "GO" ? "verdict-GO" : "verdict-NICHE";
  return <span className={`verdict-badge ${cls}`}>{v}</span>;
}

function DemandSignal({ s }) {
  if (s.error) return <div className="signal demand"><div className="label">{s.engine}</div><div className="kv">⚠ {s.error}</div></div>;
  if (s.engine === "google_trends")
    return (
      <div className="signal demand">
        <div className="label">📈 Google Trends</div>
        <div className="kv">interest {s.trend_direction} ({s.change_pct}%)</div>
        <div>{(s.related_rising || []).map((q) => <span className="chip" key={q}>↑ {q}</span>)}</div>
      </div>
    );
  if (s.engine === "google_shopping") {
    const b = s.price_band || {};
    return <div className="signal demand"><div className="label">🛍️ Google Shopping</div><div className="kv">band {b.min}–{b.max} · {s.count} listings</div></div>;
  }
  if (s.engine === "google_news")
    return <div className="signal demand"><div className="label">📰 Google News</div><div className="kv">{(s.headlines || []).length} headlines</div>{(s.headlines || []).slice(0, 2).map((h, i) => <div className="kv" key={i}>• {h.title}</div>)}</div>;
  return <div className="signal demand"><div className="label">{s.engine}</div></div>;
}

function SupplySignal({ s }) {
  if (s.error) return <div className="signal supply"><div className="label">{s.source}</div><div className="kv">⚠ {s.error}</div></div>;
  if (s.source === "amazon_search")
    return (
      <div className="signal supply">
        <div className="label">📦 Amazon top sellers</div>
        {(s.products || []).slice(0, 4).map((p) => <div className="kv" key={p.asin}>• {p.title?.slice(0, 42)} — {p.currency || ""}{p.price} ★{p.rating}</div>)}
      </div>
    );
  return <div className="signal supply"><div className="label">📦 {s.source}</div></div>;
}

export default function App() {
  const [markets, setMarkets] = useState([]);
  const [domain, setDomain] = useState("in");
  const [threadId, setThreadId] = useState(newThread);
  const [turns, setTurns] = useState([]);
  const [demand, setDemand] = useState([]);
  const [supply, setSupply] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [activity, setActivity] = useState([]);
  const streamRef = useRef(null);

  useEffect(() => { getMarkets().then((d) => { setMarkets(d.marketplaces || []); setDomain(d.default || "in"); }).catch(() => {}); }, []);
  useEffect(() => { streamRef.current?.scrollTo(0, streamRef.current.scrollHeight); }, [turns, activity]);

  async function send() {
    const msg = input.trim();
    if (!msg || busy) return;
    setInput("");
    setBusy(true);
    setDemand([]); setSupply([]); setActivity([]);
    setTurns((t) => [...t, { role: "user", content: msg }, { role: "assistant", content: "" }]);

    try {
      await streamChat({ threadId, message: msg, domain }, (event, data) => {
        if (event === "research") {
          if (data.node === "router") setActivity((a) => [...a, `intent: ${data.route} → ${data.query || "(followup)"}`]);
          else if (data.side === "demand") setDemand((d) => [...d, data.signal]);
          else if (data.side === "supply") setSupply((s) => [...s, data.signal]);
        } else if (event === "tool") {
          setActivity((a) => [...a, `calling tool: ${data.calls.join(", ")}`]);
        } else if (event === "token") {
          setTurns((t) => { const c = [...t]; c[c.length - 1] = { ...c[c.length - 1], content: c[c.length - 1].content + data.text }; return c; });
        } else if (event === "error") {
          setTurns((t) => { const c = [...t]; c[c.length - 1] = { role: "assistant", content: "⚠ " + data.message }; return c; });
        }
      });
    } catch (e) {
      setTurns((t) => { const c = [...t]; c[c.length - 1] = { role: "assistant", content: "⚠ " + e.message + " — is the backend running on :8010?" }; return c; });
    } finally {
      setBusy(false);
      setActivity([]);
    }
  }

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">LaunchLens <small>🔭 demand × supply → verdict</small></div>
        <div className="spacer" />
        <select value={domain} onChange={(e) => setDomain(e.target.value)}>
          {markets.map((m) => <option key={m.code} value={m.code}>{m.label}</option>)}
        </select>
        <button onClick={() => { setThreadId(newThread()); setTurns([]); setDemand([]); setSupply([]); }}>New chat</button>
      </div>

      <div className="main">
        <div className="chat">
          <div className="stream" ref={streamRef}>
            {turns.length === 0 && <div className="empty">Ask: “Should I launch a stainless-steel insulated water bottle in India under ₹1,500?”</div>}
            {turns.map((t, i) =>
              t.role === "user" ? (
                <div className="bubble user" key={i}>{t.content}</div>
              ) : (
                <div className="bubble assistant" key={i}>
                  {verdictBadge(t.content)}
                  {t.content ? <ReactMarkdown>{t.content}</ReactMarkdown> : <span className="empty">…</span>}
                </div>
              )
            )}
            {busy && activity.length > 0 && (
              <div className="activity">
                {activity.map((a, i) => <div className="row" key={i}><span className="dot" />{a}</div>)}
              </div>
            )}
          </div>
          <div className="composer">
            <input
              value={input}
              placeholder="Describe a product idea and market…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              disabled={busy}
            />
            <button onClick={send} disabled={busy || !input.trim()}>{busy ? "…" : "Ask"}</button>
          </div>
        </div>

        <div className="rail">
          <h3>Demand · SerpApi</h3>
          {demand.length ? demand.map((s, i) => <DemandSignal s={s} key={i} />) : <div className="empty">no demand signals yet</div>}
          <h3>Supply · Oxylabs</h3>
          {supply.length ? supply.map((s, i) => <SupplySignal s={s} key={i} />) : <div className="empty">no supply signals yet</div>}
        </div>
      </div>
    </div>
  );
}
