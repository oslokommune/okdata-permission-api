import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from logging_middleware import add_logging_middleware
from resources import permissions, my_permissions, webhook_tokens
from resources.errors import ErrorResponse

root_path = os.environ.get("ROOT_PATH", "")
app = FastAPI(
    title="Okdata Permission API",
    description="API for managing permissions to okdata resources such as datasets",
    version="0.1.0",
    root_path=root_path,
)

add_logging_middleware(app, "okdata-permission-api")

app.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["permissions"],
)

app.include_router(
    my_permissions.router,
    prefix="/my_permissions",
    tags=["permissions"],
)

app.include_router(webhook_tokens.router, prefix="/webhooks", tags=["webhooks"])


@app.exception_handler(ErrorResponse)
def abort_exception_handler(request: Request, exc: ErrorResponse):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
def abort_validation_error(request: Request, exc):
    errors = exc.errors()
    # Exclude python-specific
    # e.g. 'ctx': {'enum_values': [<WebhookTokenOperation.READ: 'read'>, <WebhookTokenOperation.WRITE: 'write'>]}
    for error in errors:
        error.pop("ctx", None)
        error.pop("type", None)
    return JSONResponse(
        status_code=400,
        content={"message": "Bad Request", "errors": errors},
    )
