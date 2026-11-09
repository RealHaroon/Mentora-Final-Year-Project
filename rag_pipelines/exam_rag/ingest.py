"""
Run: cd backend && ~/.venvs/mentora-backend/bin/python ../rag_pipelines/exam_rag/ingest.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from rag_core.chroma_client import exam_kb
from rag_core.ingest_utils import ingest_directory

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")

if __name__ == "__main__":
    ingest_directory(exam_kb, CONTENT_DIR, "exam_kb")
