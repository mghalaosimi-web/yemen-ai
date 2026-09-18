# Yemen AI v5.3 — Stability, Security & Integration Update

## Completed hardening
- Unified application version to 5.3.0.
- Protected sensitive API routes with authentication and role-based authorization.
- Unified Cookie/Bearer authentication handling.
- Protected datasets, knowledge, dashboard, activities, exports and conversations.
- Scoped user conversation IDs to the authenticated user.
- Preserved existing user passwords on startup; demo users are only created when missing.
- Added production guard for the secret key and environment-driven secure cookies.
- Connected the Intelligence router to the main FastAPI application.
- Removed arbitrary server-path ingestion; ingestion accepts only validated files inside the upload directory.
- Improved UI feedback with toast notifications and active navigation state.
- Retained backward-compatible local development demo accounts.

## Production checklist
1. Set `YEMEN_AI_ENV=production`.
2. Set a strong `YEMEN_AI_SECRET_KEY`.
3. Serve behind HTTPS/reverse proxy.
4. Disable or replace demo accounts.
5. Move SQLite to PostgreSQL when multi-user concurrency grows.
6. Add rate limiting, backups, monitoring and audit retention.

## Current position
This release completes the stabilization bridge between the multi-portal foundation and the full intelligence/training expansion. The next functional work should focus on real embedding models, document extraction pipelines, training workflows, provider configuration and production deployment automation.
