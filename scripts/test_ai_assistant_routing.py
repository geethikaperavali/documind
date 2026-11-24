"""
DocuMind - AI Assistant Intent Routing & Grounded Citations Test Suite
Uses FastAPI TestClient with an isolated mock authentication dependency,
or a dedicated test account with credentials supplied through environment variables.
Never hardcodes personal identities or exposes signing secrets.
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import get_current_user


def get_mock_test_user():
    """
    Isolated mock authentication dependency for automated testing.
    Can be configured via TEST_USER_ID / TEST_USER_EMAIL environment variables.
    """
    return {
        "id": os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000001"),
        "email": os.getenv("TEST_USER_EMAIL", "test.analyst@documind.internal"),
        "role": "authenticated",
        "user_metadata": {"full_name": "QA Test Analyst"},
        "token": "isolated-mock-test-token"
    }


# Apply mock authentication override
app.dependency_overrides[get_current_user] = get_mock_test_user
client = TestClient(app)


def ask(question: str):
    t0 = time.time()
    response = client.post("/api/chat/ask", json={"question": question, "history": []})
    elapsed = time.time() - t0

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    data = response.json()
    source_type = data.get("source_type", "unknown")
    answer = data.get("answer", "")
    sources = data.get("sources", [])

    print(f"=== Question: {question} ===")
    print(f"Status: {response.status_code} ({elapsed:.2f}s) | Source Type: {source_type}")
    print(f"Answer Sample:\n{answer[:260]}...")
    print(f"Citations/Sources ({len(sources)}):")
    for s in sources[:3]:
        title = s.get("source", s.get("title", "Ref"))
        snippet = s.get("url", s.get("snippet", ""))[:80]
        print(f"  - [{title}]: {snippet}")
    print("\n" + "-" * 60 + "\n")
    return data


if __name__ == "__main__":
    print("TESTING AI ASSISTANT INTENT ROUTING & GROUNDED CITATIONS\n")
    # 1. Document query
    ask("What is DocuMind's retention and memory cache policy according to our uploaded document?")

    # 2. Live research query
    ask("What are the key technical capabilities and context window of Gemini 2.5 Pro?")

    # 3. Hybrid doc + live web query
    ask("Does our uploaded DocuMind document retention policy comply with the Digital Personal Data Protection Act 2023?")
