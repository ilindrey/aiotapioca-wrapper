from .client import TapiocaClient

__all__ = ("generate_wrapper_from_adapter", "TapiocaInstantiator")


def generate_wrapper_from_adapter(adapter_class, session=None):
    return TapiocaInstantiator(adapter_class, session)


class TapiocaInstantiator:
    def __init__(self, adapter_class, session=None):
        self.adapter_class = adapter_class
        self._session = session

    def __call__(self, serializer_class=None, session=None, **kwargs):
        return TapiocaClient(
            self.adapter_class(serializer_class=serializer_class),
            session=session or self._session,
            api_params=kwargs,
        )
