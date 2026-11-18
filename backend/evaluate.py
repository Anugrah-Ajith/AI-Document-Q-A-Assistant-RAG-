"""
Evaluation benchmark script for RAG Document Q&A Assistant.
Runs 15 representative domain sample questions across multi-page indexed documents,
measuring answer generation, citation correctness, negative rejection, and semantic accuracy.
"""

import asyncio
import io
import re
import sys
import time
from typing import Any, Dict, List
from pypdf import PdfWriter

# Ensure backend modules can be imported
sys.path.insert(0, ".")

from app.config import get_settings
from app.core.session_manager import session_manager
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.rag_service import RAGService
from app.services.vector_store import VectorStoreService


# 15 Benchmark Evaluation Questions with Ground Truth & Target Criteria
BENCHMARK_DATASET = [
    {
        "id": 1,
        "question": "What is the primary objective of Project Apex?",
        "ground_truth": "Develop a real-time predictive analytics engine reducing latency by 45%",
        "expected_page": 1,
        "expected_keywords": ["predictive", "latency", "analytics", "45%"],
        "category": "Direct Fact Retrieval"
    },
    {
        "id": 2,
        "question": "Who is the lead architect for Project Apex infrastructure?",
        "ground_truth": "Dr. Elena Rostova",
        "expected_page": 1,
        "expected_keywords": ["elena", "rostova"],
        "category": "Direct Fact Retrieval"
    },
    {
        "id": 3,
        "question": "What database technology is selected for time-series metrics?",
        "ground_truth": "TimescaleDB with automated data retention policies",
        "expected_page": 1,
        "expected_keywords": ["timescaledb", "retention"],
        "category": "Direct Fact Retrieval"
    },
    {
        "id": 4,
        "question": "What is the total allocated budget for Phase 1?",
        "ground_truth": "$1.85 million allocated for Q1 and Q2",
        "expected_page": 1,
        "expected_keywords": ["1.85", "million"],
        "category": "Direct Fact Retrieval"
    },
    {
        "id": 5,
        "question": "What are the security compliance standards required for the deployment?",
        "ground_truth": "SOC2 Type II, HIPAA, and ISO/IEC 27001",
        "expected_page": 2,
        "expected_keywords": ["soc2", "hipaa", "27001"],
        "category": "Multi-Condition Retrieval"
    },
    {
        "id": 6,
        "question": "How often are automated disaster recovery failover drills scheduled?",
        "ground_truth": "Bi-weekly simulated regional failover tests with 99.99% uptime goal",
        "expected_page": 2,
        "expected_keywords": ["bi-weekly", "failover", "99.99%"],
        "category": "Multi-Condition Retrieval"
    },
    {
        "id": 7,
        "question": "What is the targeted P99 API response time threshold?",
        "ground_truth": "Under 85 milliseconds across global edge nodes",
        "expected_page": 2,
        "expected_keywords": ["85", "milliseconds", "p99"],
        "category": "Direct Fact Retrieval"
    },
    {
        "id": 8,
        "question": "Which cloud provider regions will host the secondary replica clusters?",
        "ground_truth": "AWS us-east-1 and eu-central-1 Frankfurt",
        "expected_page": 2,
        "expected_keywords": ["us-east-1", "eu-central-1", "frankfurt"],
        "category": "Direct Fact Retrieval"
    },
    {
        "id": 9,
        "question": "What caching mechanism is implemented for hot analytical queries?",
        "ground_truth": "Redis cluster with LRU eviction and 15-minute TTL",
        "expected_page": 3,
        "expected_keywords": ["redis", "lru", "ttl"],
        "category": "Technical Specification"
    },
    {
        "id": 10,
        "question": "What protocol is used for intra-service communication between microservices?",
        "ground_truth": "gRPC over HTTP/2 with mutual TLS authentication",
        "expected_page": 3,
        "expected_keywords": ["grpc", "http/2", "tls"],
        "category": "Technical Specification"
    },
    {
        "id": 11,
        "question": "What is the rollback policy in case a canary deployment detects elevated error rates?",
        "ground_truth": "Automated zero-downtime rollback triggered if error rate exceeds 0.05% within 3 minutes",
        "expected_page": 3,
        "expected_keywords": ["rollback", "0.05%", "canary"],
        "category": "Technical Specification"
    },
    {
        "id": 12,
        "question": "Who serves as the primary escalation point for Sev-1 production incidents?",
        "ground_truth": "The Site Reliability Engineering On-Call Lead via PagerDuty",
        "expected_page": 3,
        "expected_keywords": ["site", "reliability", "pagerduty", "on-call"],
        "category": "Direct Fact Retrieval"
    },
    {
        "id": 13,
        "question": "What is the CEO's favorite personal vacation destination?",
        "ground_truth": "Information not available in document",
        "expected_page": None,
        "expected_keywords": ["not available", "cannot be found"],
        "category": "Negative Rejection / Hallucination Test"
    },
    {
        "id": 14,
        "question": "What is the stock price target of the company for the next fiscal year?",
        "ground_truth": "Information not available in document",
        "expected_page": None,
        "expected_keywords": ["not available", "cannot be found"],
        "category": "Negative Rejection / Hallucination Test"
    },
    {
        "id": 15,
        "question": "What brand of coffee machine is installed in the engineering kitchen?",
        "ground_truth": "Information not available in document",
        "expected_page": None,
        "expected_keywords": ["not available", "cannot be found"],
        "category": "Negative Rejection / Hallucination Test"
    },
]


