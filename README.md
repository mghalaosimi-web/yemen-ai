# Yemen AI v9.5 — Professional UI Integration

## Current release focus
This release starts from the existing v5.5 codebase and upgrades the live application interface without replacing the backend architecture.

- Complete visual system for dark and light themes.
- Responsive sidebar with desktop collapse and mobile drawer behavior.
- Redesigned login, dashboard, AI assistant, training/data, and developer pages.
- Preserved confirmation dialogs for logout and knowledge-building actions.
- Preserved API integration, authentication, role gates, and backend behavior.
- Removed legacy duplicate root UI folders to avoid editing the wrong interface.
- Automated validation: 18 tests passing.

---

# Yemen AI — Final Development Foundation v4.0

واجهة ومنصة متعددة البوابات: المستخدم، التدريب، المطور، ولوحة التحكم.

## التشغيل
```bash
python -m pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```
ثم افتح `http://127.0.0.1:8000`.

## حسابات التطوير
- admin / YemenAI2026!
- developer / YemenAI2026!
- trainer / YemenAI2026!
- user / YemenAI2026!

> غيّر كلمات المرور و `YEMEN_AI_SECRET_KEY` قبل أي نشر عام.

## الاختبار
```bash
pytest -q
```

## ما تم إنجازه في v4
- توحيد نقطة تشغيل التطبيق.
- إصلاح طبقة الاختبارات المتضاربة.
- JWT للمصادقة وتسجيل الدخول.
- صلاحيات للأدوار.
- تحقق Pydantic للمدخلات.
- رفع ملفات بمسارات آمنة وحدود حجم وأنواع مسموحة.
- SQLite persistence.
- Knowledge retrieval + conversations.
- CSV activity export.
- Health endpoint.
- واجهات البوابات الموجودة في المشروع.


## v5.2 Delivery Update
- Redesigned responsive UI with Light/Dark mode and Arabic/English direction toggle.
- Dashboard, AI Assistant, Training, and Developer pages redesigned as a unified product system.
- Demo accounts are synchronized on startup to prevent stale SQLite credentials from blocking access.
- Added UI smoke test.

### Windows quick start
Double-click `RUN_YEMEN_AI.bat`. It installs missing dependencies using Python 3.13 and launches the application automatically.

## v7.0 Intelligence Core
- AI provider layer: Echo fallback, Ollama, OpenAI-compatible API.
- RAG pipeline with relevance filtering and source metadata.
- Intelligence health endpoint and operational/degraded response states.
- Added intelligence contract tests.

Configure `.env` values before using a real model provider.

## v7.2 Model Control Center
- مركز تحكم بالمزود والنموذج من بوابة المطور.
- تبديل Echo / Ollama / OpenAI-compatible API.
- إعادة تحميل المحرك دون إعادة بناء المشروع.
- مفاتيح API لا تُحفظ في قاعدة البيانات؛ استخدم `AI_API_KEY` في البيئة.

## v7.3 Seed Knowledge
A structured initial knowledge library is included under `knowledge_seed/`. Use the Training Engine to ingest and index these files.


## v8.9 — Document Research Workspace
Multi-document evidence comparison, page-aware outlines, and stricter evidence-linked citations.
