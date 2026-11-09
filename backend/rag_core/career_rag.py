from rag_core.chroma_client import career_kb
from rag_core.pipeline import RAGPipeline
from rag_core.prompts import build_prompt


class CareerRAG(RAGPipeline):
    def __init__(self):
        super().__init__(collection=career_kb)

    async def answer(self, query: str) -> str:
        chunks = await self.aretrieve(query)
        if not chunks:
            return "I don't have information on that in my materials right now."
        return await self.agenerate(build_prompt(chunks, query))
