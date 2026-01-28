import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import verify_webhook_secret
from app.models.agent_task import Source
from app.normalizers.registry import get_normalizer

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_webhook_secret)])


@router.post("/webhooks/sonar", status_code=202)
async def sonar_webhook(request: Request, payload: dict[str, Any]) -> JSONResponse:
    try:
        task = get_normalizer(Source.SONARCLOUD).normalize(payload)
    except Exception as exc:
        logger.warning("Failed to normalize SonarCloud payload", extra={"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        await request.app.state.publisher.publish(
            task.model_dump_json().encode()
        )
    except Exception as exc:
        logger.error("Failed to publish message", extra={"error": str(exc)})
        raise HTTPException(status_code=503, detail="Failed to publish message")

    return JSONResponse(
        status_code=202, content={"task_id": str(task.task_id)}
    )
