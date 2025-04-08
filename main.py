import uvicorn
from fastapi import FastAPI
from misc import healthcheck
from process import process_endpoint

app = FastAPI()
app.include_router(healthcheck.router)
app.include_router(process_endpoint.router)

def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0")


if __name__ == "__main__":
    main()
