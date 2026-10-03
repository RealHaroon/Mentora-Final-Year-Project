"""
M1 dataset — Knowledge Gap Classifier: question bank extraction.

Source: 23 real Sindh MDCAT past papers (2000-2023, user-collected), scanned
image PDFs. Per docs/phases/MENTORA_Phase3_Datasets.md §4.3-4.4, this is the
"manual part" of Phase 3 — OCR gets ~70-90% of the way, and a human pass is
expected to clean up the rest.

Pipeline:
  1. OCR each page, split into left/right halves first (papers use a strict
     2-column layout — a single-pass OCR interleaves adjacent questions from
     the two columns, verified empirically).
  2. Detect subject sections via short header lines (BIOLOGY / CHEMISTRY /
     PHYSICS / ENGLISH / LOGICAL REASONING) — confirmed present via manual
     page inspection.
  3. Parse each question block: a numbered stem ("12. ...") followed by 4-5
     lettered options (A-E; option count varies by year/section, handled
     dynamically rather than assumed fixed at 4).
  4. Deduplicate near-identical question text (these compiled PDFs reuse
     similar questions across years).

KNOWN LIMITATION (disclosed, not silently dropped): `correct_answer` is left
blank. Each paper does have a real answer-key page, but it's a bordered grid
table that proved unreliable to OCR accurately (tested column-cropping,
grid-line detection, positional-token extraction, and higher DPI — none
reached usable accuracy on the bordered-cell text). Filling this in by hand
per paper is realistically fast (a compact grid of 100-200 letters, not full
question text) — see mentora_data/SOURCES.md for the recommended approach.

Run: ~/.venvs/mentora-data/bin/python datasets/m1_gap_classifier/extract_questions.py
Output: mentora_data/processed/m1/question_bank.csv
"""

import csv
import re
import time
from pathlib import Path

import pdf2image
import pytesseract

PAPERS_DIR = Path(__file__).resolve().parents[2] / "past_papers"
OUT_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUBJECT_HEADERS = {
    "BIOLOGY": "Biology",
    "CHEMISTRY": "Chemistry",
    "PHYSICS": "Physics",
    "ENGLISH": "English",
    "LOGICAL REASONING": "Logical Reasoning",
    "REASONING": "Logical Reasoning",
}

QUESTION_START = re.compile(r"^\s*(\d{1,3})[.)]\s*(.+)$")
OPTION_LINE = re.compile(r"^\s*([A-Ea-e])[.)]\s*(.+)$")  # some papers use lowercase a-e


def ocr_full_pdf(path: Path) -> list[str]:
    pages = pdf2image.convert_from_path(str(path), dpi=200)
    lines = []
    for page in pages:
        width, height = page.size
        left = page.crop((0, 0, width // 2, height))
        right = page.crop((width // 2, 0, width, height))
        lines.extend(pytesseract.image_to_string(left).split("\n"))
        lines.extend(pytesseract.image_to_string(right).split("\n"))
    return lines


def parse_questions(lines: list[str], source: str) -> list[dict]:
    questions = []
    current_subject = "Unknown"
    pending = None  # {"number", "text", "options": {letter: text}}

    def flush():
        if pending and pending["text"].strip() and len(pending["options"]) >= 2:
            questions.append(
                {
                    "source": source,
                    "subject": current_subject,
                    "question_number": pending["number"],
                    "question_text": pending["text"].strip(),
                    "options": dict(pending["options"]),
                }
            )

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        header_match = next((v for k, v in SUBJECT_HEADERS.items() if k in line.upper() and len(line) < 30), None)
        if header_match:
            flush()
            pending = None
            current_subject = header_match
            continue

        opt_match = OPTION_LINE.match(line)
        if opt_match and pending is not None:
            letter, text = opt_match.groups()
            pending["options"][letter.upper()] = text.strip()
            continue

        q_match = QUESTION_START.match(line)
        if q_match:
            flush()
            number, text = q_match.groups()
            pending = {"number": int(number), "text": text, "options": {}}
            continue

        # Continuation of the question stem or an option, before any option
        # letter has appeared yet — append to the stem.
        if pending is not None and not pending["options"]:
            pending["text"] += " " + line

    flush()
    return questions


def dedupe(questions: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for q in questions:
        key = re.sub(r"\W+", "", q["question_text"].lower())[:80]
        if key in seen or len(key) < 10:
            continue
        seen.add(key)
        unique.append(q)
    return unique


def main():
    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    all_questions = []

    for i, path in enumerate(pdf_files, 1):
        t0 = time.time()
        lines = ocr_full_pdf(path)
        questions = parse_questions(lines, source=path.stem)
        elapsed = time.time() - t0
        print(f"[{i}/{len(pdf_files)}] {path.name}: {len(questions)} questions parsed ({elapsed:.0f}s)")
        all_questions.extend(questions)

    print(f"\nTotal before dedup: {len(all_questions)}")
    unique_questions = dedupe(all_questions)
    print(f"Total after dedup: {len(unique_questions)}")

    by_subject = {}
    for q in unique_questions:
        by_subject[q["subject"]] = by_subject.get(q["subject"], 0) + 1
    print("\nBy subject:")
    for subject, count in sorted(by_subject.items(), key=lambda x: -x[1]):
        print(f"  {subject}: {count}")

    out_path = OUT_DIR / "question_bank.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["question_id", "source", "subject", "topic", "subtopic", "difficulty", "question_text", "options", "correct_answer"]
        )
        for i, q in enumerate(unique_questions, 1):
            writer.writerow(
                [
                    i,
                    q["source"],
                    q["subject"],
                    "",  # topic — TODO, needs manual tagging per doc §4.4
                    "",  # subtopic — TODO
                    "",  # difficulty — TODO
                    q["question_text"],
                    str(q["options"]),
                    "",  # correct_answer — TODO, see docstring
                ]
            )
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
