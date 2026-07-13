# Architecture Design

## Core Components

The Loan/Credit Application Processing Agent is composed of a decoupled Frontend (Streamlit) and Backend (FastAPI + LangGraph).

```
   ┌────────────────────────────────────────────────────────┐
   │                       Streamlit                        │
   │                        Frontend                        │
   └───────────────────────────┬────────────────────────────┘
                               │ HTTP
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                        FastAPI                         │
   │                        Backend                         │
   └───────────────────────────┬────────────────────────────┘
                               │ State / Memory
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                       LangGraph                        │
   │                     Decision Agent                     │
   └───────┬───────────────────┬───────────────────┬────────┘
           │                   │                   │
           ▼                   ▼                   ▼
   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
   │  Validation   │   │     Credit    │   │  RAG Policy   │
   │     Tool      │   │   Score Tool  │   │   Retriever   │
   └───────────────┘   └───────────────┘   └───────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
   │     Debt      │   │   Fairness    │   │     Audit     │
   │  Calculator   │   │    Checker    │   │    Logger     │
   └───────────────┘   └───────────────┘   └───────────────┘
```

### Module Breakdown
- **`backend/agents`**: Manages LangGraph workflow nodes, states, and edges.
- **`backend/tools`**: Independent decision support and validation utility tools.
- **`backend/rag`**: Text processing, vector database (ChromaDB/FAISS), and custom retrievers.
- **`backend/database`**: DB connectivity, models, and sessions.
- **`backend/models`**: Pydantic schemas and database entity mappings.
- **`backend/utils`**: Cross-cutting concerns like logging, exceptions, and security.
