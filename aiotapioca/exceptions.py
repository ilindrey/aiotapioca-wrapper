__all__ = ("TapiocaException", "ResponseProcessException", "ClientError", "ServerError")


class TapiocaException(Exception):
    pass


class ResponseProcessException(TapiocaException):
    def __init__(self, message="", data=None, response=None, *args, **kwargs):
        self.message = message
        self.data = data
        self.response = response
        if not self.message and self.response:
            self.message = "Response: {} [{}] {}".format(
                self.response.method.upper(), self.response.status, self.response.url
            )
        super().__init__(*args)


class ClientError(ResponseProcessException):
    pass


class ServerError(ResponseProcessException):
    pass
