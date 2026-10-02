import csv

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.core.exceptions import ValidationError

from .models import Exam, Level, Question, QuestionChoice
from .importers import CSV_COLUMNS, import_question_bank


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active", "question_bank_count")
    list_filter = ("is_active",)
    search_fields = ("name",)

    change_form_template = "admin/exams/level/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<int:level_id>/import-questions/", self.admin_site.admin_view(self.import_questions), name="exams_level_import_questions"),
            path("question-bank-template.csv", self.admin_site.admin_view(self.question_bank_template), name="exams_question_bank_template"),
        ]
        return custom_urls + urls

    def import_questions(self, request, level_id):
        level = get_object_or_404(Level, id=level_id)
        if request.method == "POST":
            try:
                imported_count = import_question_bank(level, request.FILES["csv_file"])
            except (KeyError, ValidationError) as error:
                message = error.messages[0] if isinstance(error, ValidationError) else "Choose a CSV file."
                self.message_user(request, message, level=messages.ERROR)
            else:
                self.message_user(request, f"Imported {imported_count} questions into {level.name}.", messages.SUCCESS)
                return redirect(reverse("admin:exams_level_change", args=(level.id,)))
        return render(request, "admin/exams/level/import_questions.html", {"level": level, "title": "Import question bank"})

    def question_bank_template(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="question_bank_template.csv"'
        writer = csv.writer(response)
        writer.writerow(CSV_COLUMNS)
        writer.writerow((1, "Is Arabic a language?", "true_false", 1, "True", "true", "False", "false", "", "", "", ""))
        writer.writerow((2, "Choose the capital of Egypt.", "multiple_choice", 1, "Cairo", "true", "Alexandria", "false", "Giza", "false", "Luxor", "false"))
        return response

    @admin.display(description="Active questions")
    def question_bank_count(self, level):
        return level.question_bank.filter(is_active=True).count()


@admin.register(QuestionChoice)
class QuestionChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "text", "is_correct")
    list_filter = ("is_correct",)
    search_fields = ("text", "question__prompt")
    autocomplete_fields = ("question",)


class QuestionChoiceInline(admin.TabularInline):
    model = QuestionChoice
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "level", "question_type", "points", "bank_order", "is_active")
    list_filter = ("question_type", "level", "is_active")
    search_fields = ("prompt",)
    autocomplete_fields = ("level",)
    inlines = (QuestionChoiceInline,)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "name", "level", "max_score", "status", "time_limit_minutes",
        "exam_date", "opens_at", "closes_at",
    )
    search_fields = ("name",)
    list_filter = ("level", "status", "exam_date")
    autocomplete_fields = ("level",)
