from .client import TapiocaClient


__all__ = ("generate_wrapper_from_adapter", "TapiocaInstantiator")


def generate_wrapper_from_adapter(adapter_class, session=None, sync_mode=False):
    return TapiocaInstantiator(adapter_class, session, sync_mode)


class TapiocaInstantiator:
    def __init__(self, adapter_class, session=None, sync_mode=False):
        self.adapter_class = adapter_class
        self._session = session
        self._sync_mode = sync_mode

    def __call__(self, serializer_class=None, session=None, **kwargs):
        return TapiocaClient(
            self.adapter_class(
                serializer_class=serializer_class, sync_mode=self._sync_mode
            ),
            session=session or self._session,
            api_params=kwargs,
        )
