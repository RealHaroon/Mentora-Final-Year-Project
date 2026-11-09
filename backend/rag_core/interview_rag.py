from rag_core.chroma_client import interview_kb
from rag_core.pipeline import RAGPipeline

_START_PROMPT = """You are conducting a mock job interview for a {career_title} role.
Using the reference questions below as inspiration, ask the student ONE realistic
opening interview question. Ask only the question, nothing else.

REFERENCE MATERIAL:
{reference}
"""

_CONTINUE_PROMPT = """You are conducting a mock job interview for a {career_title} role.
Give brief, constructive feedback on the student's last answer (2-3 sentences), then
ask ONE follow-up or new interview question, using the reference material where relevant.

REFERENCE MATERIAL:
{reference}

CONVERSATION SO FAR:
{history_text}

STUDENT'S LATEST ANSWER:
{student_answer}
"""


class InterviewRAG(RAGPipeline):
    def __init__(self):
        super().__init__(collection=interview_kb)

    async def start(self, career_title: str) -> str:
        chunks = await self.aretrieve(f"interview questions for {career_title}")
        prompt = _START_PROMPT.format(career_title=career_title, reference="\n\n".join(chunks))
        return await self.agenerate(prompt)

    async def answer(self, career_title: str, conversation_history: list[dict], student_answer: str) -> str:
        chunks = await self.aretrieve(f"{career_title} interview: {student_answer}")
        history_text = "\n".join(f"{turn['role']}: {turn['text']}" for turn in conversation_history)
        prompt = _CONTINUE_PROMPT.format(
            career_title=career_title,
            reference="\n\n".join(chunks),
            history_text=history_text,
            student_answer=student_answer,
        )
        return await self.agenerate(prompt)
