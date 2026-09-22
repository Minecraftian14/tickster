from fastapi import APIRouter

from tickster.models import HelloResponse


router = APIRouter()


@router.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    return HelloResponse(api_version="v3", message="Hello from API v3")


# /users/{user_id} is deliberately absent in v3 for this demo.
# The version fallback will route that endpoint through v2 -> v1.
