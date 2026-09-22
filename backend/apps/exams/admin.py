from django.contrib import admin

from .models import Exam, ExamSection, Level


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "exam", "max_score", "order")
    list_filter = ("exam",)
    search_fields = ("name", "exam__name")
    autocomplete_fields = ("exam",)


class ExamSectionInline(admin.TabularInline):
    model = ExamSection
    extra = 0


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "max_score", "status", "exam_date", "opens_at", "closes_at")
    search_fields = ("name",)
    list_filter = ("level", "status", "exam_date")
    autocomplete_fields = ("level",)
    inlines = (ExamSectionInline,)
