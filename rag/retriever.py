"""
Retrieval tool used by the LangGraph agent's Legal Retrieval node.
Wraps the ChromaDB collection built by build_index.py.
"""

import pickle
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import CHROMA_PATH, CHROMA_COLLECTION_NAME, VECTORIZER_PATH, RETRIEVAL_TOP_K

with open(VECTORIZER_PATH, "rb") as f:
    _vectorizer = pickle.load(f)


class TfidfEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return _vectorizer.transform(input).toarray().tolist()


_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_collection(
    name=CHROMA_COLLECTION_NAME,
    embedding_function=TfidfEmbeddingFunction(),
)


def retrieve_sections(query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
    """
    Retrieve the top-k most relevant Act/Rules sections for a consumer complaint.

    Returns a list of dicts: {section_no, source, title, text, distance}
    Used by the LangGraph 'legal_retrieval' node and callable directly
    by the MCP server as a tool.
    """
    results = _collection.query(query_texts=[query], n_results=top_k)

    out = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        out.append({
            "section_no": meta["section_no"],
            "source": meta["source"],
            "title": meta["title"],
            "part": meta["part"],
            "text": doc,
            "distance": round(dist, 4),
        })
    return out


if __name__ == "__main__":
    import json
    r = retrieve_sections("my washing machine broke after a week and the shop refuses to fix it")
    print(json.dumps(r, indent=2))
