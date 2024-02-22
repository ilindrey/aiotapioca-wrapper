Release v4.3.0 (2024-02-22)
--------------------------
- Added support pydantic v2. If you need pydantic v1 you need to use an older version of the library.
- Drop support Python 3.7 and below.
- Minor fixes.

Release v4.2.1 (2024-01-18)
--------------------------
- Fixed check of success statuses.

Release v4.2.0 (2022-10-19)
--------------------------
- Added linters, mypy and pre-commit hooks.
- Added CI for tests, pre-commit and release.
- Migrate to PDM.
- Optional support orjson and ujson when available.
- Optional dependencies xml and pydantic mixins.
- Replaced setup.py to pyproject.toml.

Release v4.1.1 (2022-06-21)
--------------------------
- Added a py.typed marker for type hints.

Release v4.0.2 (2022-06-17)
--------------------------
- Added to_dict_by_alias option in TapiocaAdapterPydanticMixin.

Release v4.0.1 (2022-06-15)
--------------------------
- Added option to specify a session when generating a wrapper.
- Added max_retries_requests flag to limit the number of retries requests.
- Added ability to specify classmethod in parsers.
- Dump and load data in threads. Added more abstract methods to prepare parameters and data for requests or prepare native data.
- Drop support Python 3.6 and below.
- Implemented multiple use of aiohttp.ClientSession, outside the context manager.
- Rework of the library structure. Splitting Tapioca client structure into classes: TapiocaClient, TapiocaClientResource, TapiocaClientExecutor and TapiocaClientResponse.
- Reworked exception handling v.2.
- Minor fixes.

Release v3.8.0 (2022-05-15)
--------------------------
- Added propagate_exception flag after retry_request call.
- Added data parsing mechanism. Parsers can be specified in resource_mapping.
- Reworked exception handling.

Release v3.7.0 (2022-04-27)
--------------------------
- Removed debug option.
- Expanded the possibility of error handling. Added catch aiohttp exceptions.

Release v3.6.0 (2022-04-22)
--------------------------
- Added context transfer to get_request_kwargs method.
- Peddling kwargs to format_data_to_request and serialize_data methods.
- Increased the debugging data output limit.
- Removed api_params argument from get_request_kwargs method.
- Removed PydanticSerializer.
- Added PydanticAdapterMixin.

Release v3.5.0 (2022-04-12)
--------------------------
- migration to orjson

Release v3.4.2 (2022-04-08)
--------------------------
- Fixed requirements.

Release v3.4.1 (2022-04-08)
--------------------------
- Fixed requirements.

Release v3.4.0 (2022-04-0)
--------------------------
- Using aiologger for debugging logs.
- Fix for recursion due to refresh_token flag.
- Added attribute semaphore to TapiocaAdapter.
- Added ability to pass Semaphore as a client or request parameter.
- Added get_resource_mapping method to TapiocaAdapter.
- Fixed an unnecessary request.
- Added serialisation from the pydantic model.
- Reworked flag debug.

Release v3.3.1 (2022-03-24)
--------------------------
- Expanding debugging information.

Release v3.3.0 (2022-03-24)
--------------------------
- The handling of the refresh token parameter was changed.
- Added refresh_token attribute to the TapiocaAdapter class.
- Removed refresh_token_by_default parameter in the tapioca classes.
- Parameters passing was changed in _wrap_in_tapioca and _wrap_in_tapioca_executor.
- Minor fixes.

Release v3.2.4 (2022-03-23)
--------------------------
- Fixed "This instance has no response object" error in _wrap_in_tapioca and _wrap_in_tapioca_executor (empty response in property descendants and pages).

Release v3.2.3 (2022-03-22)
--------------------------
- Returned pass request_method as param in get_request_kwargs.

Release v3.2.2 (2022-03-22)
--------------------------
- Fixed fill resource template url.

Release v3.2.1 (2022-03-22)
--------------------------
- Context transmission was extended.

Release v3.2.0 (2022-03-22)
--------------------------
- Added retry_request and error_handling methods.
- Added context passed to different adapter methods.

Release v3.1.1 (2022-03-21)
--------------------------
- Fixed debugging flag.

Release v3.1.0 (2022-03-21)
--------------------------
- Added PydanticSerializer.

