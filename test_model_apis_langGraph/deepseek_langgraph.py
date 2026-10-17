"""Minimal LangGraph + NVIDIA DeepSeek proof of concept.

Install: python -m pip install -r requirements.txt
Run from project root: python test_model_apis_langGraph/deepseek_langgraph.py
Requires NVIDIA_API_KEY in the project-root .env file.
"""

import os
import sys
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import OpenAI


class State(TypedDict):
    prompt: str
    answer: str


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise SystemExit("Set NVIDIA_API_KEY in the project-root .env file.")

    # Use the same NVIDIA endpoint and DeepSeek model as the supplied template.
    with OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        timeout=120.0,
        max_retries=0,
    ) as client:

        def call_deepseek(state: State):
            response = client.chat.completions.create(
                model="deepseek-ai/deepseek-v4.1-flash",
                messages=[{"role": "user", "content": state["prompt"]}],
                max_tokens=1024,
                stream=False,
            )
            answer = response.choices[0].message.content
            if not answer or not answer.strip():
                raise RuntimeError("DeepSeek returned no answer; try increasing max_tokens.")
            return {"answer": answer}

        # START -> DeepSeek -> END: the API request runs inside LangGraph.
        builder = StateGraph(State)
        builder.add_node("deepseek", call_deepseek)
        builder.add_edge(START, "deepseek")
        builder.add_edge("deepseek", END)
        agent = builder.compile()

        prompt = " ".join(sys.argv[1:]) or "Reply with exactly: LANGGRAPH_DEEPSEEK_OK"
        result = agent.invoke({"prompt": prompt})
        print(result["answer"])


if __name__ == "__main__":
    main()
