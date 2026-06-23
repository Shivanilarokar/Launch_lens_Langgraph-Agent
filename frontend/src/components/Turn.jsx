import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ProductCard from './ProductCard.jsx'
import Analytics, { computePicks } from './Analytics.jsx'
import DemandPulse from './DemandPulse.jsx'

// Robust: matches "VERDICT: GO", "**Verdict:** NO-GO", "Niche", "NOGO", etc.
function parseVerdict(text = '') {
  const m = text.match(/VERDICT[:\s]*\*{0,2}\s*(GO|NO-?GO|NICHE)\b/i)
  if (!m) return null
  return m[1].toUpperCase().replace('NOGO', 'NO-GO')
}

function VerdictCard({ verdict }) {
  const cls = verdict === 'NO-GO' ? 'nogo' : verdict === 'GO' ? 'go' : 'niche'
  const icon = verdict === 'GO' ? '✅' : verdict === 'NO-GO' ? '⛔' : '🎯'
  const label =
    verdict === 'GO' ? 'Worth launching'
      : verdict === 'NO-GO' ? 'Not worth it'
        : 'Niche opportunity'
  return (
    <div className={`verdict-card ${cls}`}>
      <span className="vc-icon">{icon}</span>
      <span className="vc-word">{verdict}</span>
      <span className="vc-label">{label}</span>
    </div>
  )
}

export default function Turn({ turn }) {
  if (turn.role === 'user') {
    return (
      <div className="turn user">
        <div className="bubble">{turn.content}</div>
      </div>
    )
  }

  const verdict = parseVerdict(turn.content)
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

      {verdict && <VerdictCard verdict={verdict} />}

      <div className={`bubble ${turn.error ? 'error' : ''}`}>
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
