=========
Changelog
=========

4.1.0
=====
- Added a py.typed merker for type hints.

4.0.2
=====
- Added to_dict_by_alias option in TapiocaAdapterPydanticMixin.

4.0.1
=====
- Fixed release

4.0.0
=====
- Added option to specify a session when generating a wrapper.
- Added max_retries_requests flag to limit the number of retries requests.
- Added ability to specify classmethod in parsers.
- Dump and load data in threads. Added more abstract methods to prepare parameters and data for requests or prepare native data.
- Drop support Python 3.6 and below.
- Implemented multiple use of aiohttp.ClientSession, outside the context manager.
- Rework of the library structure. Splitting Tapioca client structure into classes: TapiocaClient, TapiocaClientResource, TapiocaClientExecutor and TapiocaClientResponse.
- Reworked exception handling v.2.
- Minor fixes.

3.8.0
=====
- Added propagate_exception flag after retry_request call.
- Added data parsing mechanism. Parsers can be specified in resource_mapping.
- Reworked exception handling.

3.7.0
=====
- Removed debug option.
- Expanded the possibility of error handling. Added catch aiohttp exceptions.

3.6.0
=====
- Added context transfer to get_request_kwargs method.
- Peddling kwargs to format_data_to_request and serialize_data methods.
- Increased the debugging data output limit.
- Removed api_params argument from get_request_kwargs method.
- Removed PydanticSerializer.
- Added PydanticAdapterMixin.

3.5.0
=====
- migration to orjson

3.4.2
=====
- Fixed requirements.

3.4.1
=====
- Fixed requirements.

3.4.0
=====
- Using aiologger for debugging logs.
- Fix for recursion due to refresh_token flag.
- Added attribute semaphore to TapiocaAdapter.
- Added ability to pass Semaphore as a client or request parameter.
- Added get_resource_mapping method to TapiocaAdapter.
- Fixed an unnecessary request.
- Added serialisation from the pydantic model.
- Reworked flag debug.

3.3.1
=====
- Expanding debugging information.

3.3.0
=====
- The handling of the refresh token parameter was changed.
- Added refresh_token attribute to the TapiocaAdapter class.
- Removed refresh_token_by_default parameter in the tapioca classes.
- Parameters passing was changed in _wrap_in_tapioca and _wrap_in_tapioca_executor.
- Minor fixes.

3.2.4
=====
- Fixed "This instance has no response object" error in _wrap_in_tapioca and _wrap_in_tapioca_executor (empty response in property descendants and pages).

3.2.3
=====
- Returned pass request_method as param in get_request_kwargs.

3.2.2
=====
- Fixed fill resource template url.

3.2.1
=====
- Context transmission was extended.

3.2.0
=====
- Added retry_request and error_handling methods.
- Added context passed to different adapter methods.

3.1.1
=====
- Fixed debugging flag.

3.1.0
=====
- Added PydanticSerializer.
  
3.0.0
=====
- Implementing an asynchronous fork.

2.1.0
=====
- Make ``TapiocaClient`` and ``TapiocaClientExecutor`` pickle-able.

2.0.2
=====
- Updated deprecated collections import
- Adds support for python 3.10

2.0.1
=====
- Updates the list of supported versions in setup.py

2.0
===
- Drops support for python 2.7 and 3.4
- Adds support for python 3.7 and 3.8

1.5.1
=====
- Adds a ``resource_name`` kwarg to the ``get_api_root`` method

1.5
===
- Removes support for Python 3.3


1.4
===
- Adds support to Session requests

1.3
===
- ``refresh_authentication`` should return data about the refresh token process
- If a falsy value is returned by ``refresh_authentication`` the request wont be retried automatically
- Data returned by ``refresh_authentication`` is stored in the tapioca class and can be accessed in the executor via the attribute ``refresh_data``

1.2.3
======
- ``refresh_token_by_default`` introduced to prevent passing ``refresh_token`` on every request.

1.1.10
======
- Fixed bugs regarding ``request_kwargs`` passing over calls
- Fixed bugs regarding external ``serializer`` passing over calls
- Wrapper instatiation now accepts ``default_url_params``

1.1
===
- Automatic refresh token support
- Added Python 3.5 support
- Added support for ``OrderedDict``
- Documentation cleanup

1.0
===
- Data serialization and deserialization
- Access CamelCase attributes using snake_case
- Dependencies are now tied to specific versions of libraries
- ``data`` and ``response`` are now attributes instead of methods in the executor
- Added ``status_code`` attribute to tapioca executor
- Renamed ``status`` exception attribute to ``status_code``
- Fixed return for ``dir`` call on executor, so it's lot easier to explore it
- Multiple improvments to documentation

0.6.0
=====
- Giving access to request_method in ``get_request_kwargs``
- Verifying response content before trying to convert it to json on ``JSONAdapterMixin``
- Support for ``in`` operator
- pep8 improvments

0.5.3
=====
- Adding ``max_pages`` and ``max_items`` to ``pages`` method

0.5.1
=====
- Verifying if there's data before json dumping it on ``JSONAdapterMixin``

0.5.0
=====
- Automatic pagination now requires an explicit ``pages()`` call
- Support for ``len()``
- Attributes of wrapped data can now be accessed via executor
- It's now possible to iterate over wrapped lists

0.4.1
=====
- changed parameters for Adapter's ``get_request_kwargs``. Also, subclasses are expected to call ``super``.
- added mixins to allow adapters to easily choose witch data format they will be dealing with.
- ``ServerError`` and ``ClientError`` are now raised on 4xx and 5xx response status. This behaviour can be customized for each service by overwriting adapter's ``process_response`` method.
