========
Features
========

Here are some features aiotapioca supports. The wrapper you are using may support them or not, it will depend on the `aiotapioca-wrapper` version it is tied to and if the developer implemented the methods needed to support the feature. Either way, if you find yourself in a situation where you need one of these features, clone the wrapper, update the `aiotapioca-wrapper` version to the latest one, implement the features you need and submit a pull request to the developer. You will be helping a lot of people!


TapiocaClient
=============

The first object you get after you instanciate a aiotapioca wrapper is an instance of the ``TapiocaClient`` class. This class is capable of accessing the API endpoints of the wrapper and traversing response objects. No other action besides those can be achieved from a ``TapiocaClient``. To retrieve the raw data returned from the API call you will need to transform it in a ``TapiocaClientExecutor``.

**TODO: add examples**

Default URL params
------------------

Sometimes URLs templates need parameters that will be repeated across all API calls. For example, an user id:

.. code-block:: bash

	http://www.someapi.com/{user_id}/resources/
	http://www.someapi.com/{user_id}/resources/{resource_id}/
	http://www.someapi.com/{user_id}/other-resources/{other_id}/


In this cases you can instantiate the wrapper passing a ``default_url_params`` parameter, and they will be used automatically to fill URL templates.

.. code-block:: python

	cli = MyWrapper(access_token='some_token', default_url_params={'user_id': 123456}):
	cli.resources() # http://www.someapi.com/123456/resources/

Using an existing requests.Session
----------------------------------

Requests provides access to a number of advanced features by letting users maintain a `Session object`_.

To use these features you can create a ``TapiocaClient`` with an existing session by passing it to the new client as the ``session`` parameter:

.. code-block:: python

    session = aiohttp.ClientSession()
    async with MyWrapper(access_token='some_token', session=session) as cli:
		cli.resources() # http://www.someapi.com/123456/resources/

This allows us to perform some interesting operations without having to support them directly in ``TapiocaClient`` and instantiate it using the ``async with`` construct.
For example caching for github requests using `cachecontrol`_:

.. code-block:: python

    from cachecontrol import CacheControl
    from cachecontrol.caches import FileCache
    import requests
    import tapioca_github

    session = CacheControl(requests.Session(), cache=FileCache('webcache'))
    gh = tapioca_github.Github(client_id='some_id', access_token='some_token', session=session)
    response  = gh.repo_single(owner="ilindrey", repo="aiotapioca-wrapper").get()
    repo_data = response().data

This will cache the E-tags provided by github to the folder `webcache`.

.. _Session object: http://docs.python-requests.org/en/master/user/advanced/#session-objects
.. _cachecontrol: https://cachecontrol.readthedocs.io/en/latest/

TapiocaClientExecutor
=====================

Every time you ``call`` in ``TapiocaClient`` you will get a ``TapiocaClientExecutor``. Here are the features available in a ``TapiocaClientExecutor``:

Accessing raw response data
---------------------------

To access the raw data contained in the executor, use the ``data`` **attribute**. To access the raw response, use the ``response`` **attribute**. To access the status code of the response, use the ``status`` **attribute**.

.. code-block:: python

    cli = MyWrapper(access_token='some_token')

	response = await cli.some_resource().get()

	data = response.data()
	response = response.response  # return aiohttp.ClientResponse
	status = response.status


HTTP calls
----------

Executors have access to make HTTP calls using the current data it possesses as the URL. The `aiohttp <https://docs.aiohttp.org/en/stable/>`_ library is used as the engine to perform API calls. Every key word parameter you pass to: ``get()``, ``post()``, ``put()``, ``patch()``, ``delete()`` methods will be directly passed to the request library call. This means you will be using ``params={'myparam': 'paramvalue'}`` to send querystring arguments in the url and ``data={'datakey': 'keyvalue'}`` to send data in the body of the request.

.. code-block:: python

    cli = MyWrapper()
	response = await cli.some_resource().get(params={'myparam': 'paramvalue'})
	response = await cli.some_resource().post(data={'datakey': 'keyvalue'})
	response = await cli.some_resource().delete(data={'id': 123})

For perform multiple requests asynchronously, you can use batch methods as like a ``post_batch()``, ``patch_batch()``, ``put_batch()``, ``delete_batch()``. The data in the list must be passed to the data parameter in order to execute requests.

.. code-block:: python

    cli = MyWrapper()
	response = await cli.some_resource().post_batch(data=[
			{'datakey': 'keyvalue1'},
			{'datakey': 'keyvalue2'},
		])

Auth refreshing (\*)
--------------------

Some clients need to update its token once they have expired. If the client supports this feature, you might
specify ``refresh_token=True`` in the adapter class, instantiate it passing ``refresh_token=True``
or make any HTTP call passing ``refresh_auth=True`` (both default to ``False``).
Note that if your adapter claass or client instance has ``refresh_token=True``, then you don't need to explicitly set it on HTTP calls.


.. code-block:: python

    class MyAPIAdapter(TapiocaAdapter):
        refresh_token=True
        ...

    MyWrapper = generate_wrapper_from_adapter(MyAPIAdapter)

    # or

    cli = MyWrapper(refresh_token=True)
	    ...

    # or

    cli = MyWrapper()
    response = await cli.some_resource().post(refresh_token=True)
    ...

*the wrapper you are current using may not support this feature

Pagination (\*)
---------------

Use ``pages()`` method to call an endpoint that returns a collection of objects in batches. This will make your client automatically fetch more data untill there is none more left. You may use ``max_pages`` and/or ``max_items`` to limit the number of items you want to iterate over.

.. code-block:: python

    cli = MyWrapper():

    response = await cli.some_resource().get(params=...)

    async for page in response().pages():
    	print(page.data())
    	print(page.response)
    	...

	# or

	async for page in response().pages(max_pages=2):
		...

	# or

	async for page in response().pages(max_items=10):
		...

	# or

	async for page in response().pages(max_pages=2, max_items=10):
		...


*the wrapper you are current using may not support this feature


Open docs (\*)
--------------

When accessing an endpoint, you may want to read it's documentation in the internet. By calling ``open_docs()`` in a python interactive session, the doc page will be openned in a browser.

.. code-block:: python

    cli = MyWrapper()
    cli.some_resource.open_docs()

*the wrapper you are current using may not support this feature

Open in the browser (\*)
------------------------

Whenever the data contained in the executor is a URL, you can directly open it in the browser from an interactive session by calling ``open_in_browser()``

.. code-block:: python

    cli = MyWrapper()
    response = await cli.some_resource().get()
    response.data.url.open_in_browser()

*the wrapper you are current using may not support this feature

Exceptions
==========

AioTapioca built in exceptions will help you to beautifuly catch and handle whenever there is a client or server error. Make sure the wrapper you are using correctly raises exceptions, the developer might not have treated this. Please refer to the :doc:`exceptions <exceptions>` for more information about exceptions.

Serializers
===========

Serializers will help you processing data before it is sent to the endpoint and transforming data from responses into python objects. Please refer to the :doc:`serializers <serializers>` for more information about serializers.
