from django.http import JsonResponse
from django.conf import settings

from .models import User
from .utils.jwt_utils import decode_jwt


class EmailVerificationRequiredMiddleware:
    """Block authenticated-but-unverified users from protected API endpoints."""

    ALLOWED_PATHS = {
        "/api/user/login",
        "/api/user/register",
        "/api/user/verify-email",
        "/api/user/send-verification-email",
        "/api/users/getByToken",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "EMAIL_VERIFICATION_ENABLED", True):
            return self.get_response(request)

        path = request.path or ""

        if not path.startswith("/api/") or path in self.ALLOWED_PATHS:
            return self.get_response(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return self.get_response(request)

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return self.get_response(request)

        payload = decode_jwt(token)
        if not payload:
            return self.get_response(request)

        user_id = payload.get("user_id")
        user = User.objects.filter(id=user_id).only("id", "verified").first()
        if not user:
            return self.get_response(request)

        if not user.verified:
            return JsonResponse(
                {
                    "error": "Email verification required.",
                    "code": "email_not_verified",
                },
                status=403,
            )

        return self.get_response(request)
