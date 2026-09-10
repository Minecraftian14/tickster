import inspect, os, re

from functools import wraps

from dataclasses import dataclass

from fastapi import APIRouter
from starlette.routing import Match

import importlib
import pkgutil


@dataclass(frozen=True)
class VersionRouter:
    version: str
    router: APIRouter
    previous: "VersionRouter | None" = None


def discover_api_versions():
    api_versions = []

    from upstox_connector import api
    for module in pkgutil.iter_modules(api.__path__):
        name = module.name

        # If it is some other module
        if not name.startswith("v"): continue
        if not name[1:].isdigit(): continue

        # If it is an invalid version
        module_routes = f"{api.__name__}.{name}.routes"
        if importlib.util.find_spec(module_routes) is None: continue
        router = getattr(importlib.import_module(module_routes), "router", None)
        if router is None: continue

        api_versions.append((int(name[1:]), router))
    
    api_versions.sort()

    previous = None
    for i in range(len(api_versions)):
        version, router = api_versions[i]
        api_versions[i] = VersionRouter(f"v{version}", router, previous)
        previous = api_versions[i]

    return api_versions


def get_latest_version(api_versions):
    return api_versions[-1]


def get_stable_version(api_versions):
    version_idx = int(os.getenv("upstox_connector.stable")[1:]) - 1
    return api_versions[version_idx]


def chain(version: VersionRouter):
    current: VersionRouter | None = version
    while current is not None:
        yield current
        current = current.previous


def matches_version(scope: dict, version: VersionRouter) -> bool:
    """Return whether the requested path/method has an endpoint in this version."""
    for route in version.router.routes:
        if not hasattr(route, "matches"):
            continue
        match, _ = route.matches(scope)
        if match is Match.FULL:
            return True
    return False


def add_api_version(function):
    match = re.search(r"\.api\.v(\d+).", function.__module__)
    version = "v1" if match is None else f"v{match[1]}" 

    def inject_attribute(response):
        if hasattr(response, "api_version"): response.api_version = version
        elif hasattr(response, "__setitem__"): response["api_version"] = version
        return response

    if inspect.iscoroutinefunction(function):
        @wraps(function)
        async def intercept(*args, **kwargs):
            return inject_attribute(await function(*args, **kwargs))

    else:
        @wraps(function)
        def intercept(*args, **kwargs):
            return inject_attribute(function(*args, **kwargs))

    return intercept
