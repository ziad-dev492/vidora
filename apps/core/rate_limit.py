from functools import wraps
from hashlib import sha256
import logging
from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def rate_limit(limit, seconds, label=None):
    """Throttle mutating requests by IP and account; keep GET/HEAD requests unaffected."""
    def decorate(view):
        scope = label or f"{view.__module__}.{view.__name__}"
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
                return view(request, *args, **kwargs)
            user_id = request.user.pk if getattr(request, "user", None) is not None and request.user.is_authenticated else "anon"
            identity = f"{request.META.get('REMOTE_ADDR', 'unknown')}:{user_id}:{scope}"
            key = "vidora:ratelimit:" + sha256(identity.encode("utf-8")).hexdigest()
            try:
                if cache.add(key, 1, timeout=seconds):
                    count = 1
                else:
                    try:
                        count = cache.incr(key)
                    except ValueError:
                        cache.set(key, 1, timeout=seconds)
                        count = 1
            except Exception:
                logger.exception("Rate-limit cache unavailable for %s", scope)
                return view(request, *args, **kwargs)
            if count > limit:
                response = HttpResponse("تم تجاوز عدد الطلبات المسموح. حاول لاحقًا.", status=429, content_type="text/plain; charset=utf-8")
                response["Retry-After"] = str(seconds)
                return response
            return view(request, *args, **kwargs)
        return wrapped
    return decorate
