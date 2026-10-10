from rest_framework.throttling import SimpleRateThrottle, AnonRateThrottle, UserRateThrottle
from django.core.cache import cache
from decouple import config

class ExponentialBackoffThrottle(SimpleRateThrottle):
    # Base class for exponential backoff throttling
    cache_format = 'throttle_%(scope)s_%(ident)s'
    base_time = 1  # 1 second base

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
    
    def allow_request(self, request, view):
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Keep history records that occurred within the maximum wait window we want to track
        # say 10 minutes max window for exponential calculation
        max_window = 600 
        while self.history and self.history[-1] <= self.now - max_window:
            self.history.pop()

        # Number of failures determines backoff
        failures = len(self.history)
        if failures >= self.num_requests:
            # Calculate exponential wait: base_time * (2 ^ (failures - num_requests))
            wait_time = self.base_time * (2 ** (failures - self.num_requests))
            # Check if wait time has passed since the last failure
            if self.now - self.history[0] < wait_time:
                return self.throttle_failure()
            
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, max_window)
        return True

    def wait(self):
        if self.history:
            failures = len(self.history)
            wait_time = self.base_time * (2 ** (failures - self.num_requests))
            remaining_duration = wait_time - (self.now - self.history[0])
            return max(remaining_duration, 1)
        return None


class AuthIPThrottle(ExponentialBackoffThrottle):
    scope = 'auth_ip'
    
    def __init__(self):
        # Default 5 req per minute for auth IP
        self.num_requests = config('THROTTLE_AUTH_IP_REQS', default=5, cast=int)
        self.rate = f"{self.num_requests}/min"
        super().__init__()

class AuthAccountThrottle(ExponentialBackoffThrottle):
    scope = 'auth_account'
    
    def __init__(self):
        self.num_requests = config('THROTTLE_AUTH_ACCOUNT_REQS', default=3, cast=int)
        self.rate = f"{self.num_requests}/min"
        super().__init__()

    def get_cache_key(self, request, view):
        # Identity by email provided in request if any
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = request.data.get('email') or self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

class PublicRateThrottle(AnonRateThrottle):
    scope = 'public'
    
    def __init__(self):
        self.rate = config('THROTTLE_PUBLIC_RATE', default='100/min')
        super().__init__()

class UserActionRateThrottle(UserRateThrottle):
    scope = 'user_action'
    
    def __init__(self):
        self.rate = config('THROTTLE_USER_RATE', default='1000/min')
        super().__init__()
