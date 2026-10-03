from .models import AuditLog, StaffProfile


ROLE_ORDER = {"viewer": 1, "editor": 2, "administrator": 3}


def staff_role(user):
    if user.is_superuser:
        return "administrator"
    if not user.is_staff:
        return None
    profile, _ = StaffProfile.objects.get_or_create(user=user)
    return profile.role


def has_staff_role(user, minimum_role="viewer"):
    role = staff_role(user)
    return role is not None and ROLE_ORDER[role] >= ROLE_ORDER[minimum_role]


def record_audit(actor, action, target_type, target_id="", details=None):
    return AuditLog.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        details=details or {},
    )
