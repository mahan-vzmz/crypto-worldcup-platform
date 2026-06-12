"""Shared HTTP plumbing for all API clients.

Owns session reuse, explicit timeouts, exponential-backoff retries, and
the translation of every ``requests`` exception into ``APIError`` so
nothing from the HTTP layer leaks upward (boundary rule).
"""

from types import TracebackType
from typing import Any, Self

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)

#: (connect timeout, read timeout) in seconds. Connect fails fast on an
#: unreachable host; read tolerates a slow-but-alive server.
DEFAULT_TIMEOUT: tuple[float, float] = (5.0, 15.0)

#: HTTP statuses worth retrying: rate limit and transient server errors.
RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class BaseAPIClient:
    """Base class for external API adapters.

    Subclasses call :meth:`get_json` and are responsible for validating
    the payload shape and mapping it into domain models (the
    anti-corruption layer).
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        if headers:
            self._session.headers.update(headers)

        retry_policy = Retry(
            total=max_retries,
            backoff_factor=0.5,  # waits: 0.5s, 1s, 2s, ...
            status_forcelist=RETRY_STATUSES,
            allowed_methods=frozenset({"GET"}),  # idempotent only
        )
        adapter = HTTPAdapter(max_retries=retry_policy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        """GET ``base_url + path`` and return the parsed JSON body.

        Raises:
            APIError: on timeout, connection failure, HTTP error status,
                or a body that is not valid JSON.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        logger.debug("GET %s", url)  # never log params/headers: secrets
        try:
            response = self._session.get(
                url, params=params, timeout=self._timeout
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise APIError(f"request to {url} timed out") from exc
        except requests.HTTPError as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else "unknown"
            )
            raise APIError(
                f"request to {url} failed with HTTP status {status}"
            ) from exc
        except requests.RequestException as exc:
            raise APIError(f"could not connect to {url}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise APIError(f"response from {url} is not valid JSON") from exc

    def close(self) -> None:
        """Release pooled connections."""
        self._session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()