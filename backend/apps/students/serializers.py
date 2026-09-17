from django.db import IntegrityError
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

    def validate_passport_number(self, passport_number):
        normalized_passport = passport_number.strip().upper()
        if Student.objects.filter(passport_number__iexact=normalized_passport).exists():
            raise serializers.ValidationError("A student with this passport number already exists.")
        return normalized_passport

    def create(self, validated_data):
        try:
            return Student.objects.create(**validated_data)
        except IntegrityError as error:
            if "passport_number" not in str(error):
                raise
            raise serializers.ValidationError(
                {"passport_number": "A student with this passport number already exists."}
            ) from error


class StudentLevelSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source="level.name", allow_null=True)

    class Meta:
        model = Student
        fields = ("student_code", "full_name", "level")


class LevelOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
