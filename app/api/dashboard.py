import logging

from fastapi import APIRouter

from app.services.salesforce_reports import SalesforceReportService


router = APIRouter(prefix="/api", tags=["dashboard"])
service = SalesforceReportService()
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    logger.info("event=api_health")
    return {"status": "ok"}


@router.get("/dashboard")
def get_dashboard() -> dict:
    payload = service.fetch_all_reports()
    logger.info(
        "event=api_dashboard status=%s columns=%s errors=%s data_source=%s",
        payload.get("status") or payload.get("salesforceStatus"),
        len(payload.get("columns", [])),
        len(payload.get("errors", [])),
        payload.get("dataSource"),
    )
    return payload
