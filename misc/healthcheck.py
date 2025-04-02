from pydantic import BaseModel
from fastapi import APIRouter, status

router = APIRouter()

class HealthCheck(BaseModel):
    status: str = "OK"
    started: bool = True

health_status = HealthCheck(status="OK", started=True)

@router.get(
    "/healthz",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
def get_health() -> HealthCheck:
    return health_status
