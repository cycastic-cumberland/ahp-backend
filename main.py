import uvicorn
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from misc import healthcheck
from process import process_endpoint
from typing import Callable, Awaitable

ORIGINS = ["http://localhost:8001"]
app = FastAPI()

app.include_router(healthcheck.router)
app.include_router(process_endpoint.router)

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
