import asyncio

from operonx.app.jobs import Job

from chat.graph import chat_flow
from chat.ops import clean, reply


def test_clean_collapses_whitespace():
    assert clean(question=" what  is\noperonx? ")()["question"] == "what is operonx?"


def test_reply_reports_a_failed_model_call():
    out = reply(error="timeout")()
    assert out == {"answer": None, "error": "timeout"}


def test_the_flow_answers_with_the_model(fake_model, tmp_path):
    job = Job(
        "t",
        graph=chat_flow,
        items=[{"question": "Hello?"}],  # each item fills the graph's parameters
        key="question",
        record_dir=tmp_path,
    )
    run = asyncio.run(job.run())
    assert run.status == "ok"
    assert run.results == {"Hello?": {"answer": "Echo: Hello?", "error": None}}


def test_the_service_answers_and_refuses_a_bad_body(fake_model):
    from pathlib import Path

    from operonx.app import Application
    from starlette.testclient import TestClient

    app = Application.find(Path(__file__).resolve().parent.parent)
    with TestClient(app.asgi()) as client:
        ok = client.post("/chat", json={"question": "Hello?"})
        bad = client.post("/chat", json={"q": "typo"})
    assert ok.status_code == 200 and ok.json() == {"answer": "Echo: Hello?", "error": None}
    assert bad.status_code == 400 and bad.json()["field"] == "q"
