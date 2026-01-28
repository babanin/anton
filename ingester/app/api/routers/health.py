from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    publisher = request.app.state.publisher
    rabbitmq_status = "ok" if publisher.is_connected else "degraded"
    return {"status": "ok", "rabbitmq": rabbitmq_status}