Release v3.0.0 (2022-03-21)
--------------------------
- Implementing an asynchronous fork.

Release v2.1.0 (2022-03-19)
--------------------------
- Make ``TapiocaClient`` and ``TapiocaClientExecutor`` pickle-able.

Release v2.0.2 (2022-02-25)
--------------------------
- Updated deprecated collections import
- Adds support for python 3.10

Release v2.0.1 (2020-01-25)
--------------------------
- Updates the list of supported versions in setup.py

Release v2.0.0 (2020-01-25)
--------------------------
- Drops support for python 2.7 and 3.4
- Adds support for python 3.7 and 3.8

Release v1.5.1 (2019-04-19)
--------------------------
- Adds a ``resource_name`` kwarg to the ``get_api_root`` method

Release v1.5.0 (2019-04-19)
--------------------------
- Removes support for Python 3.3

Release v1.4.3 (2017-06-15)
--------------------------

Release v1.4.1 (2017-05-25)
--------------------------

Release v1.4.0 (2017-03-28)
--------------------------
- Adds support to Session requests

Release v1.3.0 (2017-01-20)
--------------------------
- ``refresh_authentication`` should return data about the refresh token process
- If a falsy value is returned by ``refresh_authentication`` the request wont be retried automatically
- Data returned by ``refresh_authentication`` is stored in the tapioca class and can be accessed in the executor via the attribute ``refresh_data``

Release v1.2.3 (2016-09-28)
--------------------------
- ``refresh_token_by_default`` introduced to prevent passing ``refresh_token`` on every request.

Release v1.2.2 (2016-04-23)
--------------------------

Release v1.2.1 (2016-01-02)
--------------------------

Release v1.1.12 (2016-05-31)
---------------------------

Release v1.1.11 (2016-05-31)
---------------------------

Release v1.1.10 (2016-03-27)
---------------------------
- Fixed bugs regarding ``request_kwargs`` passing over calls
- Fixed bugs regarding external ``serializer`` passing over calls
- Wrapper instatiation now accepts ``default_url_params``

Release v1.1.9 (2016-03-27)
--------------------------

Release v1.1.8 (2016-03-27)
--------------------------

Release v1.1.7 (2016-03-27)
--------------------------

Release v1.1.6 (2016-02-29)
--------------------------

Release v1.1.4 (2016-02-27)
--------------------------

Release v1.1.0 (2016-02-27)
--------------------------
- Automatic refresh token support
- Added Python 3.5 support
- Added support for ``OrderedDict``
- Documentation cleanup

Release v1.0.0 (2015-11-10)
--------------------------
- Data serialization and deserialization
- Access CamelCase attributes using snake_case
- Dependencies are now tied to specific versions of libraries
- ``data`` and ``response`` are now attributes instead of methods in the executor
- Added ``status_code`` attribute to tapioca executor
- Renamed ``status`` exception attribute to ``status_code``
- Fixed return for ``dir`` call on executor, so it's lot easier to explore it
- Multiple improvments to documentation

Release v0.6.0 (2015-09-23)
--------------------------
- Giving access to request_method in ``get_request_kwargs``
- Verifying response content before trying to convert it to json on ``JSONAdapterMixin``
- Support for ``in`` operator
- pep8 improvments

Release v0.5.3 (2015-04-10)
--------------------------
- Adding ``max_pages`` and ``max_items`` to ``pages`` method

Release v0.5.1 (2015-08-06)
--------------------------
- Verifying if there's data before json dumping it on ``JSONAdapterMixin``

Release v0.5.0 (2015-08-05)
--------------------------
- Automatic pagination now requires an explicit ``pages()`` call
- Support for ``len()``
- Attributes of wrapped data can now be accessed via executor
- It's now possible to iterate over wrapped lists

Release v0.4.1 (2015-08-01)
--------------------------
- changed parameters for Adapter's ``get_request_kwargs``. Also, subclasses are expected to call ``super``.
- added mixins to allow adapters to easily choose witch data format they will be dealing with.
- ``ServerError`` and ``ClientError`` are now raised on 4xx and 5xx response status. This behaviour can be customized for each service by overwriting adapter's ``process_response`` method.
