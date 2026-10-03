from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog, HomepageVideo, StaffProfile
from .serializers import HomepageVideoSerializer
from .services import has_staff_role, record_audit, staff_role


User = get_user_model()


def health_check(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


@api_view(["GET"])
def homepage_videos(request):
    videos = HomepageVideo.objects.filter(is_active=True)
    return Response(HomepageVideoSerializer(videos, many=True, context={"request": request}).data)


def staff_error(request, minimum_role="viewer"):
    if not request.user.is_authenticated or not has_staff_role(request.user, minimum_role):
        return Response({"message": "Staff access required."}, status=status.HTTP_403_FORBIDDEN)
    return None


class StaffAccountView(APIView):
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"message": "Super administrator access required."}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.filter(is_staff=True).select_related("staff_profile").order_by("username")
        return Response([self.serialize_user(user) for user in users])

    def post(self, request):
        if not request.user.is_superuser:
            return Response({"message": "Super administrator access required."}, status=status.HTTP_403_FORBIDDEN)
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))
        role = str(request.data.get("role", "viewer"))
        if not username or not password or role not in dict(StaffProfile.ROLE_CHOICES):
            return Response({"message": "Username, password, and a valid role are required."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username__iexact=username).exists():
            return Response({"message": "This username already exists."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(password)
        except ValidationError as error:
            return Response({"message": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=username, password=password, is_active=True, is_staff=True)
        StaffProfile.objects.create(user=user, role=role)
        record_audit(request.user, "staff.created", "User", user.id, {"username": username, "role": role})
        return Response(self.serialize_user(user), status=status.HTTP_201_CREATED)

    def patch(self, request, user_id):
        if not request.user.is_superuser:
            return Response({"message": "Super administrator access required."}, status=status.HTTP_403_FORBIDDEN)
        user = User.objects.filter(id=user_id, is_staff=True).first()
        if user is None:
            return Response({"message": "Staff account not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.id == request.user.id and request.data.get("is_active") is False:
            return Response({"message": "You cannot disable your own account."}, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = StaffProfile.objects.get_or_create(user=user)
        if "role" in request.data:
            if request.data["role"] not in dict(StaffProfile.ROLE_CHOICES):
                return Response({"message": "Invalid staff role."}, status=status.HTTP_400_BAD_REQUEST)
            profile.role = request.data["role"]
            profile.save(update_fields=("role", "updated_at"))
        if "is_active" in request.data:
            user.is_active = bool(request.data["is_active"])
            user.save(update_fields=("is_active",))
        record_audit(request.user, "staff.updated", "User", user.id, self.serialize_user(user))
        return Response(self.serialize_user(user))

    @staticmethod
    def serialize_user(user):
        return {
            "id": user.id,
            "username": user.get_username(),
            "role": staff_role(user),
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        }


class AuditLogView(APIView):
    def get(self, request):
        if (error := staff_error(request, "administrator")):
            return error
        logs = AuditLog.objects.select_related("actor")[:100]
        return Response([{
            "id": log.id,
            "actor": log.actor.get_username() if log.actor else "System",
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "created_at": log.created_at,
        } for log in logs])
