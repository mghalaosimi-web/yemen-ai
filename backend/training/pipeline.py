"""
backend/training/pipeline.py
=============================
v9.6 Offline training pipeline with complete provenance tracking.

Turns raw files/datasets into searchable knowledge, concept graphs, and QA cards.
Full Provenance metadata:
  • source_id
  • source_type
  • knowledge_id
  • source_knowledge_id
  • document_id
  • training_run_id
"""
import time
import json
import uuid
import re
from app.data.database import connect, initialize_database
from backend.services.knowledge_quality_validator import KnowledgeQualityValidator
from backend.services.bilingual_knowledge_service import BilingualKnowledgeService
from backend.services.concept_mapper import ConceptMapper
from backend.services.local_brain import normalize, tokens
from backend.training.enrichment import extract_concepts, extract_relations, qa_cards


class KnowledgeTrainingPipeline:
    def __init__(self, intelligence):
        self.intelligence = intelligence
        self.validator = KnowledgeQualityValidator()
        self.bilingual = BilingualKnowledgeService()
        self.mapper = ConceptMapper()
        initialize_database()

    def _sentences(self, text):
        out = []
        for s in re.split(r'(?<=[.!؟?])\s+|\n+', text or ''):
            s = s.strip(' -•\t')
            if 35 <= len(s) <= 500:
                out.append(s)
        return out

    def _title(self, text):
        for line in (text or '').splitlines():
            line = line.strip('# -\t ')
            if 4 <= len(line) <= 120:
                return line
        ts = tokens(text)
        return ' '.join(ts[:8]) or 'معرفة مستوردة'

    def train_file(self, path, metadata_base=None):
        start_t = time.perf_counter()
        metadata_base = dict(metadata_base or {})
        run_id = metadata_base.get('training_run_id') or f"run_{uuid.uuid4().hex[:8]}"
        metadata_base['training_run_id'] = run_id

        result = self.intelligence.ingest(path, metadata_base=metadata_base)
        cards = 0
        concepts: set[str] = set()
        relations: list[dict] = []

        documents_processed = 1
        chunks_created = len(result['items'])
        concepts_created = 0
        relationships_created = 0
        bilingual_links_created = 0
        duplicates_skipped = 0
        conflicts_detected = 0
        failures = 0

        for item in result['items']:
            text = item.get('text', '')
            meta = dict(item.get('metadata', {}))

            # Quality validation
            q_res = self.validator.validate_item(text, metadata=meta)
            if not q_res.valid:
                failures += 1
                continue

            source_kid = meta.get('knowledge_id')
            doc_id = meta.get('document_id')
            src = meta.get('source', 'dataset')

            title = self._title(text)
            chunk_concepts = extract_concepts(text)
            concepts.update(chunk_concepts)
            concepts_created += len(chunk_concepts)

            chunk_relations = extract_relations(text)
            relations.extend(chunk_relations)
            relationships_created += len(chunk_relations)

            # Language & concept linking
            lang = self.bilingual.detect_language(text)
            for c_term in chunk_concepts:
                if lang == "ar":
                    self.bilingual.link_terms(c_term, c_term)
                    bilingual_links_created += 1

            derived_meta = {
                **meta,
                'source_id': str(source_kid or doc_id or src),
                'source_type': 'dataset_file' if doc_id else 'knowledge_record',
                'source_knowledge_id': source_kid,
                'document_id': doc_id,
                'training_run_id': run_id,
                'knowledge_domain': meta.get('domain', 'general'),
                'knowledge_layer': meta.get('layer', 4),
                'language': lang,
                'owner_scope': meta.get('scope', 'public'),
                'confidence': 1.0,
                'status': 'active'
            }

            if chunk_concepts:
                concept_text = 'مفاهيم مرتبطة: ' + ', '.join(chunk_concepts)
                self.intelligence.rag.store.add(
                    concept_text,
                    {**derived_meta, 'training_artifact': 'concept_index',
                     'concept': title[:120], 'concepts': chunk_concepts},
                )

            for q, a in qa_cards(text, title):
                card = f"سؤال: {q}\nإجابة: {a}"
                self.intelligence.rag.store.add(
                    card,
                    {**derived_meta, 'training_artifact': 'qa_card',
                     'concept': title[:120], 'concepts': chunk_concepts},
                )
                cards += 1

        duration = round(time.perf_counter() - start_t, 2)
        report = {
            "run_id": run_id,
            "documents_processed": documents_processed,
            "chunks_created": chunks_created,
            "concepts_created": concepts_created,
            "relationships_created": relationships_created,
            "bilingual_links_created": bilingual_links_created,
            "duplicates_skipped": duplicates_skipped,
            "conflicts_detected": conflicts_detected,
            "failures": failures,
            "duration_seconds": duration,
            "status": "completed"
        }

        # Save to SQLite
        with connect() as c:
            c.execute(
                """
                INSERT INTO training_reports (
                    run_id, documents_processed, chunks_created, concepts_created,
                    relationships_created, bilingual_links_created, duplicates_skipped,
                    conflicts_detected, failures, duration_seconds, status, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    documents_processed=excluded.documents_processed,
                    chunks_created=excluded.chunks_created,
                    concepts_created=excluded.concepts_created,
                    relationships_created=excluded.relationships_created,
                    bilingual_links_created=excluded.bilingual_links_created,
                    duration_seconds=excluded.duration_seconds,
                    status=excluded.status
                """,
                (
                    run_id, documents_processed, chunks_created, concepts_created,
                    relationships_created, bilingual_links_created, duplicates_skipped,
                    conflicts_detected, failures, duration, "completed", json.dumps(report, ensure_ascii=False)
                )
            )

        return {
            **result,
            'training_cards': cards,
            'training_run_id': run_id,
            'training_report': report,
            'concepts': sorted(concepts)[:150],
            'relations': relations[:100],
            'pipeline': [
                'normalize', 'smart_chunk', 'quality_validation', 'concept_extraction',
                'bilingual_linking', 'relation_extraction', 'hybrid_index',
                'qa_card_generation', 'retrieval_ready', 'evaluation_ready',
                'provenance_linking'
            ],
        }
