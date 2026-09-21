import importlib.util
import json
from pathlib import Path
import sys
import hashlib
from contextlib import asynccontextmanager

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

_root = Path(__file__).resolve().parents[1]
_namespace = "_clipit_gateway_" + hashlib.sha256(str(_root).encode()).hexdigest()[:12]
if _namespace not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_namespace, _root / "clipit_plugin" / "__init__.py",
                                                  submodule_search_locations=[str(_root / "clipit_plugin")])
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_namespace] = _module
    _spec.loader.exec_module(_module)
_client = importlib.import_module(_namespace + ".client")
_runtime_module = importlib.import_module(_namespace + ".runtime")
runtime = _runtime_module.Runtime()
@asynccontextmanager
async def lifespan(_app):
    try:
        yield
    finally:
        runtime.reset()


router = APIRouter(lifespan=lifespan)


def _response(value, status=200):
    return JSONResponse(value, status_code=status, headers={"Cache-Control": "private, no-store"})


@router.get("/status")
async def status():
    try:
        return _response(await run_in_threadpool(runtime.status))
    except _client.ClipItError as exc:
        return _response(exc.public(), exc.status)


@router.get("/doctor")
async def doctor():
    return _response(await run_in_threadpool(runtime.doctor))


@router.post("/operations/{operation}")
async def operation_call(operation: str, request: Request):
    try:
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            raise _client.ClipItError("INVALID_INPUT", "Use application/json.", 415)
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > _client.MAX_REQUEST_BYTES:
                raise _client.ClipItError("REQUEST_TOO_LARGE", "Request exceeds the 64 KiB limit.", 413)
            chunks.append(chunk)
        try:
            arguments = json.loads(b"".join(chunks))
        except (ValueError, UnicodeError):
            raise _client.ClipItError("INVALID_INPUT", "Invalid JSON request.") from None
        if not isinstance(arguments, dict):
            raise _client.ClipItError("INVALID_INPUT", "Request must be an object.")
        connection_id = arguments.pop("connectionId", None)
        if not isinstance(connection_id, str) or len(connection_id) != 64:
            raise _client.ClipItError("CONNECTION_REQUIRED", "Refresh the connection before using ClipIt.", 409)
        _client.operation_request(operation, arguments)
        try:
            value = await run_in_threadpool(runtime.call, operation, arguments,
                                           media=operation in {"upload_create", "upload_parts", "download"}, connection_id=connection_id)
        except _client.ClipItError as exc:
            return _response(exc.public())
        return _response(value)
    except _client.ClipItError as exc:
        return _response(exc.public(), exc.status)
