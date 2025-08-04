import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from okdata.aws.logging import add_fastapi_logging
from pydantic import ValidationError

from resources import my_permissions, permissions, resources, teams
from resources.errors import ErrorResponse, error_message_models

root_path = os.environ.get("ROOT_PATH", "")
app = FastAPI(
    title="Okdata Permission API",
    description="API for managing permissions to okdata resources such as datasets",
    version="0.2.0",
    root_path=root_path,
)

add_fastapi_logging(app)

app.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["permissions"],
)

app.include_router(
    resources.router,
    prefix="/permissions",
    tags=["permissions"],
)

app.include_router(
    my_permissions.router,
    prefix="/my_permissions",
    tags=["permissions"],
)

app.include_router(
    teams.router,
    prefix="/teams",
    tags=["teams"],
    responses=error_message_models(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)


@app.exception_handler(ErrorResponse)
def abort_exception_handler(request: Request, exc: ErrorResponse):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
def abort_validation_error(request: Request, exc):
    errors = exc.errors()
    # Exclude python-specific
    # e.g. "ctx": {"enum_values": ["team", "user", "client"]}
    for error in errors:
        error.pop("ctx", None)
        error.pop("type", None)
    return JSONResponse(
        status_code=400,
        content={"message": "Bad Request", "errors": errors},
    )
