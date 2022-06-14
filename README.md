# AioTapioca-Wrapper

[![Join the chat at https://gitter.im/vintasoftware/tapioca-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/vintasoftware/tapioca-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Build Status](https://travis-ci.org/vintasoftware/tapioca-wrapper.svg?branch=master)](https://travis-ci.org/vintasoftware/tapioca-wrapper)
[![Coverage Status](https://coveralls.io/repos/vintasoftware/tapioca-wrapper/badge.svg?branch=master&service=github)](https://coveralls.io/github/vintasoftware/tapioca-wrapper?branch=master)
[![Current version at PyPI](https://img.shields.io/pypi/v/aiotapioca-wrapper.svg)](https://pypi.python.org/pypi/aiotapioca-wrapper)
![Supported Python Versions](https://img.shields.io/pypi/pyversions/tapioca-wrapper.svg)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/vintasoftware/tapioca-wrapper/master/LICENSE)
[![Codestyle](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

It's an asynchronous fork of [tapioca-wrapper](https://github.com/vintasoftware/tapioca-wrapper) library.

![](docs/static/aiologo.png)

Tapioca helps you generating Python clients for APIs.
APIs wrapped by Tapioca are explorable and follow a simple interaction pattern that works uniformly so developers don't need to learn how to use a new coding interface/style for each service API.

## Usage

First, you need to set up the mapping of the resources you want to work with:

```python
RESOURCE_MAPPING = {
    "test": {
        "resource": "test/{number}/",
        "docs": "http://test.com/docs",
        "spam": "eggs",
        "foo": "bar",
    },
    ...
}
```

Then create an adapter class that will work with resources:
```python
from aiotapioca import JSONAdapterMixin, TapiocaAdapter


class SomeClientAdapter(JSONAdapterMixin, TapiocaAdapter):
    serializer_class = ...  # default SimpleSerializer
    api_root = "https://api.test.com"
    resource_mapping = RESOURCE_MAPPING
```

Generate a class-based wrapper using `generate_wrapper_from_adapter`:
```python
from aiotapioca.adapters import generate_wrapper_from_adapter

SomeClient = generate_wrapper_from_adapter(SomeClientAdapter)
```

Using:

```python
async with SomeClient() as client:
    
    response = await client.test(number=...).get(data=..., 
                                                 params=...)
    print(response.data())
    print(response.response)
    
    response = await client.test(number=...).post(data=..., 
                                                  params=...)
    
    responses = await client.test(number=...).post_batch(data=[..., ...], 
                                                         params=...)
```

For page-by-page traversal, you can use the method of the `pages`:

```python
async with SomeClient() as client:
    result = await client.test(number=...).get()
    async for page in result().pages():
        print(page.data())
        print(page.response)
```

You must also implement the `get_iterator_list` and `get_iterator_next_request_kwargs` methods for it.

## Documentation

Full documentation hosted by [readthedocs](http://aiotapioca-wrapper.readthedocs.org/).

## Flavours

You can find the full list of available tapioca clients [here](http://aiotapioca-wrapper.readthedocs.org/en/stable/flavours.html).

To create new flavours, refer to [Building a wrapper](http://aiotapioca-wrapper.readthedocs.org/en/stable/buildingawrapper.html) in the documentation. There is also a [cookiecutter template](https://github.com/vintasoftware/cookiecutter-tapioca) to help bootstraping new API clients.


## Other resources

- [Contributors](https://github.com/ilindrey/aiotapioca-wrapper/graphs/contributors)
- [Changelog](http://aiotapioca-wrapper.readthedocs.org/en/stable/changelog.html)
- [Blog post explaining the basics about Tapioca](http://www.vinta.com.br/blog/2016/python-api-clients-with-tapioca/)

