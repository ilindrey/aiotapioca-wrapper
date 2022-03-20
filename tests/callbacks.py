from aioresponses import CallbackResult


def callback_201(*args, **kwargs):
    return CallbackResult(status=201)


def callback_401(*args, **kwargs):
    return CallbackResult(status=401)
