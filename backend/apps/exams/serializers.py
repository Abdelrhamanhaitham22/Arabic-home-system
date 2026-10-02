from rest_framework import serializers

from .models import Exam, QuestionChoice


class QuestionChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionChoice
        fields = ("id", "text", "order")


class ExamQuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    prompt = serializers.CharField()
    question_type = serializers.CharField()
    points = serializers.IntegerField()
    order = serializers.IntegerField()
    choices = QuestionChoiceSerializer(many=True, read_only=True)


class AvailableExamSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source="level.name", allow_null=True)
    class Meta:
        model = Exam
        fields = (
            "id", "name", "level", "max_score", "exam_date", "opens_at", "closes_at",
            "time_limit_minutes",
        )


class AvailableExamDetailSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source="level.name", allow_null=True)

    class Meta:
        model = Exam
        fields = (
            "id", "name", "level", "max_score", "exam_date", "opens_at", "closes_at",
            "time_limit_minutes",
        )
