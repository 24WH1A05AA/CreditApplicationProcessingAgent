# 🚀 Production Deployment Documentation

This document describes how to deploy the **TechVest Credit Application Processing Agent** to production using Docker and Docker Compose.

---

## 🏗️ Architectural Overview
The application consists of two containerized services communicating over a virtual bridge network:
1. **Backend Service (`FastAPI`)**: Manages databases (SQLite/Postgres), executes the LangGraph underwriting state graph, queries the vector database (ChromaDB), and runs the OCR processor.
2. **Frontend Service (`Streamlit`)**: Provides an interactive dashboard for underwriters, loan queues management, AI reasoning views, and human-in-the-loop governance tools.

```
       +------------------+           +------------------+
       |   User Browser   |<=========>|    Streamlit     | (Frontend)
       +------------------+           +--------+---------+
                                               |
                                               v (Port 8000)
+----------------------------------------------+---------+
|                                                        |
|  +--------------------+      +----------------------+  |
|  |  FastAPI Endpoints |<====>|  LangGraph Workflow  |  |
|  +---------+----------+      +----------+-----------+  | (Backend)
|            |                            |              |
|            v                            v              |
|   +--------+--------+          +--------+--------+     |
|   |  Relational DB  |          | Vector Database |     |
|   | (SQLite/Postgr) |          |   (ChromaDB)    |     |
|   +-----------------+          +-----------------+     |
+--------------------------------------------------------+
```

---

## 📋 Prerequisites
Ensure the following tools are installed on your deployment server:
* **Docker** (v20.10 or higher)
* **Docker Compose** (v2.0 or higher)
* **Internet Connection** (to pull base images and access external APIs like OpenAI if configured)

---

## ⚡ Deployment Steps

### 1. Clone the Repository
Clone the codebase to your deployment server:
```bash
git clone https://github.com/24WH1A05AA/CreditApplicationProcessingAgent.git
cd CreditApplicationProcessingAgent
```

### 2. Configure Environment Variables
Copy the production environment variables template:
```bash
cp .env.production .env
```
Open `.env` in an editor and configure parameters securely:
```ini
# Generate a secure 32-character random string for SECRET_KEY
SECRET_KEY=generate_a_secure_long_secret_key_string_here_991122

# Configure OpenAI API key to enable vector embedding indexing for RAG
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. Start Container Services
Launch the application services in detached/background mode:
```bash
docker compose up -d --build
```
This command builds the Docker containers, sets up the private bridge network, mounts persistent storage volumes, and runs health checks.

### 4. Verify System Health
Verify that both containers are up and running:
```bash
docker compose ps
```
The backend healthcheck should report `healthy` within 15–20 seconds.

---

## 🛠️ Configuration Details

| Variable Name | Default Value | Description |
|---|---|---|
| `ENV` | `production` | Deployment mode (`development`, `production`). |
| `DATABASE_URL` | `sqlite:////app/data/credit_processing.db` | Connection URI. Supports SQLite & PostgreSQL. |
| `SECRET_KEY` | *N/A* | Secret key for JWT hashing. **Must be secure in production.** |
| `OPENAI_API_KEY` | `mock-key-for-development` | OpenAI API Key. Enables embedding indexing. |
| `CHROMA_DB_PATH` | `/app/data/chromadb` | Directory where ChromaDB vector logs are persisted. |

---

## 🛡️ Health Checks & Monitoring

The backend service includes a built-in health check `/health` endpoint. In `docker-compose.yml`, it is configured as follows:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 15s
  timeout: 10s
  retries: 3
```

To fetch container logs in production:
```bash
# View backend logs
docker compose logs -f backend

# View frontend logs
docker compose logs -f frontend
```

---

## 💾 Persistent Storage & Backups

Two Docker local volumes are created to persist state:
1. `app_data`: Persists the SQLite database (`credit_processing.db`), the ChromaDB vector database index, and local execution trace logs (`data/debug_traces`).
2. `app_uploads`: Persists uploaded PAN cards, Aadhaar cards, bank statements, and salary slips.

### Backing up Data
To back up the database and uploaded documents:
```bash
# Export relational database
docker compose exec backend tar -czf /app/data/backup_$(date +%F).tar.gz /app/data /app/uploads
```
