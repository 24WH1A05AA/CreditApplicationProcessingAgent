# 🚀 Deploying to Render: Step-by-Step Guide

This guide provides step-by-step instructions to deploy the **TechVest Credit Application Processing Agent** (FastAPI backend + Streamlit frontend) onto [Render](https://render.com/).

---

## 🏗️ Deployment Architecture on Render

On Render, the project runs as two **Web Services**:
1. **`credit-backend`**: A FastAPI Docker service that processes OCR, coordinates the LangGraph agent, and hosts database APIs.
2. **`credit-frontend`**: A Streamlit Docker service that communicates with the backend via internal/external networking.

```
       +------------------+           +------------------+
       |   User Browser   |<=========>|   Streamlit UI   | (credit-frontend)
       +------------------+           +--------+---------+
                                               |
                                               v (Private Network)
+----------------------------------------------+---------+
|                                                        |
|   +--------------------+     +----------------------+  |
|   |  FastAPI Backend   |<===>|   LangGraph Agent    |  | (credit-backend)
|   +---------+----------+     +----------+-----------+  |
|             |                           |              |
|             v                           v              |
|     SQLite / Postgres               ChromaDB           |
|                                                        |
+--------------------------------------------------------+
```

---

## 💾 Understanding Data Persistence on Render

Render operates on an ephemeral filesystem for its free tier. Here are your options for database and file persistence:

### Option 1: Free Tier (Development & Demos)
* **Relational DB**: SQLite database (`credit_processing.db`) is stored in `/app/data/`.
* **ChromaDB Vector Store**: ChromaDB index is auto-initialized on startup.
* **Uploads**: PAN, Aadhaar, and statements are uploaded to `/app/uploads`.
* Note: On Render's Free tier, all uploaded files and SQLite records are lost whenever the backend restarts or scales down. This is perfect for demonstration and evaluation, but not for production.

### Option 2: Production Tier (Persistent Disk or Postgres DB)
* **Relational DB**: Connect a managed **Render PostgreSQL Database** by setting the `DATABASE_URL` environment variable.
* **Storage Disk**: Attach a **Render Persistent Disk** to the backend service mounted at `/app/data` (standard plans only, starting at $5/month for the disk).

---

## ⚡ Method 1: Automated Deployment using Render Blueprints (Recommended)

This project contains a `render.yaml` file that allows you to deploy all services and configurations in a single click.

### Steps:
1. Push your repository to your GitHub or GitLab account.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click on the **Blueprints** tab in the top navigation bar.
4. Click **New Blueprint Instance**.
5. Connect your GitHub repository.
6. Render will automatically detect the `render.yaml` file.
7. Fill in the required fields:
   * **Service Group Name**: e.g., `credit-application-agent`
   * **`OPENAI_API_KEY`**: Input your OpenAI API Key or your LLM Provider Key.
8. Click **Approve**. Render will build and deploy both services automatically!

---

## ⚡ Method 2: Manual Deployment via Render Dashboard

If you prefer to configure the services manually, follow these step-by-step instructions.

### Step 1: Deploy the Backend Service (`credit-backend`)
1. In the Render Dashboard, click **New +** and select **Web Service**.
2. Connect your repository.
3. Configure the following fields:
   * **Name**: `credit-backend`
   * **Runtime**: `Docker`
   * **Docker Command**: Leave blank (it will use the `CMD` defined in the Dockerfile).
   * **Docker Context**: `.`
   * **Dockerfile Path**: `Dockerfile.backend`
4. Under **Instance Type**, select **Free** (or a higher tier).
5. Click **Advanced** and add the following **Environment Variables**:
   
   | Key | Value | Notes |
   | :--- | :--- | :--- |
   | `ENV` | `production` | Sets execution environment |
   | `DATABASE_URL` | `sqlite:////app/data/credit_processing.db` | Path to DB |
   | `CHROMA_DB_PATH` | `/app/data/chromadb` | Vector store index directory |
   | `KNOWLEDGE_BASE_DIR` | `/app/knowledge_base` | Pre-loaded policy guidelines |
   | `SECRET_KEY` | *[Click 'Generate UUID' or enter a secure random string]* | For security tokens |
   | `OPENAI_API_KEY` | `your-api-key-here` | Key for embeddings and agent LLM |
   | `OPENAI_MODEL` | `meta-llama/llama-3-8b-instruct:free` | Model selection |
   | `OPENAI_API_BASE` | `https://openrouter.ai/api/v1` | Custom endpoint base if using OpenRouter |
   | `PORT` | `8000` | Port uvicorn binds to |
   | `HOST` | `0.0.0.0` | Bind address |
   | `LOG_LEVEL` | `INFO` | Verbosity of logs |

6. Click **Create Web Service**. Wait for the build to finish.
7. Once deployed, note down the internal URL (e.g. `http://credit-backend:8000`) and the public URL (e.g., `https://credit-backend.onrender.com`).

---

### Step 2: Deploy the Frontend Service (`credit-frontend`)
1. In the Render Dashboard, click **New +** and select **Web Service**.
2. Connect the same repository.
3. Configure the following fields:
   * **Name**: `credit-frontend`
   * **Runtime**: `Docker`
   * **Docker Context**: `.`
   * **Dockerfile Path**: `Dockerfile.frontend`
4. Under **Instance Type**, select **Free**.
5. Click **Advanced** and add the following **Environment Variable**:
   
   | Key | Value | Notes |
   | :--- | :--- | :--- |
   | `BACKEND_URL` | `http://credit-backend:8000` | Point to backend service name internally |

   > Setting `BACKEND_URL` to `http://credit-backend:8000` utilizes Render's fast and secure **Private Networking**. If you encounter network issues, you can replace it with your backend's public URL: `https://credit-backend.onrender.com`.

6. Click **Create Web Service**.

---

## 🔍 Verifying the Deployment
1. Navigate to the public URL of your `credit-frontend` (e.g., `https://credit-frontend.onrender.com`).
2. You should see the Streamlit Underwriter Dashboard.
3. Go to the backend dashboard or check logs in the Render console to confirm that connections are active and database tables have initialized successfully.
