"""tcb-wepro: one HTTP service that answers with a model.

POST /chat:8000 {"question": ...} ──► chat_flow ──► {answer, error}
                                        └── llm:assistant (resources.yaml; OPENROUTER_API_KEY in .env)

Every service and job of the project is declared here; operonx.toml only
points at `APP`.
"""

from operonx.app import Application, Service, env, http

from chat.graph import chat_flow

APP = Application(
    "tcb-wepro",
    description="A chat service: one LLMOp on the llm:assistant model.",
    services=[
        Service(
            "chat",
            http("POST", "/chat", port=env("PORT", 8000)),
            graph=chat_flow,
            description="POST {question}, get {answer, error}.",
        )
    ],
)
