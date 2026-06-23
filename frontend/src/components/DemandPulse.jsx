function trendClass(dir) {
  if (dir === 'rising') return 'up'
  if (dir === 'declining') return 'down'
  return 'flat'
}

export default function DemandPulse({ signals }) {
  const trends = signals.find((s) => s.engine === 'google_trends')
  const shopping = signals.find((s) => s.engine === 'google_shopping')
  const news = signals.find((s) => s.engine === 'google_news')
  if (!trends && !shopping && !news) return null

  return (
    <div className="demand">
      <div className="snap-head">
        <span className="snap-title">Demand pulse</span>
        <span className="snap-n">Google · SerpApi</span>
      </div>

      <div className="demand-grid">
        {trends && !trends.error && (
          <div className="dcell">
            <div className="dcell-l">Search interest</div>
            <div className={`dcell-v ${trendClass(trends.trend_direction)}`}>
              {trends.trend_direction === 'rising' ? '▲' : trends.trend_direction === 'declining' ? '▼' : '▬'}{' '}
              {trends.trend_direction} {trends.change_pct != null ? `(${trends.change_pct}%)` : ''}
            </div>
            {(trends.related_rising || []).length > 0 && (
              <div className="chips">
                {trends.related_rising.slice(0, 4).map((q) => <span className="chip" key={q}>↑ {q}</span>)}
              </div>
            )}
          </div>
        )}

        {shopping && !shopping.error && shopping.price_band && (
          <div className="dcell">
            <div className="dcell-l">Cross-retailer price band</div>
            <div className="dcell-v">
              {shopping.price_band.min}–{shopping.price_band.max}
              <span className="dcell-sub"> · median {shopping.price_band.median} · {shopping.count} listings</span>
            </div>
          </div>
        )}

        {news && !news.error && (news.headlines || []).length > 0 && (
          <div className="dcell wide">
            <div className="dcell-l">Recent news</div>
            <ul className="news-list">
              {news.headlines.slice(0, 3).map((h, i) => (
                <li key={i}><span className="news-src">{h.source || '—'}</span> {h.title}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
