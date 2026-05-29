from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit
import json as jsonlib

import requests

from .auth_cli import sign_request
from .key_registry import HMACKeyRegistry


class CPOSClientError(RuntimeError):
    pass


def _read_secret_file(path: str) -> str:
    try:
        secret = open(path, encoding="utf-8").read().strip()
    except OSError as exc:
        raise CPOSClientError(f"secret_file_unreadable: {exc}") from exc
    if not secret:
        raise CPOSClientError("secret_file_empty")
    return secret


@dataclass(frozen=True)
class CPOSAuthConfig:
    secret_file: str | None = None
    registry_file: str | None = None
    key_id: str | None = None
    agent_id: str = "CPOSClient"

    def resolve_secret(self) -> tuple[str, str | None]:
        if self.registry_file:
            if not self.key_id:
                raise CPOSClientError("key_id_required_with_registry")
            record = HMACKeyRegistry(self.registry_file).get(self.key_id)
            if record is None:
                raise CPOSClientError("key_not_found")
            usable, reason = record.is_usable()
            if not usable:
                raise CPOSClientError(reason)
            return _read_secret_file(record.secret_file), record.key_id
        if not self.secret_file:
            raise CPOSClientError("secret_file_required")
        return _read_secret_file(self.secret_file), self.key_id


class CPOSClient:
    """Small signed HTTP client for CPOS Engine-Zero APIs.

    Secrets are read from runtime secret files or a non-secret key registry that
    points to runtime secret files. Secrets are never logged or returned.
    """

    def __init__(
        self,
        base_url: str,
        *,
        secret_file: str | None = None,
        registry_file: str | None = None,
        key_id: str | None = None,
        agent_id: str = "CPOSClient",
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ):
        if not base_url.startswith("https://"):
            raise CPOSClientError("https_required")
        self.base_url = base_url.rstrip("/") + "/"
        self.auth = CPOSAuthConfig(secret_file=secret_file, registry_file=registry_file, key_id=key_id, agent_id=agent_id)
        self.timeout = timeout
        self.session = session or requests.Session()

    def signed_headers(self, method: str, path: str, *, body: bytes = b"", query_string: str | None = None, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        secret, key_id = self.auth.resolve_secret()
        parsed = urlsplit(path)
        sign_path = parsed.path or path
        sign_query = parsed.query if query_string is None else query_string
        headers = sign_request(method=method, path=sign_path, query_string=sign_query, body=body, secret=secret)
        if key_id:
            headers["X-CPOS-Key-Id"] = key_id
        headers["X-Agent-Id"] = self.auth.agent_id
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def request(self, method: str, path: str, *, json: Any | None = None, data: bytes | str | None = None, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> requests.Response:
        method = method.upper()
        if json is not None and data is not None:
            raise CPOSClientError("json_and_data_are_mutually_exclusive")
        body = b""
        request_headers = dict(headers or {})
        if json is not None:
            body = jsonlib.dumps(json, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif data is not None:
            body = data.encode("utf-8") if isinstance(data, str) else data

        relative = path.lstrip("/")
        url = urljoin(self.base_url, relative)
        parsed_url = urlsplit(url)
        query_string = parsed_url.query
        if params:
            # Let requests encode params. Because the server signs request.query_string,
            # callers needing params should include them in path for exact signing.
            raise CPOSClientError("params_not_supported_for_signed_requests_use_query_in_path")
        signed = self.signed_headers(method, parsed_url.path, body=body, query_string=query_string, extra_headers=request_headers)
        return self.session.request(method, url, data=body if body else None, headers=signed, timeout=self.timeout)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def get_json(self, path: str, **kwargs: Any) -> Any:
        response = self.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, payload: Any, **kwargs: Any) -> Any:
        response = self.post(path, json=payload, **kwargs)
        response.raise_for_status()
        return response.json()
