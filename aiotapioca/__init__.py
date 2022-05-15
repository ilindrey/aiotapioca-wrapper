__author__ = "Filipe Ximenes, Andrey Ilin"
__email__ = "andreyilin@fastmail.com"
__version__ = "3.8.0"


from .adapters import (
    FormAdapterMixin,
    JSONAdapterMixin,
    PydanticAdapterMixin,
    TapiocaAdapter,
    XMLAdapterMixin,
    generate_wrapper_from_adapter,
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
