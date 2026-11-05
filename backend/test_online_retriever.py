
from rag.online_retriever import retrieve_health_evidence


TEST_QUESTIONS = [
    "What causes malaria?",
    "What are the symptoms of diabetes?",
    "What causes hypertension?",
    "What are the symptoms of asthma?",
    "How can anaemia be prevented?",
    "What are the symptoms of breast cancer?",
    "How can heart disease be prevented?",
    "What are the benefits of breastfeeding?",
    "What causes tuberculosis?",
    "What are the symptoms of influenza?",
]


for question in TEST_QUESTIONS:

    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    response = retrieve_health_evidence(
        question,
        top_k=5,
    )

    print("\nPROVIDER STATUS:")

    for provider, status in response[
        "provider_status"
    ].items():

        print(
            f"{provider}: "
            f"{status['status']} "
            f"({status['results']} results)"
        )

    print("\nRETRIEVED EVIDENCE:")

    for result in response["results"]:

        print("\nSource:", result["source"])
        print("Title:", result["title"])
        print("Similarity:", result["similarity"])
        print("URL:", result["url"])
        print("Content:", result["text"][:300])

    print("\nMESSAGE:", response["message"])
