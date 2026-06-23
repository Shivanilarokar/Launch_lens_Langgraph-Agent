import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Only the four canonical verdict sections, each requiring a colon. (We deliberately
// do NOT match a bare "Price:" line so product/brand price lists are never mistaken
// for verdict rows.)
const SECTION_RE = /^[\s>*•\-]*\*{0,2}\s*(Demand|Price band|Differentiation|Positioning)\*{0,2}\s*:\s*(.+)$/i
const VERDICT_RE = /VERDICT[:\s]*\*{0,2}\s*(GO|NO-?GO|NICHE)\b/i

export function isVerdict(content = '') {
  return VERDICT_RE.test(content)
}

function parse(content = '') {
  const vm = content.match(VERDICT_RE)
  const verdict = vm ? vm[1].toUpperCase().replace('NOGO', 'NO-GO') : null
  const rows = []
  const seen = new Set()
  for (const line of content.split('\n')) {
    const m = line.match(SECTION_RE)
    if (m) {
      const label = m[1]
      if (!seen.has(label.toLowerCase())) {
        seen.add(label.toLowerCase())
        rows.push({ label, text: m[2].trim() })
      }
    }
  }
  const om = content.match(/Overall[,:]?\s*([^\n]+)/i)
  return { verdict, rows, overall: om ? om[1].trim() : '' }
}

const META = {
  GO: { cls: 'go', icon: '✅', tag: 'Worth launching' },
  'NO-GO': { cls: 'nogo', icon: '⛔', tag: 'Not worth launching' },
  NICHE: { cls: 'niche', icon: '🎯', tag: 'Niche opportunity' },
}

export default function Verdict({ content }) {
  if (!content) return null
  // Not a launch verdict → just render the answer cleanly (no card).
  if (!isVerdict(content)) {
    return <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown></div>
  }

  const { verdict, rows, overall } = parse(content)
  const meta = META[verdict] || { cls: 'neutral', icon: '🔭', tag: 'Analysis' }

  return (
    <div className={`verdict ${meta.cls}`}>
      <div className="verdict-head">
        <span className="v-icon">{meta.icon}</span>
        <span className="v-word">{verdict}</span>
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
