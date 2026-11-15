from rag_core.chroma_client import exam_kb
from rag_core.pipeline import RAGPipeline
from rag_core.prompts import build_prompt


class ExamRAG(RAGPipeline):
    def __init__(self, max_tokens: int = 300):
        super().__init__(collection=exam_kb, max_tokens=max_tokens)

    async def answer(self, query: str) -> str:
        chunks = await self.aretrieve(query)
        if not chunks:
            return "I don't have information on that in my materials right now."
        return await self.agenerate(build_prompt(chunks, query))
