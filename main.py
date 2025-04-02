import uvicorn
from fastapi import FastAPI
from misc import healthcheck

app = FastAPI()
app.include_router(healthcheck.router)

def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0")


if __name__ == "__main__":
    main()
