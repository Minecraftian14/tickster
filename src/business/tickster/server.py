import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uvicorn

from dotenv import load_dotenv
load_dotenv()

from ngrok_service import connect_tunnel
from tickster.api_version_mechanism import (
    VersionRouter,
    discover_api_versions,
    get_latest_version,
    get_stable_version,
    chain,
    matches_version,
    VersionFallbackMiddleware,
)


class ServerControls:
    def __init__(self):
        self.app = FastAPI(title="Upstox Connector", version="0.1.0")
        self.api_versions = []

        self.refresh_api_versions()
        self.app.add_middleware(VersionFallbackMiddleware)


    def refresh_api_versions(self):
        self.api_versions = discover_api_versions()
        self.api_routers = {v.version: v for v in VERSIONS}

