from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class Essay:
    essay_text: str
    id: Optional[int] = None
    external_id: Optional[str] = None
    source: str = "persuade"
    prompt_id: Optional[int] = None
    word_count: int = 0
    language: str = "en"
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.word_count and self.essay_text:
            self.word_count = len(self.essay_text.split())


@dataclass
class ExpertScore:
    essay_id: int
    score_raw: float
    score_normalized: float
    source: str
    id: Optional[int] = None
    score_arg: Optional[int] = None
    score_evidence: Optional[int] = None
    score_logic: Optional[int] = None
    score_perspective: Optional[int] = None
    score_metacog: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class LLMScore:
    essay_id: int
    id: Optional[int] = None
    job_id: Optional[str] = None
    model_name: str = "gptoss-120b"
    score_arg: Optional[int] = None
    score_evidence: Optional[int] = None
    score_logic: Optional[int] = None
    score_perspective: Optional[int] = None
    score_metacog: Optional[int] = None
    score_composite: Optional[float] = None
    reasoning: Optional[str] = None
    arg_structure: Optional[Any] = None
    detected_fallacies: Optional[Any] = None
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        scores = [
            self.score_arg, self.score_evidence, self.score_logic,
            self.score_perspective, self.score_metacog,
        ]
        if self.score_composite is None and all(s is not None for s in scores):
            self.score_composite = (sum(scores) / len(scores) - 1) / 3


@dataclass
class LLMFeedback:
    essay_id: int
    llm_score_id: int
    feedback_text: str
    id: Optional[int] = None
    weakest_dimension: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class NLPFeatures:
    essay_id: int
    id: Optional[int] = None
    arg_claim_count: int = 0
    arg_evidence_count: int = 0
    arg_warrant_count: int = 0
    arg_counter_count: int = 0
    arg_coverage: float = 0.0
    fallacy_total: int = 0
    fallacy_authority: int = 0
    fallacy_generalize: int = 0
    fallacy_dichotomy: int = 0
    fallacy_circular: int = 0
    sentence_count: int = 0
    avg_sent_length: float = 0.0
    transition_density: float = 0.0
    type_token_ratio: float = 0.0
    subordination_idx: float = 0.0
    metacognitive_count: int = 0
    has_counter_arg: bool = False
    aqi: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class ValidationResult:
    run_id: str
    n_essays: int
    id: Optional[int] = None
    pearson_r: Optional[float] = None
    spearman_rho: Optional[float] = None
    qwk: Optional[float] = None
    bias_mean: Optional[float] = None
    loa_upper: Optional[float] = None
    loa_lower: Optional[float] = None
    rf_r2: Optional[float] = None
    gb_r2: Optional[float] = None
    created_at: Optional[datetime] = None
