import hmac

from fastapi import Header, HTTPException

from app.config import settings


async def verify_webhook_secret(
    x_webhook_secret: str = Header(...),
) -> None:
    if not hmac.compare_digest(x_webhook_secret, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
