from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication class that reads the JWT access token from:
    1. HttpOnly 'access_token' cookie
    2. Fallback to 'Authorization: Bearer <token>' header
    """
    def authenticate(self, request):
        # 1. Try to read token from HttpOnly cookie
        raw_token = request.COOKIES.get("access_token")

        # 2. Fallback to standard Authorization header
        if raw_token is None:
            header = self.get_header(request)
            if header is not None:
                raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
