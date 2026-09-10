from pydantic import BaseModel


class HelloResponse(BaseModel):
    api_version: str
    message: str

