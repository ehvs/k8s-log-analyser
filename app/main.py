"""RAG API: retrieval no Qdrant + geração no SLM (Ollama)."""
import os

import httpx
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from qdrant_client import QdrantClient

# APIs compatíveis com OpenAI: mesmo código serve RamaLama (cluster) e Ollama (dev).
LLM_URL = os.getenv("LLM_URL", "http://ramalama-llm:8080")
EMBED_URL = os.getenv("EMBED_URL", "http://ramalama-embed:8080")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
TOP_K = int(os.getenv("TOP_K", "4"))

app = FastAPI(title="SLM + RAG API")
qdrant = QdrantClient(url=QDRANT_URL)

# Expõe métricas Prometheus em /metrics (latência, contagem por rota, etc.)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    sources: list[str]


def embed(text: str) -> list[float]:
    resp = httpx.post(
        f"{EMBED_URL}/v1/embeddings",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def generate(prompt: str) -> str:
    resp = httpx.post(
        f"{LLM_URL}/v1/chat/completions",
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        hits = qdrant.search(
            collection_name=COLLECTION,
            query_vector=embed(req.question),
            limit=TOP_K,
        )
    except Exception as exc:  # coleção ausente / Qdrant fora do ar
        raise HTTPException(status_code=503, detail=str(exc))

    if not hits:
        return AskResponse(answer="Não encontrei nada na base de conhecimento.", sources=[])

    context = "\n\n".join(h.payload.get("text", "") for h in hits)
    sources = [h.payload.get("source", "desconhecido") for h in hits]
    prompt = (
        "Você é um assistente de SRE. Responda usando SOMENTE o contexto abaixo. "
        "Se a resposta não estiver no contexto, diga que não sabe.\n\n"
        f"Contexto:\n{context}\n\nPergunta: {req.question}\n\nResposta:"
    )
    return AskResponse(answer=generate(prompt), sources=sources)
