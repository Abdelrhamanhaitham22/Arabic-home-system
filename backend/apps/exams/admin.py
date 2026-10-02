from django.contrib import admin

from .models import Exam, ExamSection, Level, Question, QuestionChoice


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active", "question_bank_count")
    list_filter = ("is_active",)
    search_fields = ("name",)

    @admin.display(description="Active questions")
    def question_bank_count(self, level):
        return level.question_bank.filter(is_active=True).count()


@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "exam", "max_score", "order")
    list_filter = ("exam",)
    search_fields = ("name", "exam__name")
    autocomplete_fields = ("exam",)


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
    autocomplete_fields = ("level", "section")
    inlines = (QuestionChoiceInline,)


class ExamSectionInline(admin.TabularInline):
    model = ExamSection
    extra = 0
    max_num = 1
    can_delete = False


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "name", "level", "max_score", "status", "time_limit_minutes",
        "exam_date", "opens_at", "closes_at",
    )
    search_fields = ("name",)
    list_filter = ("level", "status", "exam_date")
    autocomplete_fields = ("level",)
    inlines = (ExamSectionInline,)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)
