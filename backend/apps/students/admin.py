from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_code",
        "full_name",
        "level",
        "phone_number",
        "preferred_language",
        "created_at",
    )
    search_fields = ("student_code", "full_name", "phone_number")
    list_filter = ("level", "preferred_language", "created_at")
    autocomplete_fields = ("level",)
    readonly_fields = ("student_code", "created_at", "updated_at")
