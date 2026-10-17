import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = ChatNVIDIA(
    base_url="https://integrate.api.nvidia.com/v1",
    model="nvidia/nemotron-3.5-super-vl-120b-a12b",
    api_key=os.environ["NVIDIA_API_KEY"],
    temperature=1,
    top_p=0.95,
    max_completion_tokens=16384,


    seed=42,
)


client = client.bind(**{"chat_template_kwargs": {"enable_thinking": True}, "parallel_tool_calls": True})


for chunk in client.stream([{"role": "user", "content": [{"type": "text", "text": "Read the traffic sign in this image. What does it say, and what color is the sign?"}, {"type": "image_url", "image_url": {"url": "https://assets.ngc.nvidia.com/products/api-catalog/phi-3-5-vision/example1a.jpg"}}]}]):
    if chunk.additional_kwargs and "reasoning_content" in chunk.additional_kwargs:
        print(chunk.additional_kwargs["reasoning_content"], end="")
    print(chunk.content, end="")
