const BASE =
  new URLSearchParams(window.location.search).get('api') ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8010'

export const apiBase = BASE

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} on ${path}`)
  return res.json()
}

export const api = {
  marketplaces: () => get('/marketplaces'),
  history: (threadId) => get(`/threads/${encodeURIComponent(threadId)}/history`),
  state: (threadId) => get(`/threads/${encodeURIComponent(threadId)}/state`),
  memory: () => get('/memory'),
}

// Stream one chat turn (SSE). on(event, data): research | tool | token | final | error
export async function streamChat({ threadId, message, domain }, on) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, message, domain }),
  })
  if (!res.ok || !res.body) throw new Error(`chat failed with ${res.status}`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop()
    for (const frame of frames) {
      const event = frame.match(/^event: (.*)$/m)?.[1]
      const data = frame.match(/^data: (.*)$/m)?.[1]
      if (event && data) on(event, JSON.parse(data))
    }
  }
}
