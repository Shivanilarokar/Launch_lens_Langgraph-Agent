import { useState } from 'react'

export default function Sidebar({ threads, activeThread, onSelect, onCreate, live }) {
  const [name, setName] = useState('')

  const nextId = () => {
    let n = threads.length + 1
    let id = `ll-${String(n).padStart(3, '0')}`
    while (threads.includes(id)) {
      n += 1
      id = `ll-${String(n).padStart(3, '0')}`
    }
    return id
  }

  const createCustom = (e) => {
    e.preventDefault()
    const id = name.trim().replace(/\s+/g, '-').toLowerCase()
    if (!id) return
    onCreate(id)
    setName('')
  }

  return (
    <aside className="sidebar">
      <div className="wordmark">
        <h1>Launch<span className="tick">Lens</span> <span className="logo-dot">🔭</span></h1>
        <div className="sub">demand × supply → verdict</div>
      </div>

      <button className="new-chat-btn" onClick={() => onCreate(nextId())}>
        <span className="plus">+</span> New analysis
      </button>

      <div className="threads">
        <div className="threads-label">Threads</div>
        {threads.map((t) => (
          <button
            key={t}
            className={`thread-item ${t === activeThread ? 'active' : ''}`}
            onClick={() => onSelect(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <form className="new-thread" onSubmit={createCustom}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name a new thread" />
        <button type="submit" title="create named thread">→</button>
      </form>

      <div className="side-foot">
        <span className={`dot ${live ? 'on' : ''}`} /> {live ? 'Live data' : 'Mock'}
      </div>
    </aside>
  )
}
