class ResponseProcessException(Exception):
    def __init__(self, tapioca_exception, data, *args, **kwargs):
        self.tapioca_exception = tapioca_exception
        self.data = data
        super().__init__(*args, **kwargs)


class TapiocaException(Exception):
    def __init__(self, message, client):
        self.status = None
        self.client = client
        if client is not None:
            self.status = client().status

        if not message:
            message = "response status code: {}".format(self.status)
        super().__init__(message)


class ClientError(TapiocaException):
    def __init__(self, message="", client=None):
        super().__init__(message, client=client)


class ServerError(TapiocaException):
    def __init__(self, message="", client=None):
        super().__init__(message, client=client)
