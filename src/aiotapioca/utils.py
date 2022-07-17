from inspect import iscoroutinefunction

__all__ = ("coro_wrap",)


async def coro_wrap(func, *args, **kwargs):
    if iscoroutinefunction(func):
        result = await func(*args, **kwargs)
    else:
        result = func(*args, **kwargs)
    return result
