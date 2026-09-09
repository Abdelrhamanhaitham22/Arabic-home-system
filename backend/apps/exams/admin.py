from django.contrib import admin

from .models import Exam


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "max_score", "exam_date", "created_at")
    search_fields = ("name",)
    list_filter = ("exam_date",)
