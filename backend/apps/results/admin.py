from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html

from .models import ExamSubmission, Result, SectionScore


@admin.register(ExamSubmission)
class ExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "answer_file_link", "status", "result_status", "submitted_at", "reviewed_at")
    search_fields = ("student__student_code", "student__full_name", "exam__name")
    list_filter = ("exam", "status", "submitted_at")
    autocomplete_fields = ("student", "exam")
    actions = ("start_review",)

    @admin.display(description="Result")
    def result_status(self, submission):
        if not hasattr(submission, "result"):
            return "Not started"
        return "Published" if submission.result.published else "Draft"

    @admin.display(description="Answer file")
    def answer_file_link(self, submission):
        if not submission.answer_file:
            return "No file"
        url = reverse("submission-file", args=(submission.id,))
        return format_html('<a href="{}" target="_blank">Open answer sheet</a>', url)

    @admin.action(description="Start review and create draft results")
    def start_review(self, request, queryset):
        created_count = 0
        for submission in queryset.select_related("student", "exam"):
            _, created = submission.create_draft_result()
            created_count += created
        self.message_user(
            request,
            f"Created {created_count} draft result(s). Open Results to enter section scores.",
            messages.SUCCESS,
        )


class SectionScoreInline(admin.TabularInline):
    model = SectionScore
    extra = 0
    autocomplete_fields = ("section",)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "score", "published", "get_percentage", "created_at")
    search_fields = ("student__student_code", "student__full_name")
    list_filter = ("exam", "published", "created_at")
    autocomplete_fields = ("student", "exam")
    inlines = (SectionScoreInline,)
    actions = ("publish_selected_results",)

    @admin.display(description="Percentage")
    def get_percentage(self, result):
        return f"{result.percentage}%"

    @admin.action(description="Publish selected results")
    def publish_selected_results(self, request, queryset):
        published_count = 0
        for result in queryset:
            try:
                result.publish()
            except ValidationError as error:
                self.message_user(request, f"{result}: {error}", messages.ERROR)
            else:
                published_count += 1
        if published_count:
            self.message_user(request, f"Published {published_count} result(s).", messages.SUCCESS)
