from fastapi import APIRouter, HTTPException

from tickster.models import HelloResponse


router = APIRouter()


@router.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    return HelloResponse(api_version="v2", message="Hello from API v2")


@router.get("/echo/{value}")
def echo(value: str) -> dict[str, str]:
    if value == "missing": raise HTTPException(status_code=404, detail="Value not found")
    return {
        "value": value,
        "api_version": "v2",
    }