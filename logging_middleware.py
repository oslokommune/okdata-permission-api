from okdata.aws.logging import logging_wrapper
from starlette.middleware.base import BaseHTTPMiddleware


def _logging_middleware(request, call_next):
    @logging_wrapper("okdata-permission-api", async_wrapper=True)
    async def handler(event, context):
        return await call_next(request)

    return handler(request.scope.get("aws.event", {}), request.scope.get("aws.context"))


def add_logging_middleware(app, service_name):
    app.add_middleware(BaseHTTPMiddleware, dispatch=_logging_middleware)
