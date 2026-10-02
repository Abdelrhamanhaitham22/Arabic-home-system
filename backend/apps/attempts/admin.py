from django.contrib import admin

from .models import AttemptQuestion, ExamAttempt, StudentAnswer


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "status", "score", "max_score", "percentage", "started_at", "submitted_at")
    list_filter = ("exam", "status", "student__level")
    search_fields = ("student__student_code", "student__full_name", "exam__name")
    readonly_fields = ("started_at", "submitted_at", "score", "max_score", "percentage")


@admin.register(AttemptQuestion)
class AttemptQuestionAdmin(admin.ModelAdmin):
    list_display = ("attempt", "display_order", "question_type_snapshot", "points_snapshot")
    list_filter = ("question_type_snapshot", "attempt__exam")
    search_fields = ("attempt__student__student_code", "question_text_snapshot")
    readonly_fields = tuple(field.name for field in AttemptQuestion._meta.fields)


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt_question", "selected_choice", "is_correct", "points_earned", "answered_at")
    list_filter = ("is_correct", "attempt_question__attempt__exam")
    search_fields = ("attempt_question__attempt__student__student_code",)
    readonly_fields = tuple(field.name for field in StudentAnswer._meta.fields)
