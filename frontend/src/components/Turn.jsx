import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ProductCard from './ProductCard.jsx'
import Analytics, { computePicks } from './Analytics.jsx'
import DemandPulse from './DemandPulse.jsx'

function VerdictBadge({ text }) {
  const m = text.match(/VERDICT:\s*(GO|NO-GO|NICHE)/i)
  if (!m) return null
  const v = m[1].toUpperCase()
  const cls = v === 'NO-GO' ? 'nogo' : v === 'GO' ? 'go' : 'niche'
  return <span className={`verdict-badge ${cls}`}>{v}</span>
}

export default function Turn({ turn }) {
  if (turn.role === 'user') {
    return (
      <div className="turn user">
        <div className="bubble">{turn.content}</div>
      </div>
    )
  }

  const picks = turn.products?.length ? computePicks(turn.products) : []
  const pickFor = (asin) => picks.find((x) => x.p.asin === asin)?.tag

  return (
    <div className="turn agent">
      <div className="who">LaunchLens {turn.route && <span className="route-chip">{turn.route}</span>}</div>

      {turn.toolCalls?.length > 0 && (
        <div className="trace">
          {turn.toolCalls.map((c, i) => (
            <div className="trace-line" key={i}>
              <span className="fn">{c.name}</span>
              {c.args && <span className="args">({JSON.stringify(c.args)})</span>}
            </div>
          ))}
        </div>
      )}

      {turn.demand?.length > 0 && <DemandPulse signals={turn.demand} />}

      <div className={`bubble ${turn.error ? 'error' : ''}`}>
        {turn.content ? <VerdictBadge text={turn.content} /> : null}
        {turn.content
          ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.content}</ReactMarkdown>
          : <span className="thinking"><span className="pulse" /> Researching live market data…</span>}
      </div>

      {turn.products?.length >= 2 && <Analytics products={turn.products} />}

      {turn.products?.length > 0 && (
        <div className="cards">
          {turn.products.map((p, i) => (
            <ProductCard key={p.asin || i} product={p} pickTag={pickFor(p.asin)} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
