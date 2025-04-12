import json

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from misc import healthcheck
from process import process_endpoint
from typing import Callable, Awaitable

ORIGINS = ["http://localhost:8001"]
app = FastAPI()

app.include_router(healthcheck.router)
app.include_router(process_endpoint.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    dumped = ''
    if isinstance(exc.detail, BaseModel):
        dumped = exc.detail.model_dump()
    else:
        dumped = json.dumps(exc.detail)
    response = JSONResponse(dumped, status_code=exc.status_code)
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Origin"] = "*"

    return response



@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    response = await call_next(request)

    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Origin"] = "*"

    return response

def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0")

if __name__ == "__main__":
    main()
