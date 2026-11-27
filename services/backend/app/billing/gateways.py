"""Billing providers. Stripe for the web, RevenueCat for Apple and Google purchases, and a local stand-in
for development. HTTP uses the standard library so no SDK is needed; tests replace `send`."""

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from app.api.errors import ApiError

Sender = Callable[[str, str, dict[str, str], bytes | None], dict[str, Any]]


def http_send(method: str, url: str, headers: dict[str, str], body: bytes | None) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310 (https only)
    if not url.startswith("https://"):
        raise ApiError(502, "billing_provider_error", "The billing provider URL must use HTTPS.")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:  # noqa: S310
            data: dict[str, Any] = json.loads(res.read() or b"{}")
            return data
    except urllib.error.HTTPError as e:
        raise ApiError(
            502, "billing_provider_error", "The payment provider couldn't complete this. Please try again."
        ) from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ApiError(
            502, "billing_provider_error", "We couldn't reach the payment provider. Please try again."
        ) from e


def _flatten(prefix: str, value: Any, out: list[tuple[str, str]]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}[{k}]" if prefix else k, v, out)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _flatten(f"{prefix}[{i}]", v, out)
    elif isinstance(value, bool):
        out.append((prefix, "true" if value else "false"))
    else:
        out.append((prefix, str(value)))


def form_encode(data: dict[str, Any]) -> bytes:
    """Stripe's form encoding for nested objects: line_items[0][price]=..."""
    out: list[tuple[str, str]] = []
    _flatten("", data, out)
    return urllib.parse.urlencode(out).encode()


class StripeClient:
    def __init__(self, secret_key: str, api_base: str, send: Sender = http_send) -> None:
        self.secret_key, self.api_base, self.send = secret_key, api_base.rstrip("/"), send

    def post(self, path: str, data: dict[str, Any], idempotency_key: str | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return self.send("POST", f"{self.api_base}{path}", headers, form_encode(data))

    def checkout_session(
        self,
        *,
        user_id: str,
        plan_id: str,
        price_id: str,
        customer_id: str | None,
        success_url: str,
        cancel_url: str,
    ) -> str:
        data: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "client_reference_id": user_id,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": False,
            "metadata": {"user_id": user_id, "plan_id": plan_id},
            "subscription_data": {"metadata": {"user_id": user_id, "plan_id": plan_id}},
        }
        if customer_id:
            data["customer"] = customer_id
        res = self.post("/v1/checkout/sessions", data)
        return str(res["url"])

    def portal_session(self, *, customer_id: str, return_url: str) -> str:
        res = self.post("/v1/billing_portal/sessions", {"customer": customer_id, "return_url": return_url})
        return str(res["url"])


class RevenueCatClient:
    def __init__(self, api_key: str, api_base: str, send: Sender = http_send) -> None:
        self.api_key, self.api_base, self.send = api_key, api_base.rstrip("/"), send

    def subscriber(self, app_user_id: str) -> dict[str, Any]:
        url = f"{self.api_base}/v1/subscribers/{urllib.parse.quote(app_user_id, safe='')}"
        return self.send("GET", url, {"Authorization": f"Bearer {self.api_key}"}, None)
