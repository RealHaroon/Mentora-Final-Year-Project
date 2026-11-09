from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,  # characters, not tokens — keep well under the LLM's context budget once several chunks are retrieved together
    chunk_overlap=60,  # a little overlap avoids losing meaning right at a chunk boundary
    separators=["\n\n", "\n", ". ", " ", ""],  # prefer splitting on paragraph/sentence boundaries over mid-word
)


def chunk_document(text: str) -> list[str]:
    return splitter.split_text(text)
