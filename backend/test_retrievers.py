from rag.online_retriever import retrieve_health_evidence
from rag.retriever import search_health_documents


question = "What are common ways to prevent type 2 diabetes?"

print("\n========== ONLINE RETRIEVER ==========")

online_results = retrieve_health_evidence(question, top_k=5)

print("Number of online results:", len(online_results.get("results", [])))
print("Unavailable providers:", online_results.get("providers_unavailable", []))

for item in online_results.get("results", []):
    print("\nTitle:", item.get("title"))
    print("Source:", item.get("source"))
    print("Text:", item.get("text", "")[:250])
    print("Similarity:", item.get("similarity"))


print("\n========== LOCAL CHROMADB RETRIEVER ==========")

local_results = search_health_documents(question, top_k=3)

print("Number of local results:", len(local_results))

for item in local_results:
    print("\nSource:", item.get("source"))
    print("Text:", item.get("text", "")[:250])
    print("Distance:", item.get("distance"))