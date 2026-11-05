
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util


# ---------------------------------------------------------
# API CONFIGURATION
# ---------------------------------------------------------

MYHEALTHFINDER_BASE = (
    "https://odphp.health.gov/myhealthfinder/api/v4"
)

CDC_BASE = "https://tools.cdc.gov/api/v2"
CDC_SEARCH_URL = f"{CDC_BASE}/resources/media"

WHO_FACT_SHEETS_URL = (
    "https://www.who.int/news-room/fact-sheets"
)

TIMEOUT = 20
MAX_CANDIDATES = 5
MAX_CONTENT_LENGTH = 12000

USER_AGENT = "HealthGuideAI/1.0"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/json",
}

_embedding_model = None


# ---------------------------------------------------------
# EMBEDDING MODEL
# ---------------------------------------------------------

def get_model() -> SentenceTransformer:
    """Load the sentence-transformer model only when needed."""

    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

    return _embedding_model


# ---------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------

def get_json(
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a GET request and return a JSON response."""

    response = requests.get(
        url,
        params=params,
        timeout=TIMEOUT,
        headers=HEADERS,
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Unexpected API response format.")

    return data


def html_to_text(html: str) -> str:
    """Convert HTML content into readable plain text."""

    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "header",
            "footer",
            "nav",
        ]
    ):
        element.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def fetch_webpage_text(url: str) -> str:
    """Fetch a public webpage and extract readable text."""

    if not url or not url.startswith("https://"):
        return ""

    response = requests.get(
        url,
        timeout=TIMEOUT,
        headers=HEADERS,
    )

    response.raise_for_status()

    return html_to_text(response.text)[:MAX_CONTENT_LENGTH]


def normalize_query(question: str) -> str:
    """Normalize a health question for provider searches."""

    question = re.sub(r"\s+", " ", question).strip()

    return question[:300]


def make_passage(
    source: str,
    title: str,
    section: str,
    text: str,
    url: str,
    last_updated: str = "",
) -> dict[str, str]:
    """Create a consistent evidence structure."""

    return {
        "source": source,
        "title": title,
        "section": section,
        "text": text[:MAX_CONTENT_LENGTH],
        "url": url,
        "last_updated": last_updated,
    }


def normalize_list(value: Any) -> list:
    """Convert an API value into a list safely."""

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        return [value]

    return []


# ---------------------------------------------------------
# MYHEALTHFINDER RETRIEVER
# ---------------------------------------------------------

def get_myhealthfinder_topics() -> list[dict[str, Any]]:
    """Retrieve available MyHealthfinder topics."""

    response = get_json(
        f"{MYHEALTHFINDER_BASE}/itemlist.json",
        params={
            "Type": "topic",
        },
    )

    result = response.get("Result", {})
    items = result.get("Items", {})

    topics = normalize_list(
        items.get("Item", [])
    )

    return topics


def extract_myhealthfinder_sections(
    response: dict[str, Any],
) -> list[dict[str, str]]:
    """Extract readable sections from MyHealthfinder."""

    result = response.get("Result", {})
    resources = result.get("Resources", {})

    resource_list = normalize_list(
        resources.get("Resource", [])
    )

    passages = []

    for resource in resource_list:

        title = (
            resource.get("Title")
            or resource.get("title")
            or "MyHealthfinder Resource"
        )

        url = (
            resource.get("AccessibleVersion")
            or resource.get("URL")
            or resource.get("url")
            or ""
        )

        sections_data = resource.get("Sections", {})

        sections = (
            sections_data.get("section")
            or sections_data.get("Section")
            or []
        )

        sections = normalize_list(sections)

        for section in sections:

            section_title = (
                section.get("Title")
                or section.get("title")
                or "Health Information"
            )

            content = (
                section.get("Content")
                or section.get("content")
                or ""
            )

            text = html_to_text(str(content))

            if len(text) < 50:
                continue

            passages.append(
                make_passage(
                    source="MyHealthfinder",
                    title=title,
                    section=section_title,
                    text=text,
                    url=url,
                    last_updated=(
                        resource.get("LastUpdate")
                        or resource.get("LastUpdated")
                        or ""
                    ),
                )
            )

    return passages


def get_myhealthfinder_candidates(
    question: str,
) -> list[dict[str, Any]]:
    """Retrieve relevant MyHealthfinder resources."""

    topics = get_myhealthfinder_topics()

    if not topics:
        return []

    topic_titles = []

    for topic in topics:

        title = (
            topic.get("Title")
            or topic.get("title")
            or ""
        )

        if title:
            topic_titles.append((title, topic))

    if not topic_titles:
        return []

    model = get_model()

    question_embedding = model.encode(
        question,
        convert_to_tensor=True,
    )

    title_embeddings = model.encode(
        [item[0] for item in topic_titles],
        convert_to_tensor=True,
    )

    similarities = util.cos_sim(
        question_embedding,
        title_embeddings,
    )[0]

    ranked_indices = similarities.argsort(
        descending=True
    )[:MAX_CANDIDATES]

    candidates = []

    for index in ranked_indices:

        topic = topic_titles[int(index)][1]

        topic_id = (
            topic.get("Id")
            or topic.get("ID")
            or topic.get("id")
        )

        if not topic_id:
            continue

        try:

            response = get_json(
                f"{MYHEALTHFINDER_BASE}/topicsearch.json",
                params={
                    "TopicId": topic_id,
                },
            )

            candidates.extend(
                extract_myhealthfinder_sections(response)
            )

        except (
            requests.RequestException,
            ValueError,
            TypeError,
        ) as error:

            print(
                f"MyHealthfinder resource error "
                f"({topic_id}): {error}"
            )

    return candidates


# ---------------------------------------------------------
# CDC RETRIEVER
# ---------------------------------------------------------

def get_cdc_items(
    response: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract CDC media records from the API response."""

    results = response.get("results", [])

    if isinstance(results, dict):

        items = (
            results.get("items")
            or results.get("Items")
            or results.get("results")
            or []
        )

        return normalize_list(items)

    return normalize_list(results)


def get_cdc_content(
    item_id: str,
) -> str:
    """Retrieve syndicated CDC content using its media ID."""

    response = get_json(
        f"{CDC_SEARCH_URL}/{item_id}/syndicate",
        params={
            "stripScripts": "true",
            "stripComments": "true",
        },
    )

    results = response.get("results", {})

    if isinstance(results, list):
        results = results[0] if results else {}

    if isinstance(results, dict):

        content = (
            results.get("content")
            or results.get("description")
            or ""
        )

    elif isinstance(results, str):
        content = results

    else:
        content = ""

    return html_to_text(str(content))


def get_cdc_candidates(
    question: str,
) -> list[dict[str, Any]]:
    """Retrieve CDC resources using the user's health question."""

    query = normalize_query(question)

    response = get_json(
        CDC_SEARCH_URL,
        params={
            "q": query,
            "max": 50,
            "pagenum": 1,
            "mediaTypes": "HTML",
            "languageIsoCode": "eng",
        },
    )

    items = get_cdc_items(response)

    candidates = []

    for item in items:

        item_id = (
            item.get("id")
            or item.get("ID")
            or item.get("mediaId")
        )

        title = (
            item.get("name")
            or item.get("title")
            or "CDC Health Resource"
        )

        description = (
            item.get("description")
            or item.get("summary")
            or ""
        )

        url = (
            item.get("targetUrl")
            or item.get("sourceUrl")
            or item.get("url")
            or ""
        )

        content = ""

        # First choice: retrieve official CDC syndicated content.
        if item_id:

            try:

                content = get_cdc_content(
                    str(item_id)
                )

            except (
                requests.RequestException,
                ValueError,
                TypeError,
            ) as error:

                print(
                    f"CDC content error "
                    f"({item_id}): {error}"
                )

        # Second choice: retrieve the original webpage.
        if not content and url:

            try:

                content = fetch_webpage_text(url)

            except requests.RequestException as error:

                print(
                    f"CDC webpage error "
                    f"({item_id}): {error}"
                )

        # Last choice: use the available description.
        if not content:
            content = html_to_text(
                str(description)
            )

        if len(content) < 50:
            continue

        candidates.append(
            make_passage(
                source="CDC",
                title=title,
                section="CDC Health Information",
                text=content,
                url=url,
                last_updated=(
                    item.get("datePublished")
                    or item.get("dateModified")
                    or ""
                ),
            )
        )

    return candidates


# ---------------------------------------------------------
# WHO RETRIEVER
# ---------------------------------------------------------

def get_who_fact_sheet_links(
    question: str,
) -> list[dict[str, str]]:
    """
    Retrieve official WHO fact-sheet links.

    Uses the WHO fact-sheets index instead of relying
    on the website search-results page.
    """

    response = requests.get(
        WHO_FACT_SHEETS_URL,
        timeout=TIMEOUT,
        headers=HEADERS,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    links = []
    seen_urls = set()

    for anchor in soup.find_all("a", href=True):

        href = anchor.get("href", "")

        full_url = urljoin(
            "https://www.who.int",
            href,
        )

        if not full_url.startswith(
            "https://www.who.int/news-room/fact-sheets/detail/"
        ):
            continue

        if full_url in seen_urls:
            continue

        title = anchor.get_text(
            separator=" ",
            strip=True,
        )

        if not title:
            title = anchor.get("aria-label", "")

        if not title:
            title = full_url.rstrip("/").split("/")[-1]

        seen_urls.add(full_url)

        links.append({
            "title": title,
            "url": full_url,
        })

    return links


def get_who_candidates(
    question: str,
) -> list[dict[str, Any]]:
    """Retrieve relevant WHO health fact sheets."""

    links = get_who_fact_sheet_links(question)

    if not links:
        return []

    model = get_model()

    question_embedding = model.encode(
        question,
        convert_to_tensor=True,
    )

    titles = [
        item["title"]
        for item in links
    ]

    title_embeddings = model.encode(
        titles,
        convert_to_tensor=True,
    )

    similarities = util.cos_sim(
        question_embedding,
        title_embeddings,
    )[0]

    ranked_indices = similarities.argsort(
        descending=True
    )[:MAX_CANDIDATES]

    candidates = []

    for index in ranked_indices:

        link = links[int(index)]

        try:

            content = fetch_webpage_text(
                link["url"]
            )

            if len(content) < 100:
                continue

            candidates.append(
                make_passage(
                    source="World Health Organization",
                    title=link["title"],
                    section="WHO Health Information",
                    text=content,
                    url=link["url"],
                )
            )

        except requests.RequestException as error:

            print(
                f"WHO webpage error "
                f"({link['title']}): {error}"
            )

    return candidates


# ---------------------------------------------------------
# SEMANTIC RANKING
# ---------------------------------------------------------

def rank_evidence(
    question: str,
    candidates: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rank retrieved passages by semantic similarity."""

    if not candidates:
        return []

    model = get_model()

    question_embedding = model.encode(
        question,
        convert_to_tensor=True,
    )

    texts = [
        (
            item.get("title", "")
            + " "
            + item.get("section", "")
            + " "
            + item["text"]
        )
        for item in candidates
    ]

    text_embeddings = model.encode(
        texts,
        convert_to_tensor=True,
    )

    similarities = util.cos_sim(
        question_embedding,
        text_embeddings,
    )[0]

    ranked_indices = similarities.argsort(
        descending=True
    )[:top_k]

    ranked_results = []

    for index in ranked_indices:

        item = candidates[int(index)].copy()

        item["similarity"] = float(
            similarities[int(index)].item()
        )

        ranked_results.append(item)

    return ranked_results


# ---------------------------------------------------------
# DUPLICATE REMOVAL
# ---------------------------------------------------------

def remove_duplicate_evidence(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove exact duplicate passages."""

    unique_candidates = []
    seen_texts = set()

    for item in candidates:

        normalized_text = re.sub(
            r"\s+",
            " ",
            item.get("text", "").lower(),
        ).strip()

        if not normalized_text:
            continue

        if normalized_text in seen_texts:
            continue

        seen_texts.add(normalized_text)

        unique_candidates.append(item)

    return unique_candidates


# ---------------------------------------------------------
# MAIN ONLINE RETRIEVAL FUNCTION
# ---------------------------------------------------------

def retrieve_health_evidence(
    question: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Retrieve and rank health evidence from:

    1. MyHealthfinder
    2. CDC
    3. WHO
    """

    if not question or not question.strip():

        return {
            "question": question,
            "results": [],
            "providers_unavailable": [],
            "provider_status": {},
            "message": "Please provide a health question.",
        }

    question = question.strip()

    providers = {
        "MyHealthfinder": get_myhealthfinder_candidates,
        "CDC": get_cdc_candidates,
        "WHO": get_who_candidates,
    }

    provider_status = {
        name: {
            "status": "pending",
            "results": 0,
        }
        for name in providers
    }

    candidates = []

    # Retrieve from all providers concurrently.
    with ThreadPoolExecutor(max_workers=3) as executor:

        futures = {
            name: executor.submit(function, question)
            for name, function in providers.items()
        }

        for provider, future in futures.items():

            try:

                results = future.result()

                provider_status[provider] = {
                    "status": (
                        "success" if results else "no_results"
                    ),
                    "results": len(results),
                }

                candidates.extend(results)

            except Exception as error:

                print(
                    f"{provider} retrieval error: {error}"
                )

                provider_status[provider] = {
                    "status": "error",
                    "results": 0,
                }

    providers_unavailable = [
        provider
        for provider, info in provider_status.items()
        if info["status"] == "error"
    ]

    unique_candidates = remove_duplicate_evidence(
        candidates
    )

    try:

        ranked_results = rank_evidence(
            question,
            unique_candidates,
            top_k=top_k,
        )

    except Exception as error:

        print(
            f"Evidence ranking error: {error}"
        )

        ranked_results = []

    if ranked_results:

        message = (
            "Health information was retrieved "
            "from available online sources."
        )

    elif providers_unavailable:

        message = (
            "Some health information providers "
            "were unavailable. No evidence was retrieved."
        )

    else:

        message = (
            "No health information was retrieved "
            "for this question."
        )

    return {
        "question": question,
        "results": ranked_results,
        "providers_unavailable": providers_unavailable,
        "provider_status": provider_status,
        "message": message,
    }
