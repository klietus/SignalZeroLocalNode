# 🧠 SignalZero Local Node

**SignalZero Local Node** is a lightweight, modular runtime for executing the SignalZero symbolic framework in a local or private cloud environment. It hosts the core symbol store, provides REST interfaces for symbolic queries, and pipelines prompts to LLMs via a pluggable inference bridge (OpenAI, local models, etc.).

---

## 🔧 Features

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

SignalZero Local Node reads its runtime configuration from environment variables (a `.env` file is supported via `python-dotenv`). The following variables control how language model inference is performed:

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

### External symbol store

The runtime can hydrate its local Redis cache by synchronising against the managed SignalZero symbol store. The following
environment variables tune that integration:

| Variable | Default | Description |
| --- | --- | --- |
| `SYMBOL_STORE_BASE_URL` | `https://qnw96whs57.execute-api.us-west-2.amazonaws.com/prod` | Base URL for the external SignalZero store API. |
| `SYMBOL_STORE_TIMEOUT` | `10.0` | Client timeout (in seconds) when fetching batches from the external store. |

Set these variables when pointing the node at a different managed deployment or when running behind a proxy.

### Synchronising managed symbols

Use the `/sync/symbols` endpoint to pull records from the managed store into the local cache. The request accepts an optional
domain or tag filter and a `limit` (maximum 20 per external page). Example request:

```bash
curl -X POST http://localhost:8000/sync/symbols \
  -H "Content-Type: application/json" \
  -d '{"symbol_domain": "root", "limit": 10}'
```

The response summarises the run:

```json
{
  "fetched": 10,
  "stored": 10,
  "new": 7,
  "updated": 3,
  "pages": 1
}
```

You can repeat the sync call to stay aligned with the managed store or build it into a scheduled job. If you prefer a visual
workflow, open the web UI and navigate to **Symbol Sync** to launch runs and review metrics interactively.

Set `MODEL_PROVIDER=openai` together with the relevant OpenAI environment variables to call OpenAI-hosted models. Leave the provider at its default `local` value to continue using a self-hosted model endpoint.

---

## 🧪 Testing

The project ships with a pytest-based test suite that exercises the FastAPI application, symbol store, and utility modules. After installing the dependencies, run the tests with:

```bash
python scripts/run_tests.py
```

You can pass additional pytest arguments if needed, for example `python scripts/run_tests.py -k chat_history`.
