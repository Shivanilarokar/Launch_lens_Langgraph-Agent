export default function Sidebar({ conversations, activeId, onSelect, onNew, memoryFacts, profile, onPickMemory }) {
  const founder = [profile?.name, profile?.location].filter(Boolean).join(' · ')
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">🔭</span>
        <span className="brand-name">LaunchLens</span>
      </div>

      <button className="newchat" onClick={onNew}>
        <span className="nc-plus">＋</span> New chat
      </button>

      <div className="convo-list">
        <div className="side-label">Chats</div>
        {conversations.length === 0 && <div className="side-empty">No chats yet</div>}
        {conversations.map((c) => (
          <button
            key={c.id}
            className={`convo ${c.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(c.id)}
            title={c.title}
          >
            <span className="convo-ic">💬</span>
            <span className="convo-title">{c.title}</span>
          </button>
        ))}
      </div>

      <div className="memory-pane">
        <div className="side-label">
          Long-term memory
          <span className="mem-count">{memoryFacts.length}</span>
        </div>
        <div className="mem-hint">Remembered across every chat</div>
        {founder && (
          <div className="founder"><span className="founder-ic">👤</span> {founder}</div>
        )}
        {memoryFacts.length === 0 && <div className="side-empty">Nothing remembered yet</div>}
        {memoryFacts.map((f, i) => (
          <button key={i} className="memfact" onClick={() => onPickMemory(f)} title={f.summary || f.product}>
            <span className={`mem-verdict ${(f.verdict || '').toLowerCase().replace('-', '')}`}>{f.verdict || '•'}</span>
            <span className="memfact-name">{f.product}</span>
            <span className="memfact-mkt">{f.market}</span>
          </button>
        ))}
      </div>
    </aside>
  )
}
