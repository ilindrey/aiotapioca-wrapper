==========
Exceptions
==========

Catching API errors
===================

AioTapioca supports 2 main types of exceptions: ``ClientError`` and ``ServerError``. The default implementation raises ``ClientError`` for HTTP response 4xx status codes and ``ServerError`` for 5xx status codes. Since each API has its own ways of reporting errors and not all of them follow HTTP recommendations for status codes, this can be overriden by each implemented client to reflect its behaviour. Both of these exceptions extend ``TapiocaException`` which can be used to catch errors in a more generic way.


.. class:: TapiocaException

Base class for aiotapioca exceptions. Example usage:

.. code-block:: python

	from aiotapioca.exceptions import TapiocaException

	try:
		await cli.fetch_something().get()
	except TapiocaException, e:
		print("API call failed with error %s", e.status_code)

You can also access a aiotapioca client that contains response data from the exception:

.. code-block:: python

	from aiotapioca.exceptions import TapiocaException

	try:
		await cli.fetch_something().get()
	except TapiocaException, e:
		print(e.client().data)

.. class:: ClientError

Default exception for client errors. Extends from ``TapiocaException``.

.. class:: ServerError

Default exception for server errors. Extends from ``TapiocaException``.
