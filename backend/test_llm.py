from rag.llm_service import generate_health_answer

question = "What are common ways to prevent type 2 diabetes?"

sample_evidence = [
    {
        "title": "Preventing Type 2 Diabetes",
        "source": "CDC",
        "text": (
            "Lifestyle changes such as healthy eating, regular physical "
            "activity and maintaining a healthy weight can help reduce "
            "the risk of developing type 2 diabetes."
        ),
        "url": "https://www.cdc.gov/diabetes/",
        "page": None,
    }
]

try:
    result = generate_health_answer(question, sample_evidence)

    print("\n========== HEALTHGUIDE AI RESPONSE ==========")
    print("\nAnswer:\n", result["answer"])

    print("\nSources:")
    for source in result["sources"]:
        print(source)

except Exception as error:
    print("LLM test failed:", error)