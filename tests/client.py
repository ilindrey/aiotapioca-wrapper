from typing import Any, Dict

from aiotapioca import TapiocaAdapterJSON, generate_wrapper_from_adapter


test = {
    "resource": "test/",
    "docs": "http://www.example.org",
}

RESOURCE_MAPPING: Dict[str, Any] = {
    "test": test,
    "user": {"resource": "user/{id}/", "docs": "http://www.example.org/user"},
    "resource": {
        "resource": "resource/{number}/",
        "docs": "http://www.example.org/resource",
        "spam": "eggs",
        "foo": "bar",
    },
    "another_root": {
        "resource": "another-root/",
        "docs": "http://www.example.org/another-root",
    },
}


class SimpleClientAdapter(TapiocaAdapterJSON):
    api_root = "https://api.example.org"
    resource_mapping = RESOURCE_MAPPING

    def get_api_root(self, api_params, **kwargs):
        if kwargs.get("resource_name") == "another_root":
            return "https://api.another.com/"
        else:
            return self.api_root

    def get_iterator_list(self, data, **kwargs):
        return data["data"]

    def get_iterator_next_request_kwargs(
        self, request_kwargs, data, response, **kwargs
    ):
        paging = data.get("paging")
        if not paging:
            return
        url = paging.get("next")

        if url:
            return {**request_kwargs, "url": url}


SimpleClient = generate_wrapper_from_adapter(SimpleClientAdapter)
