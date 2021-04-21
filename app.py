import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from resources import permissions, my_permissions
from resources.errors import ErrorResponse

from pydantic import ValidationError


root_path = os.environ.get("ROOT_PATH", "")
app = FastAPI(
    title="Okdata Permission API",
    description="API for managing permissions to okdata resources such as datasets",
    version="0.1.0",
    root_path=root_path,
)

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


@app.exception_handler(ErrorResponse)
def abort_exception_handler(request: Request, exc: ErrorResponse):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(ValidationError)
def abort_value_error(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"message": "Bad Request", "errors": exc.errors()},
    )
