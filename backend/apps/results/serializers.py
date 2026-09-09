from rest_framework import serializers

from .models import Result


class ResultItemSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name")
    max_score = serializers.IntegerField(source="exam.max_score")
    exam_date = serializers.DateField(source="exam.exam_date")
    percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = Result
        fields = ("exam_name", "score", "max_score", "percentage", "exam_date")


class ResultLookupSerializer(serializers.Serializer):
    student_name = serializers.CharField(source="full_name")
    student_code = serializers.CharField()
    results = ResultItemSerializer(many=True)
