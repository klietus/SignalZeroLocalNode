# 🧠 SignalZero Local Node

**SignalZero Local Node** is a lightweight, modular runtime for executing the SignalZero symbolic framework in a local or private cloud environment. It hosts the core symbol store, provides REST interfaces for symbolic queries, and pipelines prompts to LLMs via a pluggable inference bridge (OpenAI, local models, etc.).

---

## 🔧 Features (planned)

- ⚙️ FastAPI web server (stubbed for local or cloud)
- 🗃️ Embedded or remote Symbol Store (SQLite / DynamoDB)
- 🧠 RAG-style prompt generator using full symbolic payloads
- 🧵 Inference bridge for OpenAI / Bedrock / Ollama / others
- 📤 RESTful API for injecting, syncing, querying, and debugging
- 🔒 Stateless + auditable, suited for AGI-aligned deployment
- 📡 Supports client-side voice input via optional local modules

---

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_ORG/signalzero-node.git
cd signalzero-node

pip install -r requirements.txt

./scripts/launch_server.sh
```

---

## ⚙️ Configuration

SignalZero Local Node reads its runtime configuration from environment variables (a `.env` file is supported via `python-dotenv`). A checked-in `.env.example` file captures the defaults used by `docker-compose`; copy it to `.env` to customize the stack locally. The following variables control how language model inference is performed:

| Variable | Default | Description |
| --- | --- | --- |
| `MODEL_PROVIDER` | `local` | Selects the inference backend (`local` or `openai`). |
| `MODEL_API_URL` | `http://localhost:11434/api/generate` | REST endpoint for the local model server. |
| `MODEL_NAME` | `llama3:8b-text-q5_K_M` | Name of the local model to invoke. |
| `MODEL_NUM_PREDICT` | `48` | Token prediction budget for the local model call. |
| `OPENAI_API_KEY` | _required when using OpenAI_ | API key used to authenticate with OpenAI. |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name to invoke. |
| `OPENAI_BASE_URL` | unset | Optional override for the OpenAI API base URL. |
| `OPENAI_TEMPERATURE` | `0.0` | Sampling temperature for OpenAI responses. |
| `OPENAI_MAX_OUTPUT_TOKENS` | `256` | Maximum tokens returned from OpenAI. |

Set `MODEL_PROVIDER=openai` together with the relevant OpenAI environment variables to call OpenAI-hosted models. Leave the provider at its default `local` value to continue using a self-hosted model endpoint.

---

## 🧪 Testing

The project ships with a pytest-based test suite that exercises the FastAPI application, symbol store, and utility modules. After installing the dependencies, run the tests with:

```bash
python scripts/run_tests.py
```

You can pass additional pytest arguments if needed, for example `python scripts/run_tests.py -k chat_history`.
