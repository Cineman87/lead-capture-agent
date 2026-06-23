"""Query function Hermes calls to retrieve relevant vault chunks."""
from ingest import COLLECTION_NAME, DB_PATH, embed_text

import chromadb


def query_vault(question: str, n_results: int = 5):
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    embedding = embed_text(question)
    results = collection.query(query_embeddings=[embedding], n_results=n_results)

    chunks = []
    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    distances = results.get("distances") or [[]]
    for text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
        chunks.append({"text": text, "metadata": metadata, "distance": distance})
    return chunks


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "What is this vault about?"
    for chunk in query_vault(question):
        print(f"\n--- {chunk['metadata']['source_file']} > {chunk['metadata']['header']} (dist={chunk['distance']:.4f}) ---")
        print(chunk["text"])
