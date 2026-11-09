import asyncio
from abc import ABC, abstractmethod

from langchain_groq import ChatGroq

from config import settings
from rag_core.prompts import build_prompt


class RAGPipeline(ABC):
    def __init__(self, collection, top_k: int = 4):
        self.collection = collection
        self.top_k = top_k
        # max_tokens caps response length — an unbounded reply risks a long,
        # rambling wait (Phase 7 doc §13's num_predict guidance, same idea).
        self.llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, max_tokens=300)

    def retrieve(self, query: str) -> list[str]:
        # Local, CPU-bound (ChromaDB + its small embedding model) — the
        # caller is responsible for running this off the event loop thread
        # (asyncio.to_thread), same reasoning as Phase 6 §0.
        result = self.collection.query(query_texts=[query], n_results=self.top_k)
        return result["documents"][0] if result["documents"] else []

    async def aretrieve(self, query: str) -> list[str]:
        # retrieve() is a synchronous, CPU-bound local call (ChromaDB's
        # on-disk query + its embedding model) — same asyncio.to_thread
        # discipline as Phase 6 §0, so it never blocks the event loop even
        # though any one call is fast on this small corpus.
        return await asyncio.to_thread(self.retrieve, query)

    async def agenerate(self, prompt: str) -> str:
        # NOT routed through Phase 6's heavy_lock semaphore, deliberately.
        # That lock exists to stop two CPU-bound jobs fighting over this
        # laptop's cores (Phase 6 §0) — but Groq's generation runs on Groq's
        # servers, not here, so there's no local CPU contention with M1/M2/M5
        # to serialize against. ainvoke() is native async I/O: it awaits the
        # HTTP response without blocking the event loop and without needing
        # a worker thread. See docs/phases/MENTORA_Phase7_RAG_Pipeline.md's
        # header note for the full Ollama->Groq rationale.
        response = await self.llm.ainvoke(prompt)
        return response.content

    @abstractmethod
    async def answer(self, query: str, **kwargs) -> str:
        """Each subclass defines its own answer() signature/behavior —
        e.g. InterviewRAG needs conversation history, ExamRAG doesn't."""
        ...
