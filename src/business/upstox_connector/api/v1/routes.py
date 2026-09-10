from fastapi import APIRouter, HTTPException, Request

from upstox_connector.models import HelloResponse
from upstox_connector.versioning import add_api_version


router = APIRouter()


@router.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    return HelloResponse(api_version="v1", message="Hello from API v1")


@router.get("/ping")
@add_api_version
def ping() -> dict[str, str]:
    return {
        "message": "pong",
        # "api_version": "v1",
    }


@router.post("/upstox/postback")
@add_api_version
async def upstox_webhook(request: Request):
    payload = await request.json()
    print("\nUpstox webhook received:", payload)
    return {"status": "ok"}


@router.post("/upstox/notifier")
@add_api_version
async def upstox_notification(request: Request):
    payload = await request.json()
    print("\nUpstox notification received:", payload)
    return {"status": "ok"}
