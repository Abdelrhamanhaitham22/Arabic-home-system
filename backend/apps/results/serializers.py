from rest_framework import serializers

from .models import Result


class ResultItemSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name")
    level = serializers.CharField(source="exam.level.name", allow_null=True)
    max_score = serializers.DecimalField(source="exam.max_score", max_digits=8, decimal_places=2)
    exam_date = serializers.DateField(source="exam.exam_date")
    percentage = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    teacher_feedback = serializers.CharField(source="teacher_notes", read_only=True)

    def get_sections(self, result):
        assessment = result.student.teacher_assessments.filter(level_id=result.exam.level_id).first()
        if assessment:
            config = assessment.level.teacher_assessment_config
            return [
                {"name": "التحريري", "score": assessment.written_score, "max_score": config.written_max, "comment": ""},
                {"name": "النشاط والإملاء", "score": assessment.activity_dictation_score, "max_score": config.activity_dictation_max, "comment": ""},
                {"name": "الشفوي", "score": assessment.oral_score, "max_score": config.oral_max, "comment": result.teacher_notes},
            ]
        return [{"name": "التحريري", "score": result.score, "max_score": result.max_score or result.exam.max_score, "comment": result.teacher_notes}]

    def get_percentage(self, result):
        maximum = result.max_score or result.exam.max_score
        return round((result.score / maximum) * 100, 2) if maximum else 0

    class Meta:
        model = Result
        fields = (
            "exam_name",
            "level",
            "score",
            "max_score",
            "percentage",
            "exam_date",
            "sections",
            "teacher_feedback",
        )


class ResultLookupSerializer(serializers.Serializer):
    student_name = serializers.CharField(source="full_name")
    student_code = serializers.CharField()
    results = serializers.SerializerMethodField()

    def get_results(self, student):
        published_results = self.context.get("published_results")
        results = published_results if published_results is not None else student.results.filter(published=True)
        return ResultItemSerializer(results, many=True).data
