# 🚀 Beyond "It Works On My Machine": Building & Deploying DocuRAG (And the Real Production Battles Faced!)

Building a Retrieval-Augmented Generation (RAG) system locally is exciting. But deploying a decoupled full-stack architecture to production is where the real engineering lessons happen! 🛠️

I’m thrilled to share **DocuRAG** — a production-ready, full-stack AI Document Q&A Assistant featuring **strict page-level citations** and **anti-hallucination guardrails**.

Here is a behind-the-scenes look at the architecture, how I connected the frontend and backend across cloud platforms, the tricky deployment issues I encountered, and how I debugged them. 👇

---

## 🏗️ Architecture & Cloud Infrastructure

To mimic modern enterprise setups, I went with a decoupled microservice architecture:

* **Frontend**: **React + Vite** hosted on **Vercel** with real-time markdown rendering, citation inspection cards, and session history management.
* **Backend**: **FastAPI (Python)** containerized via **Docker** and hosted on **Render**, featuring asynchronous endpoints, sliding-window chunking, and token-bucket rate limiting.
* **Vector Store**: **ChromaDB** with persistent HNSW vector indexing.
* **LLM & Embeddings**: OpenAI `gpt-4o-mini` with `text-embedding-3-small`.

---

## 🔌 Connecting Frontend (Vercel) to Backend (Render)

1. **Client-Side API Layer**: Built a centralized `api.js` client consuming `import.meta.env.VITE_API_URL`.
2. **Environment Synchronization**: Configured `VITE_API_URL=https://ai-document-q-a-assistant-rag-1.onrender.com` in Vercel as a non-sensitive build-time variable.
3. **Cross-Origin Handshake**: Orchestrated HTTP pre-flight (`OPTIONS`) handling in FastAPI so the Vercel single-page application can upload multi-megabyte PDFs and stream answers without security blocks.

---

## ⚡ The Challenges: The "Failed to Fetch" & CORS Battle

Deploying wasn't just a push of a button. Here are the real-world bugs that hit production and how they were resolved:

### 1. Dynamic Vercel Domains vs. Static CORS Policies
* **The Issue**: While the static production domain worked locally, preview deployments (e.g., `frontend-3snsyau3v-anugrah-ajiths-projects.vercel.app`) immediately threw `net::ERR_FAILED 200 (OK)` and `CORS policy: No 'Access-Control-Allow-Origin' header is present`.
* **The Fix**: Hardcoding origins isn't viable in modern CI/CD. In FastAPI, I added wildcard regex matching:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=origins,
      allow_origin_regex=r"https://.*\.vercel\.app",
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  Now, every branch preview and production domain is securely whitelisted on the fly!

### 2. Missing Router Declarations & Deceptive 404s
* **The Issue**: During an iterative configuration update, the bottom router registration block in `main.py` was truncated. Requests to `/api/v1/documents` returned 404. In browsers, unhandled 404s on pre-flight cross-origin requests often manifest deceptively as generic CORS errors.
* **The Fix**: Re-structured the lifespan context manager, reinstated all modular routers (`health_router`, `documents_router`, `chat_router`), and added a global exception handler to guarantee proper JSON telemetry and CORS headers on all HTTP status codes.

### 3. Cloud Cold Starts on Free-Tier Containers
* **The Issue**: Render’s free tier spins containers down after 15 minutes of inactivity, requiring ~40–50 seconds to warm up Uvicorn on initial traffic. If the UI loads immediately, the health-check poll throws a transient *“Failed to fetch”*.
* **The Fix**: Built automatic retry logic into the frontend and verified the backend health endpoint (`/api/v1/health`) via scripted `curl` probes before promoting deployments.

---

## 📊 Benchmark & Evaluation Results (`evaluate.py`)

To ensure reliability, I tested the RAG pipeline against 15 diverse question categories (direct facts, multi-condition retrieval, technical specs, and negative controls):

* 🎯 **Answer Accuracy**: **93.3%**
* 📌 **Citation Verification**: **100.0%** (Every factual claim is backed by `[Source: file.pdf, Page: X]`)
* 🚫 **Strict Negative Rejection**: If the answer isn't in the document, the model explicitly refuses to guess—eliminating hallucinations.
* ⚡ **Average Retrieval Latency**: **~9.3 ms**

---

## 💡 Key Takeaways for Developers

1. **Decoupled CI/CD requires flexible CORS**: Always account for dynamic preview URLs when separating frontend (Vercel) and backend (Render/AWS/GCP).
2. **Pre-flight failures can mask routing bugs**: If CORS fails, check your server's routing table—missing endpoints often drop headers.
3. **Plan for cold-start latency**: Provide clear visual feedback in the UI when cloud services are waking up.

---

### 🔗 Try It Out!
* 🌐 **Live Web App**: https://frontend-five-plum-90.vercel.app
* 💻 **GitHub Repository**: https://github.com/Anugrah-Ajith/AI-Document-Q-A-Assistant-RAG-.git
* 📄 **Technical Case Study Brief (PDF attached)**: See the attached document in this post for the detailed post-mortem report!

Would love to hear your thoughts, feedback, or how you handle CORS and cold starts in your projects! 👇

#SoftwareEngineering #Python #FastAPI #ReactJS #ArtificialIntelligence #RAG #MachineLearning #Docker #Vercel #CloudComputing #DevOps #WebDevelopment #OpenAI #ChromaDB
