from django.urls import path
from assessment.views import (
    EssayUploadView,
    TriggerScoringView,
    ScoreSubmitView,
    EssayResultsView,
    ValidationLatestView,
)

urlpatterns = [
    path("api/essays/upload/", EssayUploadView.as_view()),
    path("api/essays/trigger-scoring/", TriggerScoringView.as_view()),
    path("api/scores/", ScoreSubmitView.as_view()),
    path("api/essays/<int:essay_id>/results/", EssayResultsView.as_view()),
    path("api/validation/latest/", ValidationLatestView.as_view()),
]
