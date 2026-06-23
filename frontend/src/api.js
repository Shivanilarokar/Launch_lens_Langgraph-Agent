const API = import.meta.env.VITE_API_URL || "http://localhost:8010";

// Stream a chat turn. `on(event, data)` is called for each SSE event:
//   research | tool | token | final | error
export async function streamChat({ threadId, message, domain }, on) {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message, domain }),
  });
  if (!res.ok || !res.body) throw new Error(`backend ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop();
    for (const frame of frames) {
      const event = frame.match(/^event: (.*)$/m)?.[1];
      const data = frame.match(/^data: (.*)$/m)?.[1];
      if (event && data) on(event, JSON.parse(data));
    }
  }
}

export async function getMarkets() {
  const res = await fetch(`${API}/marketplaces`);
  return res.json();
}
