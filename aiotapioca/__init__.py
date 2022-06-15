__author__ = "Filipe Ximenes, Andrey Ilin"
__email__ = "andreyilin@fastmail.com"
__version__ = "4.0.1"


from .adapters import (
    TapiocaAdapter,
    TapiocaAdapterForm,
    TapiocaAdapterFormMixin,
    TapiocaAdapterJSON,
    TapiocaAdapterJSONMixin,
    TapiocaAdapterPydantic,
    TapiocaAdapterPydanticMixin,
    TapiocaAdapterXML,
    TapiocaAdapterXMLMixin,
)
from .exceptions import (
    ClientError,
    ResponseProcessException,
    ServerError,
    TapiocaException,
)
from .generate import generate_wrapper_from_adapter
from .serializers import BaseSerializer, SimpleSerializer

__all__ = (
    "TapiocaAdapter",
    "TapiocaAdapterForm",
    "TapiocaAdapterFormMixin",
    "TapiocaAdapterJSON",
    "TapiocaAdapterJSONMixin",
    "TapiocaAdapterPydantic",
    "TapiocaAdapterPydanticMixin",
    "TapiocaAdapterXML",
    "TapiocaAdapterXMLMixin",
    "ClientError",
    "ResponseProcessException",
    "ServerError",
    "TapiocaException",
    "generate_wrapper_from_adapter",
    "BaseSerializer",
    "SimpleSerializer",
)
