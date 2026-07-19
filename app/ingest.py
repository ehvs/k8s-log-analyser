"""Pipeline de ingestão: lê documentos .md/.txt de ./data e grava embeddings no Qdrant.

Uso local:   python ingest.py
No cluster:  roda como um Job do Kubernetes (ver k8s/ingest-job.yaml).
"""
import os
import uuid
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

EMBED_URL = os.getenv("EMBED_URL", "http://ramalama-embed:8080")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))


def embed(text: str) -> list[float]:
    resp = httpx.post(
        f"{EMBED_URL}/v1/embeddings",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def chunks(text: str, size: int) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    out, buf = [], ""
    for p in paras:
        if len(buf) + len(p) > size and buf:
            out.append(buf)
            buf = p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf:
        out.append(buf)
    return out


def main():
    qdrant = QdrantClient(url=QDRANT_URL)
    dim = len(embed("dimension probe"))
    qdrant.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    points = []
    for path in sorted(DATA_DIR.glob("**/*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        for chunk in chunks(path.read_text(encoding="utf-8"), CHUNK_SIZE):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embed(chunk),
                    payload={"text": chunk, "source": path.name},
                )
            )

    if not points:
        print(f"Nenhum documento em {DATA_DIR}. Nada a ingerir.")
        return
    qdrant.upsert(collection_name=COLLECTION, points=points)
    print(f"Ingeridos {len(points)} chunks na coleção '{COLLECTION}'.")


if __name__ == "__main__":
    main()
