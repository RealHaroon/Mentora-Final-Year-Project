import chromadb

from config import settings

# PersistentClient writes straight to local disk under vector_store/ — no
# server process, no Docker. Default embedding function (small ONNX MiniLM,
# downloaded automatically on first use, ~90MB) — deliberately NOT reusing
# M4's all-mpnet-base-v2: M4 was fine-tuned for skill-to-career similarity,
# which is a worse semantic fit for general topic/interview content than a
# general-purpose sentence embedder. See Phase 7 doc §4.1.
client = chromadb.PersistentClient(path=settings.chroma_path)


def get_collection(name: str):
    # get_or_create_collection is idempotent — safe to call on every startup.
    return client.get_or_create_collection(name=name)


exam_kb = get_collection("exam_kb")
career_kb = get_collection("career_kb")
interview_kb = get_collection("interview_kb")
