from django.contrib import admin

from .models import HomepageVideo


@admin.register(HomepageVideo)
class HomepageVideoAdmin(admin.ModelAdmin):
    list_display = ("title_ar", "title_ru", "order", "is_active", "updated_at")
    list_filter = ("is_active",)
    list_editable = ("order", "is_active")
    search_fields = ("title_ar", "title_ru", "description_ar", "description_ru")
