import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const SECTION_RE = /^[\s>*•\-]*\*{0,2}\s*(Demand|Price band|Price|Differentiation|Positioning)\*{0,2}\s*[:\-]\s*(.+)$/i

function parse(content = '') {
  const vm = content.match(/VERDICT[:\s]*\*{0,2}\s*(GO|NO-?GO|NICHE)\b/i)
  const verdict = vm ? vm[1].toUpperCase().replace('NOGO', 'NO-GO') : null
  const rows = []
  for (const line of content.split('\n')) {
    const m = line.match(SECTION_RE)
    if (m) {
      const label = /^price$/i.test(m[1]) ? 'Price band' : m[1]
      rows.push({ label, text: m[2].trim() })
    }
  }
  const om = content.match(/Overall[,:]?\s*([^\n]+)/i)
  return { verdict, rows, overall: om ? om[1].trim() : '' }
}

export function isVerdict(content = '') {
  const { verdict, rows } = parse(content)
  return !!verdict || rows.length > 0
}

const META = {
  GO: { cls: 'go', icon: '✅', tag: 'Worth launching' },
  'NO-GO': { cls: 'nogo', icon: '⛔', tag: 'Not worth launching' },
  NICHE: { cls: 'niche', icon: '🎯', tag: 'Niche opportunity' },
}

export default function Verdict({ content }) {
  if (!content) return null
  const { verdict, rows, overall } = parse(content)
  if (!verdict && rows.length === 0) {
    return <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown></div>
  }
  const meta = META[verdict] || { cls: 'neutral', icon: '🔭', tag: 'Analysis' }

  return (
    <div className={`verdict ${meta.cls}`}>
      <div className="verdict-head">
        <span className="v-icon">{meta.icon}</span>
        <span className="v-word">{verdict || 'ANALYSIS'}</span>
        <span className="v-tag">{meta.tag}</span>
      </div>
      {rows.length > 0 && (
        <div className="verdict-rows">
          {rows.map((r, i) => (
            <div className="vrow" key={i}>
              <span className="vrow-l">{r.label}</span>
              <span className="vrow-t">{r.text}</span>
            </div>
          ))}
        </div>
      )}
      {overall && <div className="verdict-overall">{overall}</div>}
    </div>
  )
}
