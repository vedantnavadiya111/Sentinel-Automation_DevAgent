import os
import uuid
from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from mem0 import Memory
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer


class StoreRequest(BaseModel):
    user_id: str = Field(default="default_user")
    error: str
    fix: str
    metadata: dict | None = None


class RecallResponse(BaseModel):
    results: dict


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@lru_cache(maxsize=1)
def get_memory() -> Memory:
    qdrant_host = os.environ.get("QDRANT_HOST", "qdrant")
    qdrant_port = _env_int("QDRANT_PORT", 6333)

    collection_name = os.environ.get("MEM0_COLLECTION", "sentinel_memories")

    embed_model = os.environ.get("HF_EMBED_MODEL", "multi-qa-MiniLM-L6-cos-v1")
    embed_dims = _env_int("HF_EMBED_DIMS", 384)

    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()

    # Zero-cost default: if Groq isn't configured, skip Mem0 init and use fallback storage.
    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY not set; using qdrant_fallback")

    # Mem0 uses environment variables for provider auth.
    # - GROQ_API_KEY for Groq
    # - Hugging Face local embeddings do not require a key.
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": qdrant_host,
                "port": qdrant_port,
                "collection_name": collection_name,
                "embedding_model_dims": embed_dims,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": embed_model,
                "embedding_dims": embed_dims,
            },
        },
        "llm": {
            "provider": "groq",
            "config": {
                "model": groq_model,
                "temperature": 0.1,
                "max_tokens": 800,
            },
        },
    }

    return Memory.from_config(config)


@lru_cache(maxsize=1)
def get_fallback_embedder() -> SentenceTransformer:
    # This runs fully locally.
    model_name = os.environ.get("HF_EMBED_MODEL", "multi-qa-MiniLM-L6-cos-v1")
    return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    qdrant_host = os.environ.get("QDRANT_HOST", "qdrant")
    qdrant_port = _env_int("QDRANT_PORT", 6333)
    return QdrantClient(host=qdrant_host, port=qdrant_port)


def _ensure_collection(client: QdrantClient, collection_name: str, dims: int) -> None:
    try:
        client.get_collection(collection_name)
        return
    except Exception:
        pass

    client.create_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(size=dims, distance=qmodels.Distance.COSINE),
    )


app = FastAPI(title="Sentinel Memory", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/store")
def store(req: StoreRequest) -> dict:
    # Prefer Mem0 when configured; fall back to direct Qdrant storage when keys/providers aren't set.
    try:
        memory = get_memory()
        messages = [
            {"role": "user", "content": f"Runtime error:\n{req.error}"},
            {"role": "assistant", "content": f"Applied fix:\n{req.fix}"},
        ]
        return memory.add(messages=messages, user_id=req.user_id, metadata=req.metadata or {"type": "bugfix"})
    except Exception as e:
        client = get_qdrant_client()
        collection_name = os.environ.get("MEM0_COLLECTION", "sentinel_memories")
        embed_dims = _env_int("HF_EMBED_DIMS", 384)
        _ensure_collection(client, collection_name, embed_dims)

        embedder = get_fallback_embedder()
        vector = embedder.encode(f"ERROR\n{req.error}\n\nFIX\n{req.fix}").tolist()
        point_id = str(uuid.uuid4())

        payload = {
            "user_id": req.user_id,
            "error": req.error,
            "fix": req.fix,
            "metadata": req.metadata or {"type": "bugfix"},
            "backend": "qdrant_fallback",
            "fallback_reason": str(e),
        }

        client.upsert(
            collection_name=collection_name,
            points=[qmodels.PointStruct(id=point_id, vector=vector, payload=payload)],
        )

        return {"status": "stored", "backend": "qdrant_fallback", "id": point_id}


@app.get("/recall", response_model=RecallResponse)
def recall(user_id: str, query: str, limit: int = 5) -> RecallResponse:
    try:
        memory = get_memory()
        results = memory.search(query=query, user_id=user_id, limit=limit)
        return RecallResponse(results=results)
    except Exception as e:
        client = get_qdrant_client()
        collection_name = os.environ.get("MEM0_COLLECTION", "sentinel_memories")
        embed_dims = _env_int("HF_EMBED_DIMS", 384)
        _ensure_collection(client, collection_name, embed_dims)

        embedder = get_fallback_embedder()
        vector = embedder.encode(query).tolist()

        response = client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            query_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="user_id", match=qmodels.MatchValue(value=user_id))]
            ),
            with_payload=True,
            with_vectors=False,
        )

        fallback_results = {
            "backend": "qdrant_fallback",
            "fallback_reason": str(e),
            "results": [
                {
                    "id": str(point.id),
                    "score": point.score,
                    "payload": point.payload,
                }
                for point in (response.points or [])
            ],
        }
        return RecallResponse(results=fallback_results)
