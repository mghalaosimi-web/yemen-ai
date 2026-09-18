import json
from typing import Dict, Any, List, Optional
from app.data.database import connect, initialize_database


class UserInteractionProfileService:
    def __init__(self):
        initialize_database()

    def get_profile(self, user_id: str = "owner") -> Dict[str, Any]:
        with connect() as c:
            row = c.execute("SELECT * FROM user_interaction_profiles WHERE user_id=?", (user_id,)).fetchone()
            if not row:
                # Default profile
                c.execute(
                    """
                    INSERT INTO user_interaction_profiles (user_id, preferred_response_language, preferred_detail_level, technical_depth, communication_style, preferred_answer_format, active_projects, frequently_used_terms)
                    VALUES (?, 'ar', 'medium', 'high', 'direct', 'structured', '["Yemen AI"]', '[]')
                    """,
                    (user_id,)
                )
                row = c.execute("SELECT * FROM user_interaction_profiles WHERE user_id=?", (user_id,)).fetchone()

            d = dict(row)
            d["active_projects"] = json.loads(d.get("active_projects") or "[]")
            d["frequently_used_terms"] = json.loads(d.get("frequently_used_terms") or "[]")
            return d

    def update_profile(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        curr = self.get_profile(user_id)
        
        pref_lang = preferences.get("preferred_response_language", curr["preferred_response_language"])
        pref_detail = preferences.get("preferred_detail_level", curr["preferred_detail_level"])
        tech_depth = preferences.get("technical_depth", curr["technical_depth"])
        comm_style = preferences.get("communication_style", curr["communication_style"])
        ans_fmt = preferences.get("preferred_answer_format", curr["preferred_answer_format"])
        
        active_p = preferences.get("active_projects", curr["active_projects"])
        freq_t = preferences.get("frequently_used_terms", curr["frequently_used_terms"])

        with connect() as c:
            c.execute(
                """
                UPDATE user_interaction_profiles
                SET preferred_response_language=?,
                    preferred_detail_level=?,
                    technical_depth=?,
                    communication_style=?,
                    preferred_answer_format=?,
                    active_projects=?,
                    frequently_used_terms=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
                """,
                (
                    pref_lang,
                    pref_detail,
                    tech_depth,
                    comm_style,
                    ans_fmt,
                    json.dumps(active_p, ensure_ascii=False),
                    json.dumps(freq_t, ensure_ascii=False),
                    user_id
                )
            )

        return self.get_profile(user_id)

    def record_explicit_preference(self, user_id: str, key: str, value: Any) -> Dict[str, Any]:
        valid_keys = {
            "preferred_response_language",
            "preferred_detail_level",
            "technical_depth",
            "communication_style",
            "preferred_answer_format"
        }
        if key in valid_keys:
            return self.update_profile(user_id, {key: str(value)})
        elif key == "active_projects":
            curr = self.get_profile(user_id)
            projs = list(set(curr["active_projects"] + [str(value)]))
            return self.update_profile(user_id, {"active_projects": projs})
        elif key == "frequently_used_terms":
            curr = self.get_profile(user_id)
            terms = list(set(curr["frequently_used_terms"] + [str(value)]))
            return self.update_profile(user_id, {"frequently_used_terms": terms})
        
        return self.get_profile(user_id)

    def get_active_projects(self, user_id: str = "owner") -> List[str]:
        p = self.get_profile(user_id)
        return p.get("active_projects", [])

    def get_response_preferences(self, user_id: str = "owner") -> Dict[str, Any]:
        p = self.get_profile(user_id)
        return {
            "language": p.get("preferred_response_language", "ar"),
            "detail_level": p.get("preferred_detail_level", "medium"),
            "technical_depth": p.get("technical_depth", "high"),
            "communication_style": p.get("communication_style", "direct"),
            "format": p.get("preferred_answer_format", "structured")
        }
