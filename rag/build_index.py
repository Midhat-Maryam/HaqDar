"""
Embeds SCPA Act + Rules sections into a persistent ChromaDB collection.

Uses a custom TF-IDF embedding function instead of ChromaDB's default
ONNX MiniLM model, because the sandbox network can't reliably pull the
default model weights. TF-IDF works well here since the corpus is small
(48 sections) and legal text has distinctive per-section vocabulary.

For production, swap in OpenAI's text-embedding-3-small (needs API key
and network egress to api.openai.com) — see the commented alternative
at the bottom of this file.
"""

import json
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle

with open("/home/claude/haqdar/data/scpa_dataset.json", "r", encoding="utf-8") as f:
    data = json.load(f)

all_sections = data["act_sections"] + data["rules_sections"]

# Plain-language trigger phrases per section, layered onto the legal text so
# TF-IDF has vocabulary overlap with how real consumers describe complaints
# (not just legal terminology). This closes the biggest gap TF-IDF has vs.
# a semantic embedder — keyed by section id.
TRIGGER_PHRASES = {
    "act_s4": "appliance stopped working, phone broke after purchase, machine malfunctioned, gadget is faulty, product broke down, device failed, item not working properly, TV stopped working, laptop broke",
    "act_s5": "product came out wrong, item not made properly, manufacturing fault, poor build quality, product different from specification",
    "act_s6": "product design is unsafe, dangerous design flaw, product hazard by design",
    "act_s7": "no warning label, dangerous product no warning, safety warning missing, product caused injury no warning given",
    "act_s8": "product doesn't match warranty claims, warranty promise was false, seller lied about warranty, product doesn't do what warranty said",
    "act_s9": "manufacturer defense, manufacturer didn't know about defect",
    "act_s13": "bad service, service was faulty, technician did poor work, repair job was bad, service provider messed up, plumber electrician mechanic did bad work, tailor ruined my clothes, poor workmanship",
    "act_s14": "service below standard, service quality was poor, unprofessional service",
    "act_s16": "service provider lied about qualifications, fake expert, unqualified technician, provider didn't disclose skill level",
    "act_s18": "no price displayed, shop didn't show prices, price not listed, no price tag",
    "act_s19": "no receipt given, shopkeeper refused receipt, seller didn't give bill, no proof of purchase",
    "act_s20": "no refund policy shown, store didn't explain return policy, return policy not disclosed, refund refused",
    "act_s21": "false advertising, misleading claims, lied about product, fake claims about quality, seller lied, product not as advertised, fake reviews, false promises",
    "act_s22": "fake discount, bait and switch, advertised price not honored, sale price was a scam, discount was fake, promotional trick",
    "act_s23": "how to file complaint with authority, where to complain, who enforces this law",
    "act_s29": "before filing complaint, notice to seller, warning letter to company, first step before court, legal notice",
    "act_s31": "how court handles complaint, complaint process, what happens after filing",
    "act_s32": "what can court order, refund replace compensation, court remedies, what will I get from complaint",
    "act_s33": "penalty for violation, fine for company, punishment for seller, jail time for violation",
    "act_s34": "how to appeal, disagree with court decision, appeal process",
}

corpus_texts = []
for sec in all_sections:
    triggers = TRIGGER_PHRASES.get(sec["id"], "")
    text = f"{sec['title']}. {sec['text']}"
    if triggers:
        text += f" Related everyday complaint phrases: {triggers}."
    corpus_texts.append(text)

vectorizer = TfidfVectorizer(max_features=2000, stop_words="english", ngram_range=(1, 2))
vectorizer.fit(corpus_texts)

with open("/home/claude/haqdar/rag/tfidf_vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)


class TfidfEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        matrix = vectorizer.transform(input)
        return matrix.toarray().tolist()


embed_fn = TfidfEmbeddingFunction()

client = chromadb.PersistentClient(path="/home/claude/haqdar/rag/chroma_db")

try:
    client.delete_collection("scpa_sections")
except Exception:
    pass

collection = client.create_collection(
    name="scpa_sections",
    embedding_function=embed_fn,
    metadata={"description": "Sindh Consumer Protection Act 2014 + Rules 2017, section-level chunks (TF-IDF embeddings)"}
)

ids, documents, metadatas = [], [], []

for sec, text in zip(all_sections, corpus_texts):
    ids.append(sec["id"])
    documents.append(text)
    metadatas.append({
        "source": "Act" if sec["id"].startswith("act_") else "Rules",
        "section_no": sec["section_no"],
        "part": sec["part"],
        "title": sec["title"],
    })

collection.add(ids=ids, documents=documents, metadatas=metadatas)

print(f"Indexed {len(ids)} sections into ChromaDB (TF-IDF embeddings).")

test_queries = [
    "phone stopped working after two weeks, shop won't replace it",
    "shopkeeper didn't give me a receipt",
    "restaurant advertised a discount that didn't actually apply",
    "electrician did shoddy wiring work in my house",
]

for q in test_queries:
    print(f"\n--- Query: {q!r} ---")
    results = collection.query(query_texts=[q], n_results=3)
    for i, (doc_id, meta, dist) in enumerate(zip(
        results["ids"][0], results["metadatas"][0], results["distances"][0]
    )):
        print(f"  {i+1}. [{meta['source']} {meta['section_no']}] {meta['title']} (distance={dist:.3f})")

# -----------------------------------------------------------------------
# PRODUCTION ALTERNATIVE (OpenAI embeddings):
#
# from chromadb.utils import embedding_functions
# embed_fn = embedding_functions.OpenAIEmbeddingFunction(
#     api_key=os.environ["OPENAI_API_KEY"],
#     model_name="text-embedding-3-small"
# )
# -----------------------------------------------------------------------
