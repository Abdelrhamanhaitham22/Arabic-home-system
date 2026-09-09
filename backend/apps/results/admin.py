from django.contrib import admin

from .models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "score", "get_percentage", "created_at")
    search_fields = ("student__student_code", "student__full_name")
    list_filter = ("exam", "created_at")
    autocomplete_fields = ("student", "exam")

    @admin.display(description="Percentage")
    def get_percentage(self, result):
        return f"{result.percentage}%"
