from rag_core.chroma_client import career_kb, exam_kb, interview_kb


def test_exam_retrieval_finds_quadratic_content():
    result = exam_kb.query(query_texts=["how to factor x squared minus 5x plus 6"], n_results=3)
    sources = [m["source"] for m in result["metadatas"][0]]
    assert "algebra-quadratic-equations.md" in sources


def test_exam_retrieval_finds_grammar_content():
    result = exam_kb.query(query_texts=["what is the difference between active and passive voice"], n_results=3)
    sources = [m["source"] for m in result["metadatas"][0]]
    assert "general-english-grammar-tenses.md" in sources


def test_career_retrieval_finds_data_scientist_content():
    result = career_kb.query(query_texts=["what skills do I need to become a data scientist"], n_results=3)
    sources = [m["source"] for m in result["metadatas"][0]]
    assert "career-data-scientist.md" in sources


def test_interview_retrieval_finds_star_method_for_technique_questions():
    result = interview_kb.query(query_texts=["how should I structure my answer to a behavioral question"], n_results=3)
    sources = [m["source"] for m in result["metadatas"][0]]
    assert "interview-technique-star-method.md" in sources