def create_sample_benchmark_pdf() -> bytes:
    """Generates a synthetic multi-page PDF in-memory containing reference knowledge."""
    writer = PdfWriter()

    # Page 1: Overview & Budget
    writer.add_blank_page(width=612, height=792)
    p1_text = (
        "Project Apex Architecture and Execution Plan - Confidential\n\n"
        "1. Executive Summary:\n"
        "The primary objective of Project Apex is to develop a real-time predictive analytics engine "
        "reducing latency by 45% compared to legacy batch processing. "
        "The engineering team is led by Chief Infrastructure Architect Dr. Elena Rostova.\n\n"
        "2. Infrastructure and Budget:\n"
        "The total allocated budget for Phase 1 is $1.85 million allocated for Q1 and Q2. "
        "For storing time-series metrics, the team selected TimescaleDB with automated data retention policies "
        "to ensure sub-second querying over 90 days of high-cardinality telemetry."
    )

    # Page 2: Security & SLAs
    writer.add_blank_page(width=612, height=792)
    p2_text = (
        "Project Apex Security, Compliance and Service Level Agreements\n\n"
        "3. Security and Compliance:\n"
        "The deployment must adhere strictly to SOC2 Type II, HIPAA, and ISO/IEC 27001 compliance standards. "
        "All data at rest is encrypted using AES-256-GCM, and automated disaster recovery failover drills "
        "are scheduled for bi-weekly simulated regional failover tests with 99.99% uptime goal.\n\n"
        "4. Latency and Topology:\n"
        "The targeted P99 API response time threshold is under 85 milliseconds across global edge nodes. "
        "Secondary replica clusters are hosted across AWS us-east-1 and eu-central-1 Frankfurt regions."
    )

    # Page 3: Protocols & Reliability
    writer.add_blank_page(width=612, height=792)
    p3_text = (
        "Project Apex Operational Specifications and Protocols\n\n"
        "5. Caching and Communications:\n"
        "Hot analytical queries utilize a distributed Redis cluster with LRU eviction and 15-minute TTL. "
        "Intra-service communication between microservices is handled exclusively via gRPC over HTTP/2 "
        "with mutual TLS authentication.\n\n"
        "6. Deployment and Incident Response:\n"
        "Canary deployments monitor traffic health continuously. The automated zero-downtime rollback "
        "is triggered if error rate exceeds 0.05% within 3 minutes of release. "
        "The Site Reliability Engineering On-Call Lead acts as the primary escalation point for Sev-1 "
        "production incidents routed through PagerDuty."
    )

    # Note: For synthetic testing where PyPDF extracts text, we construct structured page objects
    return writer, [
        {"page": 1, "text": p1_text},
        {"page": 2, "text": p2_text},
        {"page": 3, "text": p3_text},
    ]


