import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from misc import healthcheck
from process import process_endpoint

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(healthcheck.router)
app.include_router(process_endpoint.router)

def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0")


if __name__ == "__main__":
    main()
