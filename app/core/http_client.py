import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import get_settings


def build_retry_session() -> requests.Session:
    settings = get_settings()

    retry = Retry(
        total=settings.SF_HTTP_RETRY_TOTAL,
        connect=settings.SF_HTTP_RETRY_TOTAL,
        read=settings.SF_HTTP_RETRY_TOTAL,
        backoff_factor=settings.SF_HTTP_RETRY_BACKOFF_SECONDS,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
