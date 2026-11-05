from rag.online_retriever import retrieve_health_evidence

question = "What are the symptoms of malaria?"

result = retrieve_health_evidence(question, top_k=5)

print("\n========== ONLINE RETRIEVER DIAGNOSTICS ==========")

print("\nQuestion:", result.get("question"))

print("\nProvider status:")
print(result.get("provider_status"))

print("\nUnavailable providers:")
print(result.get("providers_unavailable"))

print("\nMessage:")
print(result.get("message"))

print("\nNumber of retrieved results:")
print(len(result.get("results", [])))

print("\nRetrieved evidence:")

for item in result.get("results", []):
    print("\nTitle:", item.get("title"))
    print("Source:", item.get("source"))
    print("URL:", item.get("url"))
    print("Similarity:", item.get("similarity"))
    print("Text:", item.get("text", "")[:300])