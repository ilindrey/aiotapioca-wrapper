from contextlib import suppress
from inspect import iscoroutinefunction


__all__ = ("coro_wrap",)


async def coro_wrap(func, *args, **kwargs):
    if iscoroutinefunction(func):
        result = await func(*args, **kwargs)
    else:
        result = func(*args, **kwargs)
    return result


def get_json_lib():
    with suppress(ImportError):
        import orjson as json  # type: ignore

    if not json:
        with suppress(ImportError):
            import ujson as json  # type: ignore

    if not json:
        import json

    return json
