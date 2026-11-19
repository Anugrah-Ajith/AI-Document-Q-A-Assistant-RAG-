# 🚀 Built & Deployed an End-to-End Production RAG System: AI Document Q&A Assistant!

Excited to share my latest project: **DocuRAG** — a full-stack, enterprise-grade Retrieval-Augmented Generation (RAG) assistant designed for instant, verifiable document question-answering with **strict page-level citations**! 📄⚡

---

### 💡 Why I Built This
Traditional LLM search often hallucinates or returns unverified claims. I wanted to build an architecture that guarantees **grounded answers** backed directly by sources:
- Every factual response cites `[Source: document.pdf, Page: X]` with clickable source inspection cards.
- **Strict Negative Rejection**: If the document doesn't contain the answer, the model refuses to speculate, preventing hallucinations.

---

### 🛠️ Architecture & Tech Stack
- **Backend**: **FastAPI** (Python 3.14) with async endpoints, clean modular architecture (Routers, Services, Schemas), and strict type hinting.
- **Vector Database**: **ChromaDB** with persistent HNSW vector indexing and hybrid re-ranking.
- **Text Processing & Chunking**: Custom sliding-window chunking engine with configurable overlap and PDF extraction (`pypdf`).
- **Retrieval Engine**: Hybrid search combining dense semantic embeddings + lexical intent re-ranking for pinpoint accuracy on entity & identity queries.
- **Security & Scale**: Token bucket rate limiting (per session/IP) with custom 429 backoff headers.
- **Frontend**: **React + Vite** with a sleek dark-themed interface, drag-and-drop document upload, real-time citation cards, and session history management.
- **DevOps**: Multi-stage **Docker** & **docker-compose** for one-command containerized deployment.

---

### 📊 Benchmark & Evaluation (`evaluate.py`)
To ensure high accuracy and zero regressions, I built an automated evaluation pipeline running 15 diverse question categories (direct facts, multi-condition retrieval, technical specs, and negative controls):
- **Answer Accuracy**: **93.3%**
- **Citation Verification**: **100.0%**
- **Average Query Latency**: **~9.3 ms**

---

🔗 **Project Links**:
- 🌐 Live Web App (Vercel): https://frontend-five-plum-90.vercel.app
- 💻 GitHub Repository: https://github.com/Anugrah-Ajith/AI-Document-Q-A-Assistant-RAG-.git
- ⚡ Local Server: `http://127.0.0.1:8000`

Would love to hear your feedback, thoughts on RAG architectures, or suggestions! 👇

#Python #FastAPI #MachineLearning #ArtificialIntelligence #RAG #NLP #ChromaDB #Docker #FullStack #SoftwareEngineering #GenerativeAI #ReactJS
