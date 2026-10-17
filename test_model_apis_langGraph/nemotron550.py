import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = ChatNVIDIA(
    model="nvidia/nemotron-3-ultra-550b-a55b",
    api_key=os.environ["NVIDIA_API_KEY"],
    temperature=1,
    top_p=0.95,
    max_tokens=16384,
    chat_template_kwargs={"enable_thinking":True},
)

for chunk in client.stream([{"role":"user","content":"Write a limerick about the wonders of GPU computing."}]):

    if chunk.additional_kwargs and "reasoning_content" in chunk.additional_kwargs:
        print(chunk.additional_kwargs["reasoning_content"], end="")

    print(chunk.content, end="")
