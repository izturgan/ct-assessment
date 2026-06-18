from typing import Optional
from .db_client import N8nDBClient
from .models import Essay, ExpertScore, LLMScore, LLMFeedback, NLPFeatures, ValidationResult


class EssayRepository:
    def __init__(self):
        self.db = N8nDBClient()

    def create(self, essay: Essay) -> Essay:
        query = """
            INSERT INTO essays (external_id, source, prompt_id, essay_text, word_count, language)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """
        rows = self.db.execute(query, [
            essay.external_id, essay.source, essay.prompt_id,
            essay.essay_text, essay.word_count, essay.language,
        ])
        if rows:
            essay.id = rows[0]["id"]
            essay.created_at = rows[0].get("created_at")
        return essay

    def get_by_id(self, essay_id: int) -> Optional[Essay]:
        rows = self.db.execute("SELECT * FROM essays WHERE id = %s", [essay_id])
        if not rows:
            return None
        return Essay(**rows[0])

    def get_all(self) -> list[Essay]:
        rows = self.db.execute("SELECT * FROM essays ORDER BY created_at DESC")
        return [Essay(**row) for row in rows]

    def bulk_create(self, essays: list[Essay]) -> list[Essay]:
        return [self.create(essay) for essay in essays]


class ExpertScoreRepository:
    def __init__(self):
        self.db = N8nDBClient()

    def create(self, score: ExpertScore) -> ExpertScore:
        query = """
            INSERT INTO expert_scores
                (essay_id, score_raw, score_normalized, score_arg, score_evidence,
                 score_logic, score_perspective, score_metacog, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """
        rows = self.db.execute(query, [
            score.essay_id, score.score_raw, score.score_normalized,
            score.score_arg, score.score_evidence, score.score_logic,
            score.score_perspective, score.score_metacog, score.source,
        ])
        if rows:
            score.id = rows[0]["id"]
            score.created_at = rows[0].get("created_at")
        return score

    def get_by_essay_id(self, essay_id: int) -> Optional[ExpertScore]:
        rows = self.db.execute(
            "SELECT * FROM expert_scores WHERE essay_id = %s", [essay_id]
        )
        if not rows:
            return None
        return ExpertScore(**rows[0])


class LLMScoreRepository:
    def __init__(self):
        self.db = N8nDBClient()

    def create(self, score: LLMScore) -> LLMScore:
        query = """
            INSERT INTO llm_scores
                (essay_id, job_id, model_name, score_arg, score_evidence, score_logic,
                 score_perspective, score_metacog, score_composite, reasoning,
                 arg_structure, detected_fallacies, processing_time_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """
        rows = self.db.execute(query, [
            score.essay_id, score.job_id, score.model_name,
            score.score_arg, score.score_evidence, score.score_logic,
            score.score_perspective, score.score_metacog, score.score_composite,
            score.reasoning, score.arg_structure, score.detected_fallacies,
            score.processing_time_ms,
        ])
        if rows:
            score.id = rows[0]["id"]
            score.created_at = rows[0].get("created_at")
        return score

    def get_by_essay_id(self, essay_id: int) -> Optional[LLMScore]:
        rows = self.db.execute(
            "SELECT * FROM llm_scores WHERE essay_id = %s", [essay_id]
        )
        if not rows:
            return None
        return LLMScore(**rows[0])


class LLMFeedbackRepository:
    def __init__(self):
        self.db = N8nDBClient()

    def create(self, feedback: LLMFeedback) -> LLMFeedback:
        query = """
            INSERT INTO llm_feedback (essay_id, llm_score_id, feedback_text, weakest_dimension)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """
        rows = self.db.execute(query, [
            feedback.essay_id, feedback.llm_score_id,
            feedback.feedback_text, feedback.weakest_dimension,
        ])
        if rows:
            feedback.id = rows[0]["id"]
            feedback.created_at = rows[0].get("created_at")
        return feedback

    def get_by_essay_id(self, essay_id: int) -> Optional[LLMFeedback]:
        rows = self.db.execute(
            "SELECT * FROM llm_feedback WHERE essay_id = %s", [essay_id]
        )
        if not rows:
            return None
        return LLMFeedback(**rows[0])


class NLPFeaturesRepository:
    def __init__(self):
        self.db = N8nDBClient()

    def create(self, features: NLPFeatures) -> NLPFeatures:
        query = """
            INSERT INTO nlp_features
                (essay_id, arg_claim_count, arg_evidence_count, arg_warrant_count,
                 arg_counter_count, arg_coverage, fallacy_total, fallacy_authority,
                 fallacy_generalize, fallacy_dichotomy, fallacy_circular,
                 sentence_count, avg_sent_length, transition_density,
                 type_token_ratio, subordination_idx, metacognitive_count,
                 has_counter_arg, aqi)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """
        rows = self.db.execute(query, [
            features.essay_id, features.arg_claim_count, features.arg_evidence_count,
            features.arg_warrant_count, features.arg_counter_count, features.arg_coverage,
            features.fallacy_total, features.fallacy_authority, features.fallacy_generalize,
            features.fallacy_dichotomy, features.fallacy_circular, features.sentence_count,
            features.avg_sent_length, features.transition_density, features.type_token_ratio,
            features.subordination_idx, features.metacognitive_count,
            features.has_counter_arg, features.aqi,
        ])
        if rows:
            features.id = rows[0]["id"]
            features.created_at = rows[0].get("created_at")
        return features

    def get_by_essay_id(self, essay_id: int) -> Optional[NLPFeatures]:
        rows = self.db.execute(
            "SELECT * FROM nlp_features WHERE essay_id = %s", [essay_id]
        )
        if not rows:
            return None
        return NLPFeatures(**rows[0])


class ValidationResultRepository:
    def __init__(self):
        self.db = N8nDBClient()

    def create(self, result: ValidationResult) -> ValidationResult:
        query = """
            INSERT INTO validation_results
                (run_id, n_essays, pearson_r, spearman_rho, qwk,
                 bias_mean, loa_upper, loa_lower, rf_r2, gb_r2)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """
        rows = self.db.execute(query, [
            result.run_id, result.n_essays, result.pearson_r, result.spearman_rho,
            result.qwk, result.bias_mean, result.loa_upper, result.loa_lower,
            result.rf_r2, result.gb_r2,
        ])
        if rows:
            result.id = rows[0]["id"]
            result.created_at = rows[0].get("created_at")
        return result

    def get_latest(self) -> Optional[ValidationResult]:
        rows = self.db.execute(
            "SELECT * FROM validation_results ORDER BY created_at DESC LIMIT 1"
        )
        if not rows:
            return None
        return ValidationResult(**rows[0])
