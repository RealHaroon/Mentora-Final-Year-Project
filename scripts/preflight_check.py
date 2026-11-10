"""
Phase 9 §1.4 — run this before any rehearsal or the real demo. Catches
"port already in use from yesterday's session" and similar low-drama-but-
annoying issues in seconds, before they become live-demo issues.

Adapted from the doc's sketch: no Ollama check (Phase 7 switched to Groq,
a cloud API, per the user's explicit call — see docs/phases/
MENTORA_Phase7_RAG_Pipeline.md's header note). Checks GROQ_API_KEY is set
instead, and that it actually works (a live call, not just "is it present"
— an expired/revoked key would otherwise pass a presence check and only
fail live, mid-demo).

Run: cd backend && ~/.venvs/mentora-backend/bin/python ../scripts/preflight_check.py
"""

import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

REPO_ROOT = Path(__file__).resolve().parents[1]


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


def main():
    all_ok = True
    all_ok &= check("Port 8000 free (backend)", port_free(8000))
    all_ok &= check("Port 3000 free (frontend)", port_free(3000))
    all_ok &= check("backend/.env exists", (REPO_ROOT / "backend" / ".env").exists())
    all_ok &= check(
        "ml_models/saved/ populated (>=5 model dirs)",
        (REPO_ROOT / "ml_models" / "saved").exists()
        and len(os.listdir(REPO_ROOT / "ml_models" / "saved")) >= 5,
    )
    all_ok &= check(
        "vector_store/ populated (ChromaDB)",
        (REPO_ROOT / "backend" / "vector_store").exists()
        or (REPO_ROOT / "vector_store").exists(),
    )

    try:
        from config import settings
        all_ok &= check("GROQ_API_KEY set in .env", bool(settings.groq_api_key))

        if settings.groq_api_key:
            try:
                from groq import Groq
                client = Groq(api_key=settings.groq_api_key)
                client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5,
                )
                all_ok &= check(f"Groq API key works live (model: {settings.groq_model})", True)
            except Exception as e:
                all_ok &= check(f"Groq API key works live — FAILED: {type(e).__name__}: {e}", False)
    except Exception as e:
        all_ok &= check(f"Could not load backend settings: {e}", False)

    print()
    print("All checks passed — safe to start." if all_ok else "Fix the FAILs above before starting.")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
