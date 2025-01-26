from __future__ import annotations

from typing import Any, Literal, overload

from httpx import AsyncClient
from msgspec.json import Decoder as JsonDecoder
from msgspec.json import Encoder as JsonEncoder

from jkit.config import CONFIG

JSON_ENCODER = JsonEncoder()
JSON_DECODER = JsonDecoder()

DatasourceType = Literal["JIANSHU", "JPEP"]

DATASOURCE_CLIENTS: dict[DatasourceType, AsyncClient] = {
    "JIANSHU": CONFIG.datasources.jianshu._get_httpx_client(),
    "JPEP": CONFIG.datasources.jpep._get_httpx_client(),
}


@overload
async def send_request(
    *,
    datasource: Literal["JIANSHU", "JPEP"],
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    cookies: dict[str, str] | None = None,
    response_type: Literal["JSON"],
) -> dict[str, Any]: ...


@overload
async def send_request(
    *,
    datasource: Literal["JIANSHU", "JPEP"],
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    cookies: dict[str, str] | None = None,
    response_type: Literal["JSON_LIST"],
) -> list[dict[str, Any]]: ...


@overload
async def send_request(
    *,
    datasource: Literal["JIANSHU", "JPEP"],
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    cookies: dict[str, str] | None = None,
    response_type: Literal["HTML"],
) -> str: ...


async def send_request(  # noqa: PLR0913
    *,
    datasource: Literal["JIANSHU", "JPEP"],
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    cookies: dict[str, str] | None = None,
    response_type: Literal["JSON", "JSON_LIST", "HTML"],
) -> dict[str, Any] | list[dict[str, Any]] | str:
    client = DATASOURCE_CLIENTS[datasource]

    response = await client.request(
        method=method,
        url=path,
        params=params,
        content=JSON_ENCODER.encode(body) if body else None,
        headers={
            "Accpet": "text/html" if response_type == "HTML" else "application/json"
        },
        cookies=cookies,
    )

    response.raise_for_status()

    # TODO: JIANSHU 数据源 HTTP 502 -> RateLimitError

    if response_type == "HTML":
        return response.text
    else:  # noqa: RET505
        return JSON_DECODER.decode(response.content)
