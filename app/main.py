from pathlib import Path
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.dashboard import router as dashboard_router
from app.core.logging_config import configure_logging
from app.core.request_context import set_request_id


configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="Salesforce TV Dashboard", version="1.0.0")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)

    started_at = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "event=http_request method=%s path=%s status=%s elapsed_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


app.include_router(dashboard_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path("app/static/index.html"))


@app.get("/logo_laranja.png")
def logo() -> FileResponse:
    return FileResponse(Path("logo_laranja.png"))
