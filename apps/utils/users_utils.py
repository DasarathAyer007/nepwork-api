from rest_framework.request import Request

from apps.users.models import User


def get_auth_user(request: Request) -> User | None:
    user = request.user
    if not user.is_authenticated:
        return None
    return user
