from rag.online_retriever import fetch_webpage_text

url = "https://www.who.int/news-room/fact-sheets/detail/malaria"

try:
    content = fetch_webpage_text(url)

    print("\n========== WHO RETRIEVAL TEST ==========")
    print("URL:", url)
    print("Content length:", len(content))
    print("\nExtracted content:\n")
    print(content[:2500])

except Exception as error:
    print("WHO retrieval failed:", repr(error))