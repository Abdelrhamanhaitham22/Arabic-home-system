from rest_framework import serializers

from .models import Result


class ResultItemSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name")
    level = serializers.CharField(source="exam.level.name", allow_null=True)
    score = serializers.SerializerMethodField()
    max_score = serializers.SerializerMethodField()
    exam_date = serializers.DateField(source="exam.exam_date")
    percentage = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    teacher_feedback = serializers.CharField(source="teacher_notes", read_only=True)

    def get_sections(self, result):
        assessments = result.student.teacher_assessments.select_related("level__teacher_assessment_config")
        assessment = assessments.filter(level_id=result.exam.level_id).first() or assessments.filter(level_id=result.student.level_id).first() or assessments.first()
        if assessment:
            config = getattr(assessment.level, "teacher_assessment_config", None)
            if config is None:
                return [{"name": "التحريري", "score": result.score, "max_score": result.max_score or result.exam.max_score, "comment": result.teacher_notes}]
            return [
                {"name": "التحريري", "score": assessment.written_score, "max_score": config.written_max, "comment": ""},
                {"name": "النشاط والإملاء", "score": assessment.activity_dictation_score, "max_score": config.activity_dictation_max, "comment": ""},
                {"name": "الشفوي", "score": assessment.oral_score, "max_score": config.oral_max, "comment": result.teacher_notes},
            ]
        return [{"name": "التحريري", "score": result.score, "max_score": result.max_score or result.exam.max_score, "comment": result.teacher_notes}]

    def get_percentage(self, result):
        sections = self.get_sections(result)
        maximum = sum(section["max_score"] for section in sections)
        score = sum(section["score"] for section in sections)
        return round((score / maximum) * 100, 2) if maximum else 0

    def get_score(self, result):
        return sum(section["score"] for section in self.get_sections(result))

    def get_max_score(self, result):
        return sum(section["max_score"] for section in self.get_sections(result))

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
    current_level = serializers.CharField(source="level.name", allow_null=True)
    results = serializers.SerializerMethodField()

    def get_results(self, student):
        published_results = self.context.get("published_results")
        results = published_results if published_results is not None else student.results.filter(published=True)
        return ResultItemSerializer(results, many=True).data
