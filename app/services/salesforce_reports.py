import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import get_settings
from app.core.http_client import build_retry_session
from app.services.salesforce_auth import SalesforceAuthError, SalesforceJWTAuthClient


logger = logging.getLogger(__name__)


class SalesforceReportError(Exception):
    pass


class SalesforceReportService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.auth_client = SalesforceJWTAuthClient()
        self.session = build_retry_session()

        self._cache_lock = threading.Lock()
        self._refresh_lock = threading.Lock()
        self._refresh_in_progress = False

        self._cache_expires_at = 0.0
        self._cache_payload: dict[str, Any] | None = None
        self._last_success_payload: dict[str, Any] | None = None
        self._last_success_at: str | None = None

        self.report_map = {
            "ATENDIMENTO TRANSPORTADORA": self.settings.SF_REPORT_1_ID,
            "ATENDIMENTO NO CLIENTE": self.settings.SF_REPORT_2_ID,
            "ATENDIMENTOS DO DIA": self.settings.SF_REPORT_3_ID,
        }

    def _report_url(self, instance_url: str, report_id: str) -> str:
        return (
            f"{instance_url}/services/data/{self.settings.SF_API_VERSION}"
            f"/analytics/reports/{report_id}?includeDetails=true"
        )

    @staticmethod
    def _extract_rows(report_payload: dict[str, Any]) -> list[dict[str, Any]]:
        report_meta = report_payload.get("reportMetadata", {})
        report_extended_meta = report_payload.get("reportExtendedMetadata", {})
        detail_columns = report_meta.get("detailColumns", [])
        aggregate_columns = report_meta.get("aggregates", [])
        detail_column_info = report_extended_meta.get("detailColumnInfo", {})
        aggregate_column_info = report_extended_meta.get("aggregateColumnInfo", {})

        fact_map = report_payload.get("factMap", {})
        rows: list[dict[str, Any]] = []
        has_detail_rows = False

        # Handles tabular reports and summary/matrix with row details.
        for value in fact_map.values():
            for row in value.get("rows", []):
                has_detail_rows = True
                cells = row.get("dataCells", [])
                item: dict[str, Any] = {}

                for index, column_name in enumerate(detail_columns):
                    label = detail_column_info.get(column_name, {}).get("label", column_name)
                    cell_value = cells[index].get("label") if index < len(cells) else ""
                    item[label] = cell_value

                if item:
                    rows.append(item)

        if has_detail_rows:
            return rows

        # Fallback for summary/matrix aggregate-only reports.
        for key, value in fact_map.items():
            aggregates = value.get("aggregates", [])
            if not aggregates:
                continue

            item: dict[str, Any] = {"Grupo": key}
            for index, aggregate in enumerate(aggregates):
                column_id = (
                    aggregate_columns[index]
                    if index < len(aggregate_columns)
                    else aggregate.get("name") or f"aggregate_{index + 1}"
                )
                label = aggregate_column_info.get(column_id, {}).get("label", column_id)
                item[label] = aggregate.get("label") or aggregate.get("value")

            rows.append(item)

        return rows

    def fetch_report(self, label: str, report_id: str) -> dict[str, Any]:
        try:
            access_token, instance_url = self.auth_client.get_valid_token()
        except SalesforceAuthError as exc:
            raise SalesforceReportError(str(exc)) from exc

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        logger.info("event=sf_report_fetch_start report_id=%s title=%s", report_id, label)

        try:
            response = self.session.get(
                self._report_url(instance_url, report_id),
                headers=headers,
                timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.exception("event=sf_report_network_error report_id=%s", report_id)
            raise SalesforceReportError(f"Falha de rede ao buscar relatorio {report_id}: {exc}") from exc

        if response.status_code == 401:
            logger.warning("event=sf_report_token_expired report_id=%s", report_id)
            access_token, instance_url, _ = self.auth_client.authenticate()
            headers["Authorization"] = f"Bearer {access_token}"
            response = self.session.get(
                self._report_url(instance_url, report_id),
                headers=headers,
                timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
            )

        if response.status_code != 200:
            logger.error("event=sf_report_failed report_id=%s status=%s", report_id, response.status_code)
            raise SalesforceReportError(
                f"Erro ao consultar relatorio {report_id} [{response.status_code}]: {response.text}"
            )

        payload = response.json()
        rows = self._extract_rows(payload)
        return {
            "title": label,
            "reportId": report_id,
            "reportType": payload.get("reportMetadata", {}).get("reportFormat"),
            "totalRows": len(rows),
            "rows": rows,
        }

    @staticmethod
    def _build_alias_payload(columns: list[dict[str, Any]], generated_at_iso: str, refresh_seconds: int) -> dict[str, Any]:
        by_title = {item.get("title"): item.get("rows", []) for item in columns}
        generated_dt = datetime.fromisoformat(generated_at_iso.replace("Z", "+00:00"))
        return {
            "transportadora": by_title.get("ATENDIMENTO TRANSPORTADORA", []),
            "cliente": by_title.get("ATENDIMENTO NO CLIENTE", []),
            "dia": by_title.get("ATENDIMENTOS DO DIA", []),
            "last_update": generated_dt.strftime("%H:%M:%S"),
            "refresh_seconds": refresh_seconds,
        }

    def _build_payload(self) -> dict[str, Any]:
        columns: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        generated_at = datetime.now(timezone.utc).isoformat()

        for label, report_id in self.report_map.items():
            try:
                columns.append(self.fetch_report(label, report_id))
            except SalesforceReportError as exc:
                logger.exception("event=sf_report_exception report_id=%s", report_id)
                errors.append({
                    "title": label,
                    "reportId": report_id,
                    "error": str(exc),
                })

        payload = {
            "generatedAt": generated_at,
            "refreshSeconds": self.settings.REFRESH_DEFAULT_SECONDS,
            "columns": columns,
            "errors": errors,
            "salesforceStatus": "ok" if not errors else "degraded",
            "status": "ok" if not errors else "degraded",
            "last_successful_update": self._last_success_at,
            "error": "" if not errors else "Salesforce unavailable",
            "message": "",
        }

        payload.update(
            self._build_alias_payload(
                columns,
                generated_at,
                self.settings.REFRESH_DEFAULT_SECONDS,
            )
        )
        return payload

    def _refresh_cache_now(self) -> None:
        payload = self._build_payload()

        if payload.get("columns"):
            with self._cache_lock:
                self._cache_payload = payload
                self._cache_expires_at = time.time() + self.settings.SF_REPORT_CACHE_SECONDS
                self._last_success_payload = payload
                self._last_success_at = payload.get("last_update")
            return

        if self._last_success_payload:
            fallback_payload = dict(self._last_success_payload)
            fallback_payload["salesforceStatus"] = "unavailable"
            fallback_payload["status"] = "degraded"
            fallback_payload["error"] = "Salesforce unavailable"
            fallback_payload["message"] = (
                "Salesforce indisponivel. Ultima atualizacao valida: "
                f"{self._last_success_at or '--:--:--'}"
            )
            fallback_payload["errors"] = payload.get("errors", [])
            fallback_payload["last_successful_update"] = self._last_success_at

            with self._cache_lock:
                self._cache_payload = fallback_payload
                self._cache_expires_at = time.time() + max(15, int(self.settings.SF_REPORT_CACHE_SECONDS / 4))
            return

        payload["salesforceStatus"] = "unavailable"
        payload["status"] = "degraded"
        payload["error"] = "Salesforce unavailable"
        payload["message"] = "Salesforce indisponivel e sem cache valido ainda"
        payload["last_successful_update"] = None

        with self._cache_lock:
            self._cache_payload = payload
            self._cache_expires_at = time.time() + 15

    def _trigger_background_refresh_if_needed(self) -> None:
        with self._refresh_lock:
            if self._refresh_in_progress:
                return
            self._refresh_in_progress = True

        def worker() -> None:
            try:
                self._refresh_cache_now()
            finally:
                with self._refresh_lock:
                    self._refresh_in_progress = False

        threading.Thread(target=worker, daemon=True).start()

    def fetch_all_reports(self) -> dict[str, Any]:
        now = time.time()
        cached_payload: dict[str, Any] | None = None
        cache_fresh = False

        with self._cache_lock:
            if self._cache_payload:
                cached_payload = dict(self._cache_payload)
                cache_fresh = now < self._cache_expires_at

        if cache_fresh and cached_payload:
            cached_payload["dataSource"] = "cache"
            return cached_payload

        if cached_payload:
            self._trigger_background_refresh_if_needed()
            cached_payload["dataSource"] = "stale-cache"
            return cached_payload

        self._refresh_cache_now()
        with self._cache_lock:
            cold_start_payload = dict(self._cache_payload or {})
        cold_start_payload["dataSource"] = "live"
        return cold_start_payload
