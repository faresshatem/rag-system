````markdown
# 🤖 Multi-Agent Enterprise RAG System

> A production-ready **Multi-Agent Retrieval-Augmented Generation (RAG)** platform built with **LangGraph**, **LangChain**, and **FastAPI** to deliver secure, reliable, and source-grounded question answering across enterprise knowledge bases.

---

## 📖 Overview

This project is an enterprise-grade Retrieval-Augmented Generation (RAG) system designed to answer questions over organizational documents using a collaborative multi-agent architecture.

Unlike traditional RAG pipelines, this system adopts a **Plan-and-Execute** workflow powered by **LangGraph**, where specialized AI agents cooperate to retrieve, verify, and synthesize accurate responses while minimizing hallucinations and enforcing domain-level security.

The platform supports multiple LLM providers, hybrid retrieval techniques, role-based access control (RBAC), citation-aware responses, and scalable deployment using Docker.

---

## ✨ Features

### 🤖 Multi-Agent Architecture

- Supervisor Agent
- Query Planning Agent
- Retrieval Agent
- Verification Agent
- Synthesis & Citation Agent

### 🔍 Hybrid Retrieval

- Dense Vector Search
- BM25 Sparse Search
- Reciprocal Rank Fusion (RRF)
- Metadata-aware Retrieval
- Domain-specific Search

### 🛡️ Security

- JWT Authentication
- Role-Based Access Control (RBAC)
- Domain Isolation
- Metadata Filtering
- Secure Agent Delegation

### 🧠 AI Capabilities

- Multi-step Query Planning
- Context Verification
- Automatic Re-query
- Citation-aware Answer Generation
- Multi-LLM Routing

### 📊 Monitoring

- Prometheus Metrics
- Grafana Dashboards
- LLM Judge Evaluation
- Retrieval Performance Monitoring

---

# 🏗️ System Architecture

```text
                        User Query
                             │
                             ▼
                    Supervisor Agent
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
    Planning Agent    Retrieval Agent   Structured Data Agent
                             │
                  Dense + BM25 Retrieval
                             │
                     Reciprocal Rank Fusion
                             │
                             ▼
                   Verification Agent
                             │
                    Context Validation
                             │
                             ▼
                 Synthesis & Citation Agent
                             │
                             ▼
          Final Response + Sources + Confidence
```

---

# 🛠️ Tech Stack

### Backend

- Python 3.12+
- FastAPI
- LangChain
- LangGraph
- SQLAlchemy
- Celery

### AI & Retrieval

- Sentence Transformers
- Qdrant
- BM25
- Reciprocal Rank Fusion (RRF)

### Databases

- PostgreSQL
- Redis
- Qdrant

### Frontend

- React
- Axios
- Framer Motion

### Infrastructure

- Docker
- Docker Compose

### Monitoring

- Prometheus
- Grafana

---

# 📂 Project Structure

```text
rag-system/
│
├── src/
│   ├── agents/
│   ├── retrieval/
│   ├── generation/
│   ├── ingestion/
│   ├── verification/
│   └── api/
│
├── frontend/
├── monitoring/
├── database/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# ⚙️ Getting Started

## 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git
cd rag-system
```

## 2. Create a Virtual Environment

```bash
uv venv
source .venv/bin/activate
```

## 3. Install Dependencies

```bash
uv sync
```

## 4. Configure Environment Variables

Create a `.env` file:

```env
GOOGLE_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=

QDRANT_URL=http://localhost:6333

POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=

REDIS_URL=redis://localhost:6379

OLLAMA_BASE_URL=http://localhost:11434
```

## 5. Start Infrastructure

```bash
docker compose up -d
```

## 6. Run the Backend

```bash
uvicorn main:app --reload
```

## 7. Run the Frontend

```bash
cd frontend
npm install
npm start
```

---

# 🔄 Retrieval Pipeline

```text
User Query
      │
      ▼
Metadata Filter
      │
      ▼
Dense Search (Qdrant)

          +

Sparse Search (BM25)

      │
      ▼
Reciprocal Rank Fusion
      │
      ▼
Verification Agent
      │
      ▼
Synthesis & Citation Agent
      │
      ▼
Grounded Response + Citations
```

---

# 👥 Team Contributions

### Mohaned

- LangGraph State Management
- Supervisor Agent
- Query Planning Agent
- Redis Session Memory

### Maram Mazroa

- Retrieval Agent
- Metadata-aware Retrieval
- Reciprocal Rank Fusion (RRF)
- Verification Agent
- Synthesis & Citation Agent

### Faras

- Chunking Strategy
- Embedding Pipeline
- Celery Background Workers
- LLM Judge Evaluation

### Ali

- FastAPI Backend
- Authentication & RBAC
- REST APIs
- Web Search Agent
- Backend Security

---

# 🚀 Future Improvements

- GitHub Actions CI/CD
- AWS Deployment (ECS/EKS)
- Kubernetes Support
- Terraform Infrastructure
- Streaming Responses
- Multi-modal Document Support
- Long-term Agent Memory
- Advanced Monitoring & Observability

---

# 🤝 Contributing

Contributions are welcome! Feel free to fork the repository, create a feature branch, and submit a pull request.

---

# 📜 License

This project was developed for educational purposes as part of a Software Engineering / AI Engineering team project.

---

# ⭐ Acknowledgements

Special thanks to all team members for their collaboration throughout the design and implementation of this project.
````
