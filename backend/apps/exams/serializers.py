from rest_framework import serializers

from apps.results.models import ExamSubmission

from .models import Exam


class ExamSectionSerializer(serializers.Serializer):
    name = serializers.CharField()
    max_score = serializers.IntegerField()


class AvailableExamSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source="level.name", allow_null=True)
    sections = ExamSectionSerializer(many=True, read_only=True)
    exam_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ("id", "name", "level", "max_score", "exam_date", "sections", "exam_file_url")

    def get_exam_file_url(self, exam):
        if not exam.exam_file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(f"/api/exams/{exam.id}/file/") if request else None


class ExamSubmissionSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)

    class Meta:
        model = ExamSubmission
        fields = ("id", "exam", "exam_name", "status", "submitted_at")
        read_only_fields = fields
