from rest_framework import serializers

from .models import Result


class ResultItemSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name")
    level = serializers.CharField(source="exam.level.name", allow_null=True)
    max_score = serializers.IntegerField(source="exam.max_score")
    exam_date = serializers.DateField(source="exam.exam_date")
    percentage = serializers.FloatField(read_only=True)
    sections = serializers.SerializerMethodField()
    teacher_feedback = serializers.CharField(source="teacher_notes", read_only=True)

    def get_sections(self, result):
        section_scores = getattr(result, "prefetched_section_scores", None)
        if section_scores is None:
            section_scores = result.section_scores.select_related("section").all()
        return [
            {
                "name": section_score.section.name,
                "score": section_score.score,
                "max_score": section_score.section.max_score,
                "comment": section_score.teacher_comment,
            }
            for section_score in sorted(
                (
                    section_score
                    for section_score in section_scores
                    if section_score.section.exam_id == result.exam_id
                ),
                key=lambda section_score: section_score.section.order,
            )
        ]

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
