from dataclasses import asdict
from typing import Any


def _clean(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _to_dict(obj) -> dict:
    return {k: _clean(v) for k, v in asdict(obj).items()}


class EssaySerializer:
    @staticmethod
    def to_dict(essay) -> dict:
        return _to_dict(essay)

    @staticmethod
    def validate(data: dict) -> tuple[dict, str | None]:
        essay_text = (data.get("essay_text") or "").strip()
        if not essay_text:
            return {}, "essay_text is required"
        return {
            "essay_text": essay_text,
            "source": data.get("source", "manual"),
            "language": data.get("language", "en"),
            "external_id": data.get("external_id"),
            "prompt_id": data.get("prompt_id"),
        }, None


class LLMScoreSerializer:
    @staticmethod
    def to_dict(score) -> dict:
        return _to_dict(score)


class LLMFeedbackSerializer:
    @staticmethod
    def to_dict(feedback) -> dict:
        return _to_dict(feedback)


class ValidationResultSerializer:
    @staticmethod
    def to_dict(result) -> dict:
        return _to_dict(result)
