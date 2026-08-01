````markdown
# 🤖 Multi-Agent Enterprise RAG System

> A production-ready **Multi-Agent Retrieval-Augmented Generation (RAG)** platform that combines **LangGraph**, **LangChain**, and **FastAPI** to deliver secure, explainable, and citation-aware question answering across enterprise knowledge bases.

---

# 📖 Overview

This project is an enterprise-grade Retrieval-Augmented Generation (RAG) system designed to answer questions over organizational documents using a collaborative multi-agent architecture.

Unlike traditional RAG systems, this platform follows a **Plan-and-Execute** workflow powered by **LangGraph**, where specialized agents collaborate to retrieve, verify, and synthesize reliable responses while enforcing domain-level security and minimizing hallucinations.

The system combines **hybrid retrieval**, **multi-agent reasoning**, **role-based access control (RBAC)**, **citation-aware generation**, and **web search fallback** to provide accurate and trustworthy answers.

---

# ✨ Features

## 🤖 Multi-Agent Architecture

- Supervisor Agent
- Query Planning Agent
- Retrieval Agent
- Verification Agent
- Synthesis & Citation Agent
- Web Search Agent

---

## 🔍 Hybrid Retrieval

- Dense Vector Search (Qdrant)
- BM25 Sparse Search
- Reciprocal Rank Fusion (RRF)
- Metadata-aware Retrieval
- Domain-based Search

---

## 🌐 Intelligent Web Search

- Automatically searches trusted web sources when the requested information is unavailable in the internal knowledge base.
- Prevents incomplete answers by combining enterprise knowledge with external information when appropriate.

---

## 🛡️ Security

- JWT Authentication
- Role-Based Access Control (RBAC)
- Metadata Filtering
- Domain Isolation
- Secure Agent Delegation

---

## 🧠 AI Capabilities

- Multi-step Query Planning
- Context Verification
- Automatic Re-query
- Citation-aware Response Generation
- Multi-LLM Support
- Source Attribution

---

## 📊 Monitoring

- Prometheus Metrics
- Grafana Dashboards
- LLM Judge Evaluation
- System Performance Monitoring

---

# 🏗️ System Architecture

```text
                              User Query
                                   │
                                   ▼
                          Supervisor Agent
                                   │
         ┌───────────────┬───────────────┬────────────────┐
         ▼               ▼               ▼                ▼
 Query Planning     Retrieval      Web Search      Verification
     Agent            Agent           Agent            Agent
         │               │               │
         │         Dense + BM25          │
         │             Search            │
         │               │               │
         └───────────────┴──────┬────────┘
                                ▼
                   Reciprocal Rank Fusion (RRF)
                                │
                                ▼
                  Synthesis & Citation Agent
                                │
                                ▼
           Final Response + Sources + Confidence
```

---

# 🛠️ Tech Stack

## Backend

- Python 3.12+
- FastAPI
- LangChain
- LangGraph
- SQLAlchemy
- Celery

## AI & Retrieval

- Sentence Transformers
- Qdrant
- BM25
- Reciprocal Rank Fusion (RRF)
- Tavily Web Search

## Databases

- PostgreSQL
- Redis
- Qdrant

## Frontend

- React
- Axios
- Framer Motion
- Lucide Icons

## Infrastructure

- Docker
- Docker Compose

## Monitoring

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
│   ├── web_search/
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

## Clone the Repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git
cd rag-system
```

## Create Virtual Environment

```bash
uv venv
source .venv/bin/activate
```

## Install Dependencies

```bash
uv sync
```

## Configure Environment Variables

Create a `.env` file:

```env
GOOGLE_API_KEY=
OPENAI_API_KEY=
GROQ_API_KEY=
TAVILY_API_KEY=

QDRANT_URL=http://localhost:6333

POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=

REDIS_URL=redis://localhost:6379

OLLAMA_BASE_URL=http://localhost:11434
```

## Start Infrastructure

```bash
docker compose up -d
```

## Run Backend

```bash
uvicorn main:app --reload
```

## Run Frontend

```bash
cd frontend
npm install
npm start
```

---

# 🔄 Retrieval Workflow

```text
                    User Query
                         │
                         ▼
                 Query Planning Agent
                         │
                         ▼
                Metadata Filtering
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
 Dense Vector Search             BM25 Search
          │                             │
          └──────────────┬──────────────┘
                         ▼
             Reciprocal Rank Fusion
                         │
                         ▼
              Verification Agent
                         │
              Context Valid?
                 │             │
               Yes            No
                │              │
                ▼              ▼
      Synthesis Agent     Web Search Agent
                │              │
                └──────┬───────┘
                       ▼
          Final Answer with Citations
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

- Document Chunking Strategy
- Embedding Pipeline
- Celery Background Workers
- LLM Judge Evaluation

### Ali

- FastAPI Backend Development
- REST API Design & Implementation
- Authentication & JWT Authorization
- Role-Based Access Control (RBAC)
- Backend Security
- Web Search Agent

---

# 🚀 Future Improvements

- GitHub Actions CI/CD
- AWS Deployment (ECS / EKS)
- Kubernetes Support
- Terraform Infrastructure
- Streaming Responses
- Multi-modal Document Support
- Long-term Agent Memory
- Advanced Observability

---

# 🤝 Contributing

Contributions are welcome! Feel free to fork the repository, open issues, or submit pull requests.

---

# 📜 License

This project was developed for educational purposes as part of a Software Engineering & AI Engineering team project.

---

# ⭐ Acknowledgements

Special thanks to all team members for their collaboration, dedication, and contributions throughout the design and implementation of this project.
````
