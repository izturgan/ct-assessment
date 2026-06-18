import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Essay, LLMScore, LLMFeedback
from .repository import (
    EssayRepository,
    LLMScoreRepository,
    LLMFeedbackRepository,
    ValidationResultRepository,
)
from .serializers import (
    EssaySerializer,
    LLMScoreSerializer,
    LLMFeedbackSerializer,
    ValidationResultSerializer,
)

_SCORING_WEBHOOK = "https://neuron.finreg.kz/webhook/score-essay"


class EssayUploadView(APIView):
    def post(self, request):
        validated, error = EssaySerializer.validate(request.data)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        try:
            essay = EssayRepository().create(Essay(**validated))
            return Response({"id": essay.id, "word_count": essay.word_count})
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TriggerScoringView(APIView):
    def post(self, request):
        essay_id = request.data.get("essay_id")
        if not essay_id:
            return Response({"error": "essay_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            essay = EssayRepository().get_by_id(int(essay_id))
            if not essay:
                return Response({"error": "Essay not found"}, status=status.HTTP_400_BAD_REQUEST)

            resp = requests.post(
                    _SCORING_WEBHOOK,
                    json={"essay_id": essay.id, "essay_text": essay.essay_text},
                    timeout=120,
                    verify=False,
            )
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
            job_id = data.get("job_id") or data.get("executionId") or ""
            return Response({"status": "ok", "job_id": job_id})
        except requests.RequestException as exc:
            return Response({"error": f"Webhook error: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScoreSubmitView(APIView):
    def post(self, request):
        data = request.data
        essay_id = data.get("essay_id")
        if not essay_id:
            return Response({"error": "essay_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            score = LLMScore(
                essay_id=int(essay_id),
                job_id=data.get("job_id"),
                score_arg=data.get("score_arg"),
                score_evidence=data.get("score_evidence"),
                score_logic=data.get("score_logic"),
                score_perspective=data.get("score_perspective"),
                score_metacog=data.get("score_metacog"),
                reasoning=data.get("reasoning"),
                arg_structure=data.get("arg_structure"),
                detected_fallacies=data.get("detected_fallacies"),
            )
            score = LLMScoreRepository().create(score)

            feedback_text = (data.get("feedback_text") or "").strip()
            if feedback_text:
                feedback = LLMFeedback(
                    essay_id=int(essay_id),
                    llm_score_id=score.id,
                    feedback_text=feedback_text,
                    weakest_dimension=data.get("weakest_dimension"),
                )
                LLMFeedbackRepository().create(feedback)

            return Response({"status": "ok", "llm_score_id": score.id})
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EssayResultsView(APIView):
    def get(self, request, essay_id):
        try:
            essay = EssayRepository().get_by_id(essay_id)
            if not essay:
                return Response({"error": "Essay not found"}, status=status.HTTP_404_NOT_FOUND)

            score = LLMScoreRepository().get_by_essay_id(essay_id)
            feedback = LLMFeedbackRepository().get_by_essay_id(essay_id)

            return Response({
                "essay": EssaySerializer.to_dict(essay),
                "llm_score": LLMScoreSerializer.to_dict(score) if score else None,
                "llm_feedback": LLMFeedbackSerializer.to_dict(feedback) if feedback else None,
            })
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidationLatestView(APIView):
    def get(self, request):
        try:
            result = ValidationResultRepository().get_latest()
            if not result:
                return Response({"error": "No validation results found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(ValidationResultSerializer.to_dict(result))
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
