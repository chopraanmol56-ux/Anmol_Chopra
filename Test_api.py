from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.rag.crew_agents import AgenticRAGResult

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Document Search Platform" in resp.json()["name"]


def test_list_models():
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"][0]["id"] == "document-search-agentic-rag"


@patch("src.api.routes.run_agentic_rag")
def test_query_endpoint(mock_run):
    mock_run.return_value = AgenticRAGResult(
        answer="Answer text.",
        sources=[{"source_file": "handbook.pdf", "score": 0.87}],
        rewritten_query="what is X",
        grounded=True,
        iterations=1,
    )
    resp = client.post("/api/v1/query", json={"query": "what is X?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Answer text."
    assert body["grounded"] is True
    assert body["sources"][0]["source_file"] == "handbook.pdf"


@patch("src.api.routes.run_agentic_rag")
def test_chat_completions_endpoint(mock_run):
    mock_run.return_value = AgenticRAGResult(answer="Chat answer.", grounded=True, iterations=1)
    resp = client.post(
        "/v1/chat/completions",
        json={
            "model": "document-search-agentic-rag",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "Chat answer."
