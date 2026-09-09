from django.db import connection
from django.http import JsonResponse


def health_check(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})
