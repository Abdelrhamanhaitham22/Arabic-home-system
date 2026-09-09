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
