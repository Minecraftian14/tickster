from functools import wraps

from diskcache import Cache, ENOVAL
from diskcache.core import args_to_key, full_name

ONE_DAY = 86400

def make_key(cache: Cache, key_maker, name=None, typed=False, expire=None, tag=None, ignore=()):
    cache.memoize()

    def decorator(func):
        base = (full_name(func),) if name is None else (name,)

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = wrapper.__cache_key__(key_maker(*args, **kwargs))

            result = cache.get(key, default=ENOVAL, retry=True)

            if result is ENOVAL:
                result = func(*args, **kwargs)
                if expire is None or expire > 0:
                    cache.set(key, result, expire, tag=tag, retry=True)

            return result

        def __cache_key__(*args, **kwargs):
            """Make key for cache given function arguments."""
            return args_to_key(base, args, kwargs, typed, ignore)

        wrapper.__cache_key__ = __cache_key__
        return wrapper

    return decorator
