# LaunchLens backend (FastAPI + LangGraph) — for Railway / any container host.
FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; the app talks to SerpApi/Oxylabs/OpenAI/Redis over HTTP.
COPY pyproject.toml README.md ./
COPY backend ./backend

# Install the launchlens package + API extras (fastapi, uvicorn, sse-starlette).
RUN pip install --no-cache-dir ".[api]"

# Railway/most hosts inject $PORT; default to 8010 locally.
ENV PORT=8010
EXPOSE 8010

CMD ["sh", "-c", "uvicorn launchlens.api.app:app --host 0.0.0.0 --port ${PORT:-8010}"]
