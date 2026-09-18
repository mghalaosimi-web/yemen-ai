import os
import hashlib
import json
import yaml
from typing import Dict, Any, List, Optional
from app.data.database import connect, initialize_database
from backend.services.knowledge_quality_validator import KnowledgeQualityValidator


class KnowledgePackRegistry:
    def __init__(self, seed_dir: Optional[str] = None):
        initialize_database()
        self.seed_dir = seed_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_seed")
        self.validator = KnowledgeQualityValidator()

    def discover_packs(self) -> List[Dict[str, Any]]:
        packs = []
        if not os.path.exists(self.seed_dir):
            return packs

        for root, dirs, files in os.walk(self.seed_dir):
            for file in files:
                if file.endswith((".md", ".json", ".yaml", ".yml")):
                    fpath = os.path.join(root, file)
                    rel_dir = os.path.relpath(root, self.seed_dir)
                    domain = rel_dir.replace("\\", "/").split("/")[0] if rel_dir != "." else "general"
                    
                    pack_id = f"pack_{domain}_{os.path.splitext(file)[0]}"
                    checksum = self._compute_checksum(fpath)

                    packs.append({
                        "pack_id": pack_id,
                        "name": file,
                        "domain": domain,
                        "path": fpath,
                        "checksum": checksum,
                        "extension": os.path.splitext(file)[1].lower()
                    })

        return packs

    def _compute_checksum(self, filepath: str) -> str:
        h = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            return h.hexdigest()[:16]
        except Exception:
            return "00000000"

    def validate_pack(self, pack_info: Dict[str, Any]) -> Dict[str, Any]:
        fpath = pack_info.get("path")
        if not fpath or not os.path.exists(fpath):
            return {"valid": False, "reason": "File does not exist"}

        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            return {"valid": False, "reason": str(e)}

        res = self.validator.validate_item(content, title=pack_info.get("name", ""), metadata={"source": fpath})
        return res.to_dict()

    def register_pack(self, pack_info: Dict[str, Any]) -> Dict[str, Any]:
        pack_id = pack_info.get("pack_id") or f"pack_{pack_info.get('domain', 'general')}_{pack_info.get('name', 'seed')}"
        name = pack_info.get("name", "seed_pack")
        version = pack_info.get("version", "1.0")
        domain = pack_info.get("domain", "general")
        language = pack_info.get("language", "en")
        source = pack_info.get("path", "")
        scope = pack_info.get("scope", "public")
        checksum = pack_info.get("checksum") or self._compute_checksum(source) if source else ""

        with connect() as c:
            c.execute(
                """
                INSERT INTO knowledge_packs (pack_id, name, version, domain, language, source, scope, checksum, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
                ON CONFLICT(pack_id) DO UPDATE SET
                    name=excluded.name,
                    version=excluded.version,
                    domain=excluded.domain,
                    language=excluded.language,
                    source=excluded.source,
                    scope=excluded.scope,
                    checksum=excluded.checksum,
                    status='active'
                """,
                (pack_id, name, version, domain, language, source, scope, checksum)
            )

        return self.get_pack_stats(pack_id)

    def get_pack_stats(self, pack_id: str) -> Dict[str, Any]:
        with connect() as c:
            row = c.execute("SELECT * FROM knowledge_packs WHERE pack_id=?", (pack_id,)).fetchone()
            if not row:
                return {"pack_id": pack_id, "found": False}
            return dict(row)

    def load_pack(self, pack_id: str) -> Optional[str]:
        stats = self.get_pack_stats(pack_id)
        fpath = stats.get("source")
        if fpath and os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        return None

    def retrain_pack(self, pack_id: str, pipeline_service) -> Dict[str, Any]:
        content = self.load_pack(pack_id)
        if not content:
            return {"status": "failed", "reason": "Pack content not found"}

        stats = self.get_pack_stats(pack_id)
        res = pipeline_service.run_pipeline(
            content,
            dataset_name=stats.get("name", pack_id),
            metadata_base={"pack_id": pack_id, "domain": stats.get("domain", "general")}
        )
        return res
