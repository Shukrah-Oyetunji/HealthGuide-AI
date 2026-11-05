
from rag.hybrid_retriever import retrieve_hybrid_evidence


question = "What are common ways to prevent type 2 diabetes?"

response = retrieve_hybrid_evidence(
    question,
    top_k=5,
)

print("\n========== HYBRID RETRIEVER ==========")

print("Question:", response["question"])
print("Online results:", response["total_online_results"])
print("Local results:", response["total_local_results"])
print("Unique results:", response["total_unique_results"])
print("Has evidence:", response["has_evidence"])

print("\n========== RANKED EVIDENCE ==========")

for index, item in enumerate(response["results"], start=1):
    print(f"\nResult {index}")
    print("Source:", item["source"])
    print("Title:", item["title"])
    print("Retrieval method:", item["retrieval_method"])
    print("Relevance:", round(item["relevance_score"], 4))
    print("Page:", item["page"])
    print("URL:", item["url"])
    print("Text:", item["text"][:300])
