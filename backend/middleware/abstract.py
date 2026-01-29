import abc

from starlette.types import ASGIApp, Receive, Scope, Send


class ASGIMiddleware(abc.ABC):
    """
    Base class for ASGI middleware implementations.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @abc.abstractmethod
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The main entry point for the ASGI middleware.

        Parameters
        ----------
        scope : Scope
            The ASGI scope, essentially the request context.
        receive : Receive
            The ASGI receive callable, essentially the request body stream.
        send : Send
            The ASGI send callable, essentially the response body stream.
        """
