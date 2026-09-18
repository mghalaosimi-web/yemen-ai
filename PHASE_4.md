# Yemen AI v5.4 — AI Training & Knowledge Engine

## Completed
- Unified user chat with the Intelligence Engine.
- RAG retrieval connected to the production chat endpoint.
- Dataset upload → explicit secure ingestion workflow.
- Ingestion job tracking in SQLite.
- TXT, MD, CSV and JSON ingestion supported.
- Source chips returned with RAG responses.
- AI provider abstraction preserved: Echo, Ollama, OpenAI-compatible.

## Run
1. Install requirements: `py -3.13 -m pip install -r requirements.txt`
2. Start: `py -3.13 launcher.py`
3. Login, open Training, upload TXT/MD/CSV/JSON, click Build Knowledge, then ask questions in User portal.

## Provider configuration
Default is safe local Echo provider. Configure environment variables for Ollama or an OpenAI-compatible endpoint before production use.
