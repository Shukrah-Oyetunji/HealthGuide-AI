
import re

from rag.online_retriever import retrieve_health_evidence
from rag.retriever import search_health_documents


# Minimum semantic similarity required before evidence is considered.
MIN_RELEVANCE_SCORE = 0.35

# General words that do not identify a specific health topic.
STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "and", "or",
    "of", "to", "in", "on", "for", "how", "does", "do",
    "can", "could", "would", "should", "with", "from",
    "about", "explain", "tell", "me", "please", "it",
    "its", "this", "that", "be", "by", "as", "which",
    "when", "where", "why", "who", "their", "they",
    "we", "you", "your", "i", "my"
}

# General health terms that are less useful for identifying
# the specific subject of a question.
GENERAL_HEALTH_TERMS = {
    "health", "healthy", "disease", "diseases", "illness",
    "illnesses", "condition", "conditions", "medical",
    "medicine", "symptom", "symptoms", "sign", "signs",
    "cause", "causes", "caused", "risk", "risks",
    "treatment", "treatments", "prevent", "prevention",
    "preventing", "manage", "management", "care",
    "information", "outbreak", "outbreaks", "patient",
    "patients", "infection", "infections"
}


def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    text = str(text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> set:
    """Convert text into a set of meaningful word tokens."""
    return set(re.findall(r"\b[a-zA-Z]{3,}\b", text.lower()))


def extract_question_terms(question: str) -> set:
    """Extract meaningful terms from a question."""
    words = tokenize(question)

    return {
        word
        for word in words
        if word not in STOP_WORDS
    }


def extract_topic_terms(question: str) -> set:
    """
    Extract terms that identify the specific subject
    of the health question.
    """
    question_terms = extract_question_terms(question)

    return {
        term
        for term in question_terms
        if term not in GENERAL_HEALTH_TERMS
    }


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_relevance(
    question_terms: set,
    topic_terms: set,
    item: dict,
) -> tuple:
    """
    Calculate a relevance score using semantic similarity
    and keyword matches.

    Returns:
        (final_score, is_topic_relevant)
    """

    similarity = safe_float(item.get("relevance_score", 0))

    title_tokens = tokenize(item.get("title", ""))
    content_tokens = tokenize(item.get("text", ""))

    document_tokens = title_tokens | content_tokens

    # Check whether the document discusses the specific
    # topic mentioned in the question.
    matched_topic_terms = topic_terms & document_tokens

    # If a specific topic was identified, require at least
    # one matching topic term in the retrieved document.
    if topic_terms and not matched_topic_terms:
        return similarity, False

    # Give more importance to matches in document titles.
    title_matches = question_terms & title_tokens
    content_matches = question_terms & content_tokens

    title_bonus = (
        len(title_matches) / len(question_terms) * 0.10
        if question_terms else 0.0
    )

    content_bonus = (
        len(content_matches) / len(question_terms) * 0.05
        if question_terms else 0.0
    )

    # Small bonus for matching the specific health topic.
    topic_bonus = (
        len(matched_topic_terms) / len(topic_terms) * 0.10
        if topic_terms else 0.0
    )

    final_score = min(
        1.0,
        similarity + title_bonus + content_bonus + topic_bonus,
    )

    return final_score, True


def retrieve_hybrid_evidence(
    question: str,
    top_k: int = 5,
    online_top_k: int = 5,
    local_top_k: int = 5,
) -> dict:
    """
    Retrieve and rank relevant health evidence from
    online health sources and local ChromaDB documents.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if min(top_k, online_top_k, local_top_k) < 1:
        raise ValueError("All top_k values must be at least 1.")

    question_terms = extract_question_terms(question)
    topic_terms = extract_topic_terms(question)

    combined_results = []

    # -----------------------------------------------------
    # 1. Retrieve online evidence
    # -----------------------------------------------------

    online_response = retrieve_health_evidence(
        question,
        top_k=online_top_k,
    )

    online_results = online_response.get("results", [])

    providers_unavailable = online_response.get(
        "providers_unavailable", []
    )

    print("\n========== ONLINE RETRIEVAL DEBUG ==========")

    for index, item in enumerate(online_results, start=1):
        print(f"\nResult {index}")
        print("Title:", item.get("title"))
        print("Source:", item.get("source"))
        print("Similarity:", item.get("similarity"))
        print("URL:", item.get("url"))
        print("Content:", item.get("text", "")[:500])

    print("============================================\n")

    for item in online_results:
        similarity = safe_float(item.get("similarity", 0))

        combined_results.append({
            "text": item.get("text", ""),
            "source": item.get("source", "Online source"),
            "title": item.get("title", "Untitled"),
            "section": item.get("section"),
            "url": item.get("url"),
            "page": None,
            "chunk": None,
            "relevance_score": similarity,
            "retrieval_method": "online",
        })

    # -----------------------------------------------------
    # 2. Retrieve local ChromaDB evidence
    # -----------------------------------------------------

    local_results = search_health_documents(
        question,
        top_k=local_top_k,
    )

    for item in local_results:
        distance = safe_float(item.get("distance", 1))

        similarity = max(
            0.0,
            min(1.0, 1.0 - distance),
        )

        combined_results.append({
            "text": item.get("text", ""),
            "source": item.get("source", "Local document"),
            "title": item.get("source", "Local document"),
            "section": None,
            "url": None,
            "page": item.get("page"),
            "chunk": item.get("chunk"),
            "relevance_score": similarity,
            "retrieval_method": "local",
        })

    # -----------------------------------------------------
    # 3. Remove empty and duplicate passages
    # -----------------------------------------------------

    unique_results = []
    seen_texts = set()

    for item in combined_results:
        text = str(item.get("text") or "").strip()

        if not text:
            continue

        normalized = normalize_text(text)

        if normalized in seen_texts:
            continue

        seen_texts.add(normalized)

        item["text"] = text
        unique_results.append(item)

    # -----------------------------------------------------
    # 4. Filter and rank evidence
    # -----------------------------------------------------

    print("\n========== HEALTHGUIDE RETRIEVAL DEBUG ==========")
    print("Question:", question)
    print("Question terms:", sorted(question_terms))
    print("Topic terms:", sorted(topic_terms))

    ranked_results = []

    for item in unique_results:
        similarity = safe_float(
            item.get("relevance_score", 0)
        )

        document_tokens = tokenize(
            item.get("title", "") + " " + item.get("text", "")
        )

        matching_topics = topic_terms & document_tokens

        print("\nTitle:", item.get("title"))
        print("Source:", item.get("source"))
        print("Similarity:", similarity)
        print("Matching topic terms:", sorted(matching_topics))

        # Reject documents below the minimum semantic score.
        if similarity < MIN_RELEVANCE_SCORE:
            print("Rejected: similarity below threshold")
            continue

        # Reject documents that do not discuss the requested topic.
        if topic_terms and not matching_topics:
            print("Rejected: no matching health topic")
            continue

        final_score, is_topic_relevant = calculate_relevance(
            question_terms=question_terms,
            topic_terms=topic_terms,
            item=item,
        )

        if not is_topic_relevant:
            print("Rejected: topic relevance check failed")
            continue

        item["relevance_score"] = round(final_score, 4)

        print("Accepted. Final score:", item["relevance_score"])

        ranked_results.append(item)

    ranked_results.sort(
        key=lambda item: item["relevance_score"],
        reverse=True,
    )

    print("\nTotal relevant results:", len(ranked_results))
    print("=================================================\n")

    # -----------------------------------------------------
    # 5. Select the best evidence
    # -----------------------------------------------------

    selected_results = ranked_results[:top_k]

    return {
        "question": question,
        "results": selected_results,
        "total_online_results": len(online_results),
        "total_local_results": len(local_results),
        "total_unique_results": len(unique_results),
        "total_relevant_results": len(ranked_results),
        "providers_unavailable": providers_unavailable,
        "has_evidence": len(selected_results) > 0,
    }
