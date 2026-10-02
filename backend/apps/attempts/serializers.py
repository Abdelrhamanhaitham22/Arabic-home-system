from rest_framework import serializers

from .models import AttemptQuestion, ExamAttempt


class AttemptQuestionSerializer(serializers.ModelSerializer):
    choices = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()
    correct_answer = serializers.SerializerMethodField()

    class Meta:
        model = AttemptQuestion
        fields = (
            "id", "display_order", "points_snapshot", "question_text_snapshot", "question_type_snapshot",
            "choices", "answer", "correct_answer",
        )

    def get_choices(self, question):
        return [{"id": item["id"], "text": item["text"]} for item in question.choices_snapshot]

    def get_answer(self, question):
        answer = getattr(question, "answer", None)
        if answer is None:
            return None
        return {
            "selected_choice_id": answer.selected_choice_id,
            "selected_answer_value": answer.selected_answer_value,
        }

    def get_correct_answer(self, question):
        if question.attempt.status != "submitted":
            return None
        return question.correct_answer_snapshot


class ExamAttemptSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name")
    questions = AttemptQuestionSerializer(many=True, read_only=True)
    deadline = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ExamAttempt
        fields = (
            "id", "exam", "exam_name", "status", "started_at", "submitted_at", "deadline",
            "score", "max_score", "percentage", "questions",
        )
