from rest_framework import serializers

from .models import Student
from apps.exams.models import Level


class StudentRegistrationSerializer(serializers.ModelSerializer):
    level_id = serializers.PrimaryKeyRelatedField(source="level", queryset=Level.objects.all(), write_only=True)

    class Meta:
        model = Student
        fields = (
            "full_name",
            "phone_number",
            "address",
            "passport_number",
            "level_id",
            "preferred_language",
        )

    def create(self, validated_data):
        return Student.objects.create(**validated_data)


class StudentLevelSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source="level.name", allow_null=True)

    class Meta:
        model = Student
        fields = ("student_code", "full_name", "level")


class LevelOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
