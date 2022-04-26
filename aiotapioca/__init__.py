__author__ = "Filipe Ximenes, Andrey Ilin"
__email__ = "andreyilin@fastmail.com"
__version__ = "3.7.0"


from .adapters import (
    generate_wrapper_from_adapter,
    TapiocaAdapter,
    FormAdapterMixin,
    JSONAdapterMixin,
    XMLAdapterMixin,
    PydanticAdapterMixin,
)
from .serializers import BaseSerializer, SimpleSerializer


__all__ = (
    "generate_wrapper_from_adapter",
    "TapiocaAdapter",
    "FormAdapterMixin",
    "JSONAdapterMixin",
    "XMLAdapterMixin",
    "PydanticAdapterMixin",
    "BaseSerializer",
    "SimpleSerializer",
)