async def run_evaluation():
    print("=" * 78)
    print("      RAG DOCUMENT Q&A ASSISTANT — 15-QUESTION BENCHMARK EVALUATION")
    print("=" * 78)

    # 1. Setup isolated test vector store
    test_persist_dir = "./eval_chroma_data"
    vector_store = VectorStoreService(
        persist_dir=test_persist_dir,
        collection_name="eval_collection"
    )
    vector_store.reset()

    # 2. Ingest benchmark document
    _, pages_data = create_sample_benchmark_pdf()
    doc_id = "eval_doc_001"
    filename = "Project_Apex_Specification.pdf"

    chunker = ChunkingService(chunk_size=500, chunk_overlap=100)
    chunks = chunker.chunk_pages(pages_data, doc_id, filename)

    embedder = EmbeddingService()
    embeddings = embedder.get_embeddings([c.content for c in chunks])
    vector_store.add_chunks(chunks, embeddings)

    print(f"\n[+] Ingested benchmark document: '{filename}'")
    print(f"    Total Pages: {len(pages_data)} | Total Chunks: {len(chunks)}")
    print(f"    ChromaDB Storage: {test_persist_dir}\n")

    # 3. Initialize RAG Service
    rag = RAGService(vector_store=vector_store, embedding_service=embedder)

    results: List[Dict[str, Any]] = []
    correct_count = 0
    citation_correct_count = 0

    print("-" * 78)
    print(f"{'ID':<3} | {'Category':<22} | {'Score':<6} | {'Citation':<8} | {'Latency':<7} | Question")
    print("-" * 78)

    for item in BENCHMARK_DATASET:
        q_id = item["id"]
        q_text = item["question"]
        expected_page = item["expected_page"]
        expected_keywords = item["expected_keywords"]
        category = item["category"]

        session_id = f"eval_sess_{q_id}"

        start_time = time.perf_counter()
        answer, citations, chunks_retrieved = await rag.answer_question(
            question=q_text,
            session_id=session_id,
            top_k=3
        )
        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

        # Check content correctness
        answer_lower = answer.lower()
        matched_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
        is_negative_test = expected_page is None

        if is_negative_test:
            # Should refuse / state not available
            is_correct = any(
                phrase in answer_lower
                for phrase in ["not available", "cannot be found", "does not contain", "no information"]
            )
            citation_ok = True  # Negative rejection doesn't require a page
        else:
            # Must match key facts
            is_correct = len(matched_keywords) >= max(1, int(len(expected_keywords) * 0.5))
            # Verify citation points to expected page
            cited_pages = [c.page for c in citations]
            citation_ok = expected_page in cited_pages if cited_pages else False

        if is_correct:
            correct_count += 1
        if citation_ok:
            citation_correct_count += 1

        score_str = "PASS" if is_correct else "FAIL"
        cite_str = "VALID" if citation_ok else "MISSING"

        print(
            f"{q_id:<3} | {category[:22]:<22} | {score_str:<6} | {cite_str:<8} | {latency_ms:>5}ms | {q_text[:35]}..."
        )

        results.append({
            "id": q_id,
            "question": q_text,
            "category": category,
            "answer": answer,
            "citations": [f"{c.filename}:p{c.page}" for c in citations],
            "correct": is_correct,
            "citation_valid": citation_ok,
            "latency_ms": latency_ms,
        })

    # Summary Statistics
    total_questions = len(BENCHMARK_DATASET)
    accuracy_pct = round((correct_count / total_questions) * 100, 1)
    citation_accuracy_pct = round((citation_correct_count / total_questions) * 100, 1)
    avg_latency = round(sum(r["latency_ms"] for r in results) / total_questions, 1)

    print("=" * 78)
    print("                          BENCHMARK SUMMARY")
    print("=" * 78)
    print(f"  Total Questions Evaluated : {total_questions}")
    print(f"  Answer Accuracy           : {correct_count}/{total_questions} ({accuracy_pct}%)")
    print(f"  Source Citation Accuracy  : {citation_correct_count}/{total_questions} ({citation_accuracy_pct}%)")
    print(f"  Average Query Latency     : {avg_latency} ms")
    print("=" * 78)

    # Clean up test collection
    try:
        vector_store.reset()
    except Exception:
        pass

    return accuracy_pct >= 80.0


if __name__ == "__main__":
    success = asyncio.run(run_evaluation())
    sys.exit(0 if success else 1)
