from rest_framework import serializers

from .models import Student


class StudentRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = (
            "full_name",
            "phone_number",
            "address",
            "passport_number",
            "preferred_language",
        )

    def create(self, validated_data):
        return Student.objects.create(**validated_data)


class StudentLevelSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source="level.name", allow_null=True)

    class Meta:
        model = Student
        fields = ("student_code", "full_name", "level")
