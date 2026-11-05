
from rag.online_retriever import (
    get_myhealthfinder_candidates,
    get_cdc_candidates,
)

question = "What are common ways to prevent type 2 diabetes?"

print("\nTESTING MYHEALTHFINDER")

try:
    my_results = get_myhealthfinder_candidates(question)

    print("Results:", len(my_results))

    for item in my_results[:2]:
        print("Title:", item["title"])
        print("Text:", item["text"][:200])

except Exception as exc:
    print("MyHealthfinder error:", type(exc).__name__, str(exc))


print("\nTESTING CDC")

try:
    cdc_results = get_cdc_candidates(question)

    print("Results:", len(cdc_results))

    for item in cdc_results[:2]:
        print("Title:", item["title"])
        print("Text:", item["text"][:200])

except Exception as exc:
    print("CDC error:", type(exc).__name__, str(exc))
