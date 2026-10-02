import random

from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.exams.models import Exam
from apps.students.models import Student
from .models import AttemptQuestion, ExamAttempt, StudentAnswer
from .serializers import ExamAttemptSerializer


def normalized_student_code(request):
    code = str(request.data.get("student_code", request.query_params.get("student_code", ""))).strip().upper()
    if len(code) != 8 or not code.isdigit():
        return None
    return code


def attempt_for_request(request, attempt_id):
    code = normalized_student_code(request)
    if not code:
        return None, Response({"error": "invalid_student_code", "message": "Enter a valid student code."}, status=400)
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("exam", "student").prefetch_related(
            Prefetch("questions", queryset=AttemptQuestion.objects.prefetch_related("answer"))
        ),
        id=attempt_id,
        student__student_code=code,
    )
    return attempt, None


def attempt_response(attempt):
    return Response(ExamAttemptSerializer(attempt).data)


def answer_values(question, answer_payload):
    choice_id = answer_payload.get("selected_choice_id")
    answer_value = str(answer_payload.get("selected_answer_value", ""))
    if choice_id not in (None, ""):
        try:
            choice_id = int(choice_id)
        except (TypeError, ValueError) as error:
            raise ValueError("The selected answer is invalid.") from error
        if not any(choice["id"] == choice_id for choice in question.choices_snapshot):
            raise ValueError("The selected answer is invalid.")
        answer_value = next(choice["text"] for choice in question.choices_snapshot if choice["id"] == choice_id)
    if choice_id in (None, "") and not answer_value:
        raise ValueError("Select an answer.")
    selected_choice = None
    if choice_id not in (None, "") and question.original_question_id:
        selected_choice = question.original_question.choices.filter(id=choice_id).first()
    return selected_choice, answer_value


class StartExamView(APIView):
    def post(self, request, exam_id):
        code = normalized_student_code(request)
        if not code:
            return Response({"error": "invalid_student_code", "message": "Enter a valid student code."}, status=400)
        student = get_object_or_404(Student.objects.select_related("level"), student_code=code)
        exam = get_object_or_404(Exam.objects.select_related("level"), id=exam_id)
        if exam.level_id != student.level_id:
            return Response({"error": "exam_not_available", "message": "This exam is not assigned to your level."}, status=404)
        if not exam.is_submission_open:
            return Response({"error": "exam_closed", "message": "This exam is not open."}, status=409)
        if exam.level.question_bank_errors():
            return Response({"error": "question_bank_incomplete", "message": "This exam is not ready yet."}, status=409)

        existing = ExamAttempt.objects.filter(student=student, exam=exam).first()
        if existing:
            return attempt_response(existing)

        questions = list(exam.level.question_bank.filter(is_active=True).prefetch_related("choices"))
        true_false = [question for question in questions if question.question_type == "true_false"]
        multiple_choice = [question for question in questions if question.question_type == "multiple_choice"]
        if len(true_false) < 25 or len(multiple_choice) < 25:
            return Response({"error": "question_bank_incomplete", "message": "This exam is not ready yet."}, status=409)

        selected = random.sample(true_false, 25) + random.sample(multiple_choice, 25)
        random.shuffle(selected)
        try:
            with transaction.atomic():
                attempt = ExamAttempt.objects.create(student=student, exam=exam, max_score=sum(q.points for q in selected))
                AttemptQuestion.objects.bulk_create([
                    AttemptQuestion(
                        attempt=attempt,
                        original_question=question,
                        display_order=index,
                        points_snapshot=question.points,
                        question_text_snapshot=question.prompt,
                        question_type_snapshot=question.question_type,
                        choices_snapshot=[{"id": choice.id, "text": choice.text} for choice in random.sample(list(question.choices.all()), len(question.choices.all()))],
                        correct_answer_snapshot={
                            "choice_id": next(choice.id for choice in question.choices.all() if choice.is_correct),
                            "value": next(choice.text for choice in question.choices.all() if choice.is_correct),
                        },
                    )
                    for index, question in enumerate(selected, start=1)
                ])
        except IntegrityError:
            attempt = get_object_or_404(ExamAttempt, student=student, exam=exam)
        return attempt_response(attempt)


class AttemptDetailView(APIView):
    def get(self, request, attempt_id):
        attempt, error = attempt_for_request(request, attempt_id)
        if error:
            return error
        return attempt_response(attempt)


class AnswerView(APIView):
    def post(self, request, attempt_id):
        attempt, error = attempt_for_request(request, attempt_id)
        if error:
            return error
        if attempt.status == "submitted":
            return Response({"error": "attempt_submitted", "message": "Submitted attempts are read-only."}, status=409)
        question_id = request.data.get("attempt_question_id")
        question = get_object_or_404(attempt.questions.all(), id=question_id)
        try:
            selected_choice, value = answer_values(question, request.data)
        except ValueError as error:
            return Response({"error": "invalid_answer", "message": str(error)}, status=400)
        answer, _ = StudentAnswer.objects.update_or_create(
            attempt_question=question,
            defaults={"selected_choice": selected_choice, "selected_answer_value": value, "answered_at": timezone.now()},
        )
        return Response({"attempt_question_id": question.id, "saved": True, "selected_choice_id": answer.selected_choice_id, "selected_answer_value": answer.selected_answer_value})


class SubmitAttemptView(APIView):
    def post(self, request, attempt_id):
        attempt, error = attempt_for_request(request, attempt_id)
        if error:
            return error
        if attempt.status == "submitted":
            return attempt_response(attempt)
        if attempt.is_expired:
            return Response({"error": "time_expired", "message": "The exam time has expired."}, status=409)

        final_answers = request.data.get("answers", [])
        for item in final_answers:
            question = get_object_or_404(attempt.questions.all(), id=item.get("attempt_question_id"))
            try:
                selected_choice, value = answer_values(question, item)
            except ValueError as error:
                return Response({"error": "invalid_answer", "message": str(error)}, status=400)
            StudentAnswer.objects.update_or_create(
                attempt_question=question,
                defaults={"selected_choice": selected_choice, "selected_answer_value": value, "answered_at": timezone.now()},
            )

        now = timezone.now()
        score = 0
        for question in attempt.questions.select_related("attempt").prefetch_related("answer"):
            answer = getattr(question, "answer", None)
            is_correct = bool(answer and ((answer.selected_choice_id and answer.selected_choice_id == question.correct_answer_snapshot.get("choice_id")) or (answer.selected_answer_value and answer.selected_answer_value == question.correct_answer_snapshot.get("value"))))
            if answer:
                answer.is_correct = is_correct
                answer.points_earned = question.points_snapshot if is_correct else 0
                answer.answered_at = answer.answered_at or now
                answer.save(update_fields=("is_correct", "points_earned", "answered_at"))
                score += answer.points_earned
        attempt.score = score
        attempt.max_score = attempt.max_score or sum(question.points_snapshot for question in attempt.questions.all())
        attempt.percentage = round((score / attempt.max_score) * 100, 2) if attempt.max_score else 0
        attempt.status = "submitted"
        attempt.submitted_at = now
        attempt.save(update_fields=("score", "max_score", "percentage", "status", "submitted_at"))

        from apps.results.models import Result

        Result.objects.update_or_create(
            student=attempt.student,
            exam=attempt.exam,
            defaults={"attempt": attempt, "score": score, "max_score": attempt.max_score, "percentage": attempt.percentage, "submission_status": "submitted"},
        )
        return attempt_response(attempt)
