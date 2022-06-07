from inspect import iscoroutinefunction


async def coro_wrap(func, *args, **kwargs):
    if iscoroutinefunction(func):
        result = await func(*args, **kwargs)
    else:
        result = func(*args, **kwargs)
    return result
