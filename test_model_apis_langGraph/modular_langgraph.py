r"""One-file prototype: swap model adapters without changing the LangGraph.

Setup (PowerShell, from the project root):
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    # Put NVIDIA_API_KEY=... in the project-root .env file.

Run:
    .\.venv\Scripts\python.exe test_model_apis_langGraph/modular_langgraph.py
    .\.venv\Scripts\python.exe test_model_apis_langGraph/modular_langgraph.py --model nemotron550
    .\.venv\Scripts\python.exe test_model_apis_langGraph/modular_langgraph.py --model deepseek "What is 2 + 2?"

Architecture (logical modules kept together for this proof of concept):
    1. ModelAdapter contract: generate(prompt) -> answer text.
    2. Three adapters own SDKs, model IDs, and provider-specific settings.
    3. MODEL_ADAPTERS registry and DEFAULT_MODEL select the implementation.
    4. build_agent() accepts ANY adapter; graph code knows no SDK or model ID.

Change DEFAULT_MODEL below or use --model to switch. To add a fourth model,
implement generate() and register its class; no graph changes are needed.
Later, these sections can move into separate files without changing the contract.

This is a single-turn START -> respond -> END graph, with no tools or memory.
Nemotron uses LangChain ChatNVIDIA; DeepSeek uses the supplied OpenAI-compatible
API. Adapters return final answer text only; reasoning stays out of graph state.
An empty reply raises an error rather than appearing to be a successful test.
Timeouts apply to network inactivity, not total runtime for a streaming reply.

References checked through Context7:
https://docs.langchain.com/oss/python/langgraph/graph-api
https://github.com/langchain-ai/langchain-nvidia/tree/main/libs/ai-endpoints
"""

import argparse
import os
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypedDict

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.graph import END, START, StateGraph
from openai import OpenAI


# Module 1: the small contract shared by all model implementations.
class ModelAdapter(Protocol):
    def generate(self, prompt: str) -> str: ...


BASE_URL = "https://integrate.api.nvidia.com/v1"
TIMEOUT = 120.0


def stream_answer(client, prompt: str) -> str:
    """Collect LangChain's final text chunks; omit separate reasoning content."""
    return "".join(
        block["text"]
        for chunk in client.stream([{"role": "user", "content": prompt}])
        for block in chunk.content_blocks
        if block.get("type") == "text"
    )


# Module 2a: Nemotron 120 model settings stay inside this adapter.
class Nemotron120Adapter:
    def __init__(self, api_key: str):
        self.client = ChatNVIDIA(
            base_url=BASE_URL,
            model="nvidia/nemotron-3.5-super-vl-120b-a12b",
            api_key=api_key,
            temperature=1,
            top_p=0.95,
            max_completion_tokens=16384,
            seed=42,
            timeout=TIMEOUT,
        ).bind(chat_template_kwargs={"enable_thinking": True}, parallel_tool_calls=True)

    def generate(self, prompt: str) -> str:
        return stream_answer(self.client, prompt)


# Module 2b: Nemotron 550 has its own configuration.
class Nemotron550Adapter:
    def __init__(self, api_key: str):
        self.client = ChatNVIDIA(
            base_url=BASE_URL,
            model="nvidia/nemotron-3-ultra-550b-a55b",
            api_key=api_key,
            temperature=1,
            top_p=0.95,
            max_completion_tokens=16384,
            timeout=TIMEOUT,
        ).bind(chat_template_kwargs={"enable_thinking": True})

    def generate(self, prompt: str) -> str:
        return stream_answer(self.client, prompt)


# Module 2c: even a different SDK fits the same graph contract.
class DeepSeekAdapter:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        with OpenAI(
            base_url=BASE_URL, api_key=self.api_key, timeout=TIMEOUT, max_retries=0
        ) as client:
            response = client.chat.completions.create(
                model="deepseek-ai/deepseek-v4.1-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                stream=False,
            )
            return response.choices[0].message.content or ""


# Module 3: the single place where model selection is configured.
DEFAULT_MODEL = "nemotron120"
MODEL_ADAPTERS: dict[str, Callable[[str], ModelAdapter]] = {
    "nemotron120": Nemotron120Adapter,
    "nemotron550": Nemotron550Adapter,
    "deepseek": DeepSeekAdapter,
}


# Module 4: model-independent graph; only the generate() contract is used here.
class AgentState(TypedDict):
    prompt: str
    answer: str


def build_agent(model: ModelAdapter):
    """Inject the chosen adapter once; all nodes can use the same interface."""
    def respond(state: AgentState):
        answer = model.generate(state["prompt"])
        if not answer.strip():
            raise RuntimeError("Model returned no final answer text.")
        return {"answer": answer}

    builder = StateGraph(AgentState)
    builder.add_node("respond", respond)
    builder.add_edge(START, "respond")
    builder.add_edge("respond", END)
    return builder.compile()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--model", choices=MODEL_ADAPTERS, default=DEFAULT_MODEL)
    parser.add_argument("prompt", nargs="*", help="Optional prompt; defaults to a smoke test.")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        parser.error("Set NVIDIA_API_KEY in the project-root .env file.")

    model = MODEL_ADAPTERS[args.model](api_key)
    agent = build_agent(model)
    prompt = " ".join(args.prompt) or "Reply with exactly: LANGGRAPH_OK"
    print(f"Model: {args.model}", flush=True)
    result = agent.invoke({"prompt": prompt})
    print(result["answer"])


if __name__ == "__main__":
    main()
