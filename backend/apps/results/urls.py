from django.urls import path

from .views import ResultLookupView


urlpatterns = [
    path("<str:student_code>/", ResultLookupView.as_view(), name="result-lookup"),
]
