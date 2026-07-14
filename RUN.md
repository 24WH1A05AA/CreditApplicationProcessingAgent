# 🚀 Run & Test Guide (with OpenRouter Integration)

This guide provides step-by-step instructions to run, configure, and test the **TechVest Credit Application Underwriting Agent** locally or via Docker, including how to configure **OpenRouter** with free LLM models.

---

## 🛠️ Step-by-Step Local Run Command List

Follow these commands to get the application up and running perfectly in your local Python environment:

### 1. Setup Virtual Environment
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Project Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure OpenRouter & Free Models
Copy the environment template file:
```bash
cp .env.production .env
```
Open `.env` in a text editor and update the OpenAI API configurations to point to OpenRouter. Since OpenRouter uses the standard OpenAI-compatible REST API specification, you can direct the backend client to OpenRouter endpoints by configuring:

```ini
# Provide your OpenRouter API Key:
OPENAI_API_KEY=your_openrouter_api_key_here

# Change the model string to one of OpenRouter's free models:
# Examples:
# - meta-llama/llama-3-8b-instruct:free
# - google/gemma-2-9b-it:free
# - mistralai/mistral-7b-instruct:free
OPENAI_MODEL=meta-llama/llama-3-8b-instruct:free
```

> [!NOTE]
> Since OpenRouter is primarily used for LLM chat completion tasks, if you want the RAG vector embeddings database to leverage OpenRouter or external providers, we have built-in safe fallbacks: if no direct OpenAI embeddings key is active, the system automatically uses local `FakeEmbeddings` to process and index the knowledge base files, running locally on your CPU without any network overhead!

### 4. Run the Local Backend Server
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
* **API Documentation**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser to inspect and run Swagger requests.

### 5. Run the Frontend UI (in a new terminal tab/window)
```bash
# Make sure your virtual environment is active in the new tab:
# On Windows: .\venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate

streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1
```
* **Underwriter Dashboard**: Open [http://127.0.0.1:8501](http://127.0.0.1:8501) in your browser to interact with the application.

---

## 🧪 How to Run Automated Tests

### Run Unit & Integration Tests (`pytest`)
To execute the test suite (verifying document validations, scoring engine, RAG pipelines, LangGraph paths, auth logic, and telemetry tracing):
```bash
python -m pytest
```

### Run Underwriting Scenario Benchmarks
To run the evaluation suite against the 5 golden scenarios:
```bash
python -m backend.evaluation.run_eval
```
This executes the scenarios, verifies recommendations, check demographic-blind fairness, and writes a report at `backend/evaluation/evaluation_report.md`.

---

## 🐳 Docker Compose Step-by-Step Commands

To deploy the entire multi-container stack (both FastAPI backend and Streamlit UI) with persistence and health check gates in one command:

```bash
# Build and run the containers in background mode
docker compose up -d --build

# Verify that services are up and healthy
docker compose ps

# Monitor log telemetry stream
docker compose logs -f
```
* Access Frontend UI: [http://localhost:8501](http://localhost:8501)
* Access Backend APIs: [http://localhost:8000/docs](http://localhost:8000/docs)
