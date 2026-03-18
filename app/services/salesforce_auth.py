import time
import uuid
import logging
import threading
from pathlib import Path

import jwt
import requests

from app.core.config import get_settings
from app.core.http_client import build_retry_session


logger = logging.getLogger(__name__)


class SalesforceAuthError(Exception):
    pass


class SalesforceJWTAuthClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.session = build_retry_session()
        self._access_token: str | None = None
        self._instance_url: str | None = None
        self._expires_at: float = 0
        self._lock = threading.Lock()

    def _load_private_key(self) -> str:
        key_path = Path(self.settings.SF_PRIVATE_KEY_PATH)
        if not key_path.exists():
            raise SalesforceAuthError(f"Chave privada nao encontrada: {key_path}")
        return key_path.read_text(encoding="utf-8")

    def _build_jwt_assertion(self) -> str:
        private_key = self._load_private_key()
        now = int(time.time())
        payload = {
            "iss": self.settings.SF_CONSUMER_KEY,
            "sub": self.settings.SF_USERNAME,
            "aud": self.settings.SF_LOGIN_URL,
            "exp": now + 300,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    def authenticate(self) -> tuple[str, str, float]:
        assertion = self._build_jwt_assertion()
        token_url = f"{self.settings.SF_LOGIN_URL}/services/oauth2/token"
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "client_id": self.settings.SF_CONSUMER_KEY,
            "client_secret": self.settings.SF_CONSUMER_SECRET,
        }

        logger.info("event=sf_auth_start login_url=%s", self.settings.SF_LOGIN_URL)
        try:
            response = self.session.post(
                token_url,
                data=data,
                timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.exception("event=sf_auth_network_error")
            raise SalesforceAuthError(f"Falha de rede na autenticacao Salesforce: {exc}") from exc

        if response.status_code != 200:
            logger.error("event=sf_auth_failed status=%s", response.status_code)
            raise SalesforceAuthError(
                f"Falha na autenticacao Salesforce [{response.status_code}]: {response.text}"
            )

        payload = response.json()
        self._access_token = payload.get("access_token")
        self._instance_url = payload.get("instance_url")

        if not self._access_token or not self._instance_url:
            raise SalesforceAuthError("Resposta de autenticacao sem access_token ou instance_url")

        expires_in = int(payload.get("expires_in") or self.settings.SF_TOKEN_TTL_SECONDS)
        self._expires_at = time.time() + expires_in
        logger.info("event=sf_auth_success expires_in_seconds=%s", expires_in)
        return self._access_token, self._instance_url, self._expires_at

    def get_valid_token(self) -> tuple[str, str]:
        with self._lock:
            now = time.time()
            renew_boundary = self._expires_at - self.settings.SF_TOKEN_RENEW_SKEW_SECONDS
            if self._access_token and self._instance_url and now < renew_boundary:
                return self._access_token, self._instance_url

            access_token, instance_url, _ = self.authenticate()
            return access_token, instance_url
