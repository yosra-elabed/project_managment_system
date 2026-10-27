import chromadb
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer('all-MiniLM-L6-v2')

_client = chromadb.PersistentClient(path="chroma_db")
_collection = _client.get_or_create_collection(name="pms_documents")


def add_document(doc_id: str, text: str, metadata: dict):
    if not text or not text.strip():
        return
    embedding = _model.encode(text).tolist()
    _collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata]
    )


def search(query: str, allowed_project_ids: list, top_k: int = 5):
    if not allowed_project_ids:
        return []

    query_embedding = _model.encode(query).tolist()
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"project_id": {"$in": allowed_project_ids}}
    )

    if not results['documents'] or not results['documents'][0]:
        return []

    return [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(results['documents'][0], results['metadatas'][0])
    ]