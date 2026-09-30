from rest_framework import serializers

from .models import Exam


class ExamSectionSerializer(serializers.Serializer):
    name = serializers.CharField()
    max_score = serializers.IntegerField()


class AvailableExamSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source="level.name", allow_null=True)
    sections = ExamSectionSerializer(many=True, read_only=True)
    class Meta:
        model = Exam
        fields = (
            "id", "name", "level", "max_score", "exam_date", "opens_at", "closes_at",
            "sections",
        )
