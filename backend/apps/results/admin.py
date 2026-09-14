from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import ExamSubmission, Result, SectionScore


@admin.register(ExamSubmission)
class ExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "status", "submitted_at", "reviewed_at")
    search_fields = ("student__student_code", "student__full_name", "exam__name")
    list_filter = ("exam", "status", "submitted_at")
    autocomplete_fields = ("student", "exam")


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
