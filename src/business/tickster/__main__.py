import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uvicorn

from dotenv import load_dotenv
load_dotenv()

from ngrok_service import connect_tunnel
from tickster.versioning import discover_api_versions, get_latest_version, get_stable_version, VersionRouter, chain, matches_version


app = FastAPI(title="Upstox Connector", version="0.1.0")

VERSIONS = discover_api_versions()
VERSION_ROUTERS = {v.version: v for v in VERSIONS}


class VersionFallbackMiddleware(BaseHTTPMiddleware):
    """Fallback to the previous API version only when no endpoint exists."""

    async def dispatch(self, request: Request, call_next):
        original_path = request.scope["path"]
        segments = original_path.strip("/").split("/", 1)
        requested_version = segments[0] if segments and segments[0] in VERSION_ROUTERS else None

        if requested_version is None:
            # Default handler, in case no versioning has been done.
            return await call_next(request)

        relative_path = "/" + segments[1] if len(segments) == 2 else "/"
        current = VERSION_ROUTERS[requested_version]

        for candidate in chain(current):
            candidate_scope = dict(request.scope)
            candidate_scope["path"] = f"/{candidate.version}{relative_path}"
            candidate_scope["raw_path"] = candidate_scope["path"].encode("utf-8")

            # Test against the candidate router using the path *inside* that version.
            route_scope = dict(request.scope)
            route_scope["path"] = relative_path
            if matches_version(route_scope, candidate):
                request.scope.update(candidate_scope)
                return await call_next(request)

        return await call_next(request)


app.add_middleware(VersionFallbackMiddleware)


def _redirect_to_version(version: str, path: str) -> RedirectResponse:
    suffix = f"/{path}" if path else ""
    return RedirectResponse(url=f"/{version}{suffix}", status_code=307)


@app.api_route(
    "/latest/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def latest(path: str):
    version = get_latest_version(VERSIONS).version
    return _redirect_to_version(version, path)


@app.api_route(
    "/stable/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def stable(path: str):
    version = get_stable_version(VERSIONS).version
    return _redirect_to_version(version, path)


# Normal FastAPI routers retain validation, dependencies, response models, etc.
for version in VERSIONS:
    app.include_router(version.router, prefix=f"/{version.version}", tags=[version.version])


def main():
    host = os.getenv("upstox_connector.host", "0.0.0.0")
    port = int(os.getenv("upstox_connector.port", 8000))

    if os.getenv("ENVIRONMENT") == "local":
        connect_tunnel(
            auth_token=os.getenv("upstox_connector.ngrok_token", None), 
            address=port,
            endpoint=os.getenv("upstox_connector.ngrok_end_point", None), 
        )

    uvicorn.run("upstox_connector.__main__:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    main()
