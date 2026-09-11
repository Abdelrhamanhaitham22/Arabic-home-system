from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import StudentRegistrationSerializer


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set."})


@require_GET
def teacher_session(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"authenticated": False}, status=401)
    return JsonResponse({"authenticated": True})


@require_POST
def teacher_login(request):
    username = request.POST.get("username", "")
    password = request.POST.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_staff:
        return JsonResponse({"detail": "Invalid teacher credentials."}, status=401)
    login(request, user)
    return JsonResponse({"detail": "Login successful."})


@require_POST
def teacher_logout(request):
    logout(request)
    return JsonResponse({"detail": "Logout successful."})


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True), name="dispatch")
class RegisterStudentView(APIView):
    permission_classes = [IsTeacher]

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        return Response(
            {
                "message": _("Registration completed successfully."),
                "student_code": student.student_code,
                "full_name": student.full_name,
            },
            status=status.HTTP_201_CREATED,
        )
