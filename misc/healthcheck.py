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
    summary="Kiểm tra sức khỏe server",
    response_description="Trả 200 (OK) nếu còn sống",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
def get_health() -> HealthCheck:
    return health_status
