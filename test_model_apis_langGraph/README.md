# Model API and LangGraph prototype

**Project model: Nemotron 120B** (`nvidia/nemotron-3.5-super-vl-120b-a12b`). It successfully answered an image question through LangChain and passed the modular LangGraph test. DeepSeek V4.1 Flash timed out; Nemotron 550B returned a temporary overload error.

`modular_langgraph.py` has three model adapters behind one shared interface. Change `DEFAULT_MODEL` or pass `--model` to switch models without changing the graph.

A larger agent can keep retrieval, keyword/vector search, reranking, context preparation, and tool execution in separate graph nodes. The adapter interface would expand to support messages, images, tool calls, and structured responses. Each chosen model must support the features its role needs.

Run from the project root using the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe test_model_apis_langGraph/modular_langgraph.py --model nemotron120
```

The `.env`, `.venv`, and `requirements.txt` stay in the project root. The original `deepseek_api_template.py` expects `NVIDIA_API_KEY` to be set in the process environment.
