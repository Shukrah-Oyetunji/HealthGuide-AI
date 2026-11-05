
import requests

URL = "https://tools.cdc.gov/api/v2/resources/media"

tests = [
    {
        "name": "Diabetes self-management",
        "params": {"topicIds": "6129"},
    },
    {
        "name": "National Diabetes Prevention Program",
        "params": {"topicIds": "10886"},
    },
    {
        "name": "Both diabetes topics",
        "params": {"topicIds": "6129,10886"},
    },
    {
        "name": "Topic name search",
        "params": {"topic": "Self-Management of Diabetes"},
    },
]

for test in tests:
    print(f"\n========== {test['name']} ==========")

    try:
        response = requests.get(
            URL,
            params={
                **test["params"],
                "max": 10,
                "pagenum": 1,
            },
            timeout=20,
            headers={"User-Agent": "HealthGuideAI/1.0"},
        )

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        pagination = data.get("meta", {}).get("pagination", {})

        print("Total matching records:", pagination.get("total"))
        print("Returned records:", len(results))

        for item in results:
            print("\nTitle:", item.get("name"))
            print("ID:", item.get("id"))
            print("Description:", item.get("description"))
            print("URL:", item.get("targetUrl"))

    except Exception as exc:
        print("Error:", type(exc).__name__, str(exc))
