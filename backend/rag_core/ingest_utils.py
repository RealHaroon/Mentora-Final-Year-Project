import os

import frontmatter

from rag_core.chunking import chunk_document


def ingest_directory(collection, content_dir: str, label: str) -> int:
    # Wipe and rebuild rather than trying to diff — content set is small
    # enough (dozens to low hundreds of documents) that idempotent full
    # rebuilds are simpler and safer than incremental updates here.
    existing_ids = collection.get()["ids"]
    if existing_ids:
        collection.delete(ids=existing_ids)

    filenames = [f for f in os.listdir(content_dir) if f.endswith(".md")]
    ids, documents, metadatas = [], [], []
    for filename in filenames:
        post = frontmatter.load(os.path.join(content_dir, filename))
        chunks = chunk_document(post.content)
        for i, chunk in enumerate(chunks):
            ids.append(f"{filename}::chunk{i}")
            documents.append(chunk)
            metadatas.append({
                "source": filename,
                "topic": post.get("topic", post.get("career", "")),
                "type": post.get("type", ""),
                "chunk_index": i,
            })

    if documents:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Ingested {len(documents)} chunks from {len(filenames)} documents into {label}")
    return len(documents)
