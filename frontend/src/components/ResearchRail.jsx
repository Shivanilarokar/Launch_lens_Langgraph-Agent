function DemandSignal({ s }) {
  if (s.error) return <div className="signal"><div className="sig-l demand">⚠ {s.engine}</div><div className="sig-kv">{s.error}</div></div>
  if (s.engine === 'google_trends')
    return (
      <div className="signal">
        <div className="sig-l demand">📈 Google Trends</div>
        <div className="sig-kv">interest <b>{s.trend_direction}</b> {s.change_pct != null ? `(${s.change_pct}%)` : ''}</div>
        <div className="sig-chips">{(s.related_rising || []).slice(0, 4).map((q) => <span className="chip" key={q}>↑ {q}</span>)}</div>
      </div>
    )
  if (s.engine === 'google_shopping') {
    const b = s.price_band || {}
    return <div className="signal"><div className="sig-l demand">🛍️ Google Shopping</div><div className="sig-kv">band {b.min}–{b.max} · {s.count} listings</div></div>
  }
  if (s.engine === 'google_news')
    return <div className="signal"><div className="sig-l demand">📰 Google News</div>{(s.headlines || []).slice(0, 3).map((h, i) => <div className="sig-kv" key={i}>• {h.title}</div>)}</div>
  return <div className="signal"><div className="sig-l demand">{s.engine}</div></div>
}

function SupplySignal({ s }) {
  if (s.error) return <div className="signal"><div className="sig-l supply">⚠ {s.source}</div><div className="sig-kv">{s.error}</div></div>
  if (s.source === 'amazon_search')
    return (
      <div className="signal">
        <div className="sig-l supply">📦 Amazon · {(s.products || []).length} sellers</div>
        {(s.products || []).slice(0, 4).map((p) => (
          <div className="sig-kv" key={p.asin}>• {p.title?.slice(0, 40)} · {p.currency || ''}{p.price} ★{p.rating}</div>
        ))}
      </div>
    )
  return <div className="signal"><div className="sig-l supply">📦 {s.source}</div></div>
}

export default function ResearchRail({ activity, demand, supply, busy }) {
  return (
    <aside className="rail">
      <div className="rail-head">Live research {busy && <span className="rail-dot" />}</div>

      {activity.length > 0 && (
        <div className="rail-activity">
          {activity.map((a, i) => <div className="ract" key={i}><span className="ract-dot" />{a}</div>)}
        </div>
      )}

      <h4>Demand · SerpApi</h4>
      {demand.length ? demand.map((s, i) => <DemandSignal s={s} key={i} />) : <div className="rail-empty">No demand signals yet</div>}

      <h4>Supply · Oxylabs</h4>
      {supply.length ? supply.map((s, i) => <SupplySignal s={s} key={i} />) : <div className="rail-empty">No supply signals yet</div>}
    </aside>
  )
}
