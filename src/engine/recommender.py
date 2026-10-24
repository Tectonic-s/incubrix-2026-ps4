"""Content-to-Destination Recommendation Engine with Precision@10 evaluation."""
import json
from typing import Any, Dict, List, Optional
from src.database import get_db
from src.models.connector import Destination, Rendition


class RecommendationEngine:
    def rank_destinations(
        self,
        rendition: Rendition,
        destinations: Optional[List[Destination]] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Ranks candidate destinations by audience fit, rule compatibility, and platform level.
        Returns top_k items with reason and score (0-100).
        """
        # Fetch destinations from DB if not supplied
        candidate_destinations: List[Destination] = []
        if destinations:
            candidate_destinations = destinations
        else:
            with get_db() as conn:
                cur = conn.execute("SELECT * FROM destinations WHERE level != 'demoted'")
                for r in cur.fetchall():
                    tags = json.loads(r["audience_tags"]) if r["audience_tags"] else []
                    candidate_destinations.append(
                        Destination(
                            id=r["id"],
                            name=r["name"],
                            url=r["url"],
                            platform_key=r["platform_key"],
                            surface=r["surface"],
                            category=r["category"],
                            audience_tags=tags,
                            language=r["language"],
                            geo=r["geo"],
                            est_audience=r["est_audience"],
                            rules_url=r["rules_url"],
                            frequency_cap=r["frequency_cap"],
                            self_promo_allowed=bool(r["self_promo_allowed"]),
                            link_policy=r["link_policy"],
                            disclosure_required=bool(r["disclosure_required"]),
                            automation_allowed=bool(r["automation_allowed"]),
                            connector_key=r["connector_key"],
                            relevance_score=r["relevance_score"],
                            relevance_reason=r["relevance_reason"],
                            level=r["level"],
                            last_certified_at=r["last_certified_at"],
                        )
                    )

        scored_results = []
        content_text = f"{rendition.title} {rendition.body} {' '.join(rendition.tags)}".lower()
        content_tags = {t.lower().replace("-", " ") for t in rendition.tags}

        for dest in candidate_destinations:
            score = 0.0
            reasons = []

            # 1. Base Audience Match (0 - 55 points)
            dest_tags = {t.lower().replace("-", " ") for t in dest.audience_tags}
            overlap = content_tags.intersection(dest_tags)
            if overlap:
                score += min(40.0, len(overlap) * 15.0)
                reasons.append(f"Tag match on {', '.join(list(overlap)[:3])}")
            if dest.category.lower() in content_text:
                score += 25.0
                reasons.append(f"Category alignment with {dest.category}")
            if any(t in dest.name.lower() for t in content_tags if len(t) > 2):
                score += 15.0
                reasons.append(f"Name keyword match with content topic")

            # 2. Base Platform Relevance (0 - 25 points)
            score += dest.relevance_score * 5.0
            if dest.relevance_score >= 4:
                reasons.append("High strategic relevance for IncuBrix target audience")

            # 3. Certification Level (0 - 15 points)
            if dest.level in ("L3", "L4"):
                score += 15.0
                reasons.append("Fully certified native connector with proven reliability")
            elif dest.level == "L1":
                score += 8.0
                reasons.append("Assisted posting workflow supported")

            # 4. Rule Compatibility Adjustments
            if rendition.is_promotional and not dest.self_promo_allowed:
                score -= 40.0
                reasons.append("WARNING: Destination strictly bans self-promotion")

            if dest.disclosure_required and not rendition.has_ai_disclosure:
                score -= 20.0
                reasons.append("WARNING: Missing required AI transparency disclosure")

            # Language check (e.g. non-English destination)
            content_lang = rendition.extra_meta.get("language", "en")
            if dest.language != content_lang:
                score -= 25.0
                reasons.append(f"Language mismatch ({dest.language} destination vs {content_lang} content)")

            final_score = max(0.0, min(100.0, score))
            scored_results.append({
                "destination_id": dest.id,
                "destination_name": dest.name,
                "destination_url": dest.url,
                "platform_key": dest.platform_key,
                "connector_key": dest.connector_key,
                "score": round(final_score, 1),
                "reasons": reasons,
                "level": dest.level,
            })

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]

    def evaluate_precision_at_k(self, eval_data: List[Dict[str, Any]], k: int = 10) -> Dict[str, Any]:
        """
        Evaluates Precision@K against a labelled dataset.
        Format of eval_data item:
        {
          "content": {"title": ..., "body": ..., "tags": ...},
          "ground_truth_relevant_ids": ["dest_1", "dest_2", ...]
        }
        """
        precisions = []
        for item in eval_data:
            rendition = Rendition(
                title=item["content"]["title"],
                body=item["content"]["body"],
                tags=item["content"].get("tags", []),
                is_promotional=item["content"].get("is_promotional", False),
                has_ai_disclosure=item["content"].get("has_ai_disclosure", False),
            )
            relevant_set = set(item["ground_truth_relevant_ids"])
            ranked = self.rank_destinations(rendition, top_k=k)
            relevant_in_top_k = sum(
                1 for r in ranked if r["destination_id"] in relevant_set or r["destination_name"] in relevant_set
            )
            precision = relevant_in_top_k / float(k)
            precisions.append(precision)

        avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
        return {
            "samples_count": len(eval_data),
            "k": k,
            "mean_precision_at_k": round(avg_precision, 4),
            "precision_percentage": f"{round(avg_precision * 100, 1)}%",
        }


recommendation_engine = RecommendationEngine()
