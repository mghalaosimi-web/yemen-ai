# Yemen AI — Phase 3 Intelligence Layer

This upgrade adds a real intelligence architecture while preserving the existing v2 project.

## Added
- Provider abstraction
- Local fallback provider
- Ollama provider
- OpenAI-compatible provider
- RAG service
- Chunking pipeline
- Deterministic local embeddings
- Persistent JSON vector store
- Document ingestion
- Retrieval-aware chat prompt
- Intelligence API routes
- RAG tests

## New API
- GET /api/intelligence/health
- POST /api/intelligence/chat
- POST /api/intelligence/ingest

## Provider selection
Copy `.env.example` to `.env` and select:

AI_PROVIDER=echo

For local Ollama:
AI_PROVIDER=ollama

For an OpenAI-compatible API:
AI_PROVIDER=openai-compatible

## Important architecture note
The local embedding implementation is dependency-light and intended as a stable Phase 3 baseline.
For production scale, replace it with a semantic embedding model and migrate the JSON store to a vector database.
