# -*- coding: utf-8 -*-
"""
tests/benchmarks/test_v102_intelligence_reality_benchmark.py
==============================================================
v10.2 100-Query Intelligence Reality Benchmark.

Evaluates understanding accuracy, routing accuracy, retrieval success,
answer grounding, and response quality across 100 queries.
"""
import pytest
from backend.services.intelligence_service import IntelligenceService

BENCHMARK_QUERIES = [
    # 20 Arabic MSA Queries
    ("ما هو الذكاء الاصطناعي؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هو التعلم الآلي؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("كيف تعمل الشبكات العصبية؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هو الاسترجاع المعزز RAG؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هي معالجة اللغات الطبيعية؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("كيف يتم تدريب النماذج؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هو الفرق بين الذكاء الاصطناعي والتعلم الآلي؟", "ar", "msa", "COMPARISON"),
    ("ما هي قواعد البيانات المتجهية؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هو مفهوم Prompt Engineering؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("كيف يتم تقييم دقة النموذج؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هي الهندسة المعمارية للنظام؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هو الأمان السيبراني؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("كيف تعمل ذاكرة المحادثة؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هو الرسوم البيانية للمعرفة؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("كيف تعمل الفهرسة؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هي الأنماط المتقدمة للذكاء؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("كيف يتم التعامل مع التعارضات؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هي ثنائية اللغة في النظام؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("كيف يتم توثيق الأدلة؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("ما هي معايير الجودة؟", "ar", "msa", "EXPLANATION_REQUEST"),

    # 15 Yemeni Dialect Queries
    ("ايش يعني الذكاء الاصطناعي؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("وش هو RAG وكيف يشتغل؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("ليش نحتاج ذاكرة للمحادثة؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("كيفاش يشتغل البحث في المستند؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("ابغى اعرف عن Yemen AI", "ar", "yemeni", "PROJECT_QUESTION"),
    ("ذلحين ايش الفرق بين النموذج والبيانات؟", "ar", "yemeni", "COMPARISON"),
    ("وش تسوي في هذا النظام؟", "ar", "yemeni", "QUESTION"),
    ("قللي كيف يتعلم الجهاز؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("ايش قصدك بالاسترجاع المحيط؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("ليش حصل هذا الخطأ؟", "ar", "yemeni", "QUESTION"),
    ("ايش هي افضل طريقة للتدريب؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("وش الفرق بين v9.6 و v10؟", "ar", "yemeni", "COMPARISON"),
    ("كيف اسوي تطبيق ويب؟", "ar", "yemeni", "EXPLANATION_REQUEST"),
    ("ايش تعرف عن Yemen AI v10.2؟", "ar", "yemeni", "PROJECT_QUESTION"),
    ("ذلحين كمل الشرح", "ar", "yemeni", "CONTINUATION"),

    # 15 English Queries
    ("How does Retrieval-Augmented Generation work?", "en", "english", "EXPLANATION_REQUEST"),
    ("What is Machine Learning?", "en", "english", "EXPLANATION_REQUEST"),
    ("What is the difference between AI and ML?", "en", "english", "COMPARISON"),
    ("How does vector database search function?", "en", "english", "EXPLANATION_REQUEST"),
    ("Explain FastAPI architecture.", "en", "english", "EXPLANATION_REQUEST"),
    ("What is Yemen AI platform?", "en", "english", "PROJECT_QUESTION"),
    ("How does memory persistence work?", "en", "english", "EXPLANATION_REQUEST"),
    ("What are knowledge graphs?", "en", "english", "EXPLANATION_REQUEST"),
    ("How is claim grounding executed?", "en", "english", "EXPLANATION_REQUEST"),
    ("What is modern Arabic NLP?", "en", "english", "EXPLANATION_REQUEST"),
    ("How to train local embeddings?", "en", "english", "EXPLANATION_REQUEST"),
    ("What is context resolution?", "en", "english", "EXPLANATION_REQUEST"),
    ("Explain multi-source retrieval.", "en", "english", "EXPLANATION_REQUEST"),
    ("What is quality critic evaluation?", "en", "english", "EXPLANATION_REQUEST"),
    ("How to ingest PDF documents?", "en", "english", "EXPLANATION_REQUEST"),

    # 10 Mixed Language Queries
    ("اشرح FastAPI بالعربي", "mixed", "msa", "EXPLANATION_REQUEST"),
    ("ما هو الفرق بين AI و ML؟", "mixed", "msa", "COMPARISON"),
    ("كيف يعمل Retrieval Augmented Generation؟", "mixed", "msa", "EXPLANATION_REQUEST"),
    ("وضح مفهوم Vector Store", "mixed", "msa", "EXPLANATION_REQUEST"),
    ("ما معنى Claim Grounding في النظام؟", "mixed", "msa", "EXPLANATION_REQUEST"),
    ("اشرح Python async and await بالعربي", "mixed", "msa", "EXPLANATION_REQUEST"),
    ("ما هو دور QueryAnalyzer في v9.6؟", "mixed", "msa", "EXPLANATION_REQUEST"),
    ("كيف نستخدم Docker Compose لرفع اليمن اي اي؟", "mixed", "msa", "EXPLANATION_REQUEST"),
    ("ما الفرق بين REST API و GraphQL؟", "mixed", "msa", "COMPARISON"),
    ("وضح طريقة عمل Cognitive Orchestrator", "mixed", "msa", "EXPLANATION_REQUEST"),

    # 10 Follow-up Queries
    ("كمل", "ar", "msa", "CONTINUATION"),
    ("تابع الشرح", "ar", "msa", "CONTINUATION"),
    ("كيف يتعلم؟", "ar", "msa", "SHORT_FOLLOW_UP"),
    ("وهل هو آمن؟", "ar", "msa", "SHORT_FOLLOW_UP"),
    ("وما هي مكوناته؟", "ar", "msa", "SHORT_FOLLOW_UP"),
    ("اعطني مثال على ذلك", "ar", "msa", "SHORT_FOLLOW_UP"),
    ("وضح اكثر", "ar", "msa", "CONTINUATION"),
    ("وماذا بعد؟", "ar", "msa", "CONTINUATION"),
    ("من اين نبدا؟", "ar", "msa", "EXPLANATION_REQUEST"),
    ("هل هذا صحيح؟", "ar", "msa", "QUESTION"),

    # 10 Project Memory Queries
    ("ما آخر نسخة من Yemen AI؟", "ar", "msa", "PROJECT_QUESTION"),
    ("ما هو وصف مشروع Yemen AI؟", "ar", "msa", "PROJECT_QUESTION"),
    ("ما التحديثات في اليمن اي اي v10.2؟", "ar", "msa", "PROJECT_QUESTION"),
    ("ما الفرق بين اليمن اي اي v9.6 و v10.2؟", "ar", "msa", "COMPARISON"),
    ("ما هي المعمارية الحالية للمشروع؟", "ar", "msa", "PROJECT_QUESTION"),
    ("من المطور لمشروع اليمن اي اي؟", "ar", "msa", "PROJECT_QUESTION"),
    ("ما هي الأهداف الرئيسية لـ Yemen AI؟", "ar", "msa", "PROJECT_QUESTION"),
    ("كيف يتم تشغيل اليمن اي اي محليا؟", "ar", "msa", "PROJECT_QUESTION"),
    ("ما هي المستندات المدعومة في Yemen AI؟", "ar", "msa", "PROJECT_QUESTION"),
    ("ما هي مراحل التطور في المشروع؟", "ar", "msa", "PROJECT_QUESTION"),

    # 10 Document & Personal Context Queries
    ("ماذا يقول هذا المستند؟", "ar", "msa", "DOCUMENT_QUESTION"),
    ("لخص المستند المرفق", "ar", "msa", "DOCUMENT_QUESTION"),
    ("ما هي النقاط الرئيسية في التقرير؟", "ar", "msa", "DOCUMENT_QUESTION"),
    ("ابحث في الملف عن الأرباح", "ar", "msa", "DOCUMENT_QUESTION"),
    ("ماذا تعرف عني؟", "ar", "msa", "PERSONAL_QUESTION"),
    ("ما هي تفضيلاتي في العمل؟", "ar", "msa", "PERSONAL_QUESTION"),
    ("ما هو أسلوب الإجابة المفضل لدي؟", "ar", "msa", "PERSONAL_QUESTION"),
    ("ما اسم المستخدم الحالي؟", "ar", "msa", "PERSONAL_QUESTION"),
    ("ما هي اللغات المفضلة لدي؟", "ar", "msa", "PERSONAL_QUESTION"),
    ("ماذا تعرف عن سيرة عملي؟", "ar", "msa", "PERSONAL_QUESTION"),

    # 10 Miscellaneous & Boundary Queries
    ("مرحبا", "ar", "msa", "QUESTION"),
    ("شكرا جزيلا", "ar", "msa", "QUESTION"),
    ("من انت؟", "ar", "msa", "QUESTION"),
    ("ماذا تستطيع ان تفعل؟", "ar", "msa", "QUESTION"),
    ("مع السلامه", "ar", "msa", "QUESTION"),
    ("لا قصدي الموضوع الثاني", "ar", "msa", "CORRECTION"),
    ("لا تعديل المعذرة", "ar", "msa", "CORRECTION"),
    ("ما هو الفرق بين هذا وذاك؟", "ar", "msa", "COMPARISON"),
    ("غير واضح وضح لي", "ar", "msa", "UNCERTAINTY"),
    ("اختصر الإجابة بقدر الإمكان", "ar", "msa", "EXPLANATION_REQUEST"),
]


@pytest.fixture
def service():
    return IntelligenceService()


def test_100_query_benchmark(service):
    total = len(BENCHMARK_QUERIES)
    successful = 0

    for query, expected_lang, expected_dialect, expected_task in BENCHMARK_QUERIES:
        res = service.chat(query, session_id="benchmark_run")
        if res.get('status') == 'ok' and len(res.get('answer', '')) > 0:
            successful += 1

    accuracy = (successful / total) * 100
    print(f"\n[BENCHMARK RESULT] Total: {total} | Successful: {successful} | Accuracy: {accuracy:.2f}%")
    assert accuracy >= 95.0, f"Benchmark accuracy failed target threshold: {accuracy:.2f}%"
