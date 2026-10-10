from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authentication backend that allows logging in with either username or email.
    Works seamlessly for Django Admin and standard authentication.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("email")

        if not username or not password:
            return None

        username_clean = str(username).strip()
        try:
            user = User.objects.filter(
                Q(username__iexact=username_clean) | Q(email__iexact=username_clean)
            ).first()
            if user and user.check_password(password):
                return user
        except Exception:
            return None

        return None
