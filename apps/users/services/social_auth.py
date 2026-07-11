# accounts/social_auth.py
import requests
from django.conf import settings
from django.db import transaction
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from ..models import SocialAccount, User

# ---------------------------------------------------------------------
# TOKEN VERIFICATION (unchanged)
# ---------------------------------------------------------------------


def verify_google_token(token):
    try:
        idinfo = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise ValueError(f"Invalid Google token: {e}")

    if not idinfo.get("email_verified", False):
        raise ValueError("Google account email is not verified")

    return {
        "email": idinfo["email"],
        "full_name": idinfo.get("name", ""),
        "provider_user_id": idinfo["sub"],
        "avatar_url": idinfo.get("picture", ""),
        "raw": idinfo,
    }


def verify_facebook_token(access_token):
    debug_resp = requests.get(
        "https://graph.facebook.com/debug_token",
        params={
            "input_token": access_token,
            "access_token": f"{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}",
        },
        timeout=10,
    ).json()

    data = debug_resp.get("data", {})
    if (
        not data.get("is_valid")
        or data.get("app_id") != settings.FACEBOOK_APP_ID
    ):
        raise ValueError("Invalid Facebook token")

    profile = requests.get(
        "https://graph.facebook.com/me",
        params={
            "fields": "id,name,email,picture.type(large)",
            "access_token": access_token,
        },
        timeout=10,
    ).json()

    if "email" not in profile:
        raise ValueError(
            "Facebook did not return an email. The user may have denied the email "
            "permission, or their Facebook account has no verified email."
        )

    return {
        "email": profile["email"],
        "full_name": profile.get("name", ""),
        "provider_user_id": profile["id"],
        "avatar_url": profile.get("picture", {}).get("data", {}).get("url", ""),
        "raw": profile,
    }


# ---------------------------------------------------------------------
# GET-OR-CREATE using SocialAccount
# ---------------------------------------------------------------------


def _unique_username_from_email(email):
    base_username = email.split("@")[0]
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    return username


def get_or_create_social_user(info, provider):
    """
    info = { email, full_name, provider_user_id, avatar_url, raw }
    provider = "google" or "facebook"

    Returns (user, created) where created=True only for a brand-new User row.
    """
    provider_id = info["provider_user_id"]
    email = info["email"]

    with transaction.atomic():
        # --- Case 1: returning social login — SocialAccount already exists ---
        social_account = (
            SocialAccount.objects.select_for_update()
            .filter(provider=provider, provider_id=provider_id)
            .select_related("user")
            .first()
        )

        if social_account:
            # keep cached fields fresh (avatar/email can change on the provider side)
            social_account.email = email
            social_account.avatar_url = info.get("avatar_url", "")
            social_account.extra_data = info.get("raw")
            social_account.save(
                update_fields=[
                    "email",
                    "avatar_url",
                    "extra_data",
                    "updated_at",
                ]
            )
            return social_account.user, False

        # --- Case 2: existing User (local or another provider), linking this provider for the first time ---
        user = User.objects.select_for_update().filter(email=email).first()
        created = False

        if not user:
            # --- Case 3: brand new user ---
            user = User.objects.create(
                username=_unique_username_from_email(email),
                email=email,
                full_name=info.get("full_name", ""),
                is_active=True,
            )
            user.set_unusable_password()
            user.save()
            created = True
        elif not user.is_active:
            # provider already verified this email — trust it
            user.is_active = True
            user.save(update_fields=["is_active"])

        # link the provider to this user (new or existing)
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_id=provider_id,
            email=email,
            avatar_url=info.get("avatar_url", ""),
            extra_data=info.get("raw"),
        )

        return user, created
