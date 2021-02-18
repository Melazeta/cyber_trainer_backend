from rest_framework import serializers
from trainer.models import LevelScore


class LevelScoreSerializer(serializers.Serializer):
    class Meta:
        model = LevelScore
        fields = (
            "user",
            "case",
            "time_spent",
            "right_labels",
            "played",
            "email_errors",
            "file_errors",
            "conversation_errors",
            "site_errors"
        )
