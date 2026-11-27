"""Outbound integrations with the network replaced: SMTP email and the payment provider HTTP client."""

import io
import json
import urllib.error
from typing import ClassVar

import pytest

from app.api.errors import ApiError
from app.billing import gateways
from app.core.config import Settings
from app.notifications.email import OutgoingEmail, SmtpEmailSender, make_email_sender


class FakeSMTP:
    instances: ClassVar[list["FakeSMTP"]] = []

    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[tuple] = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.calls.append(("quit",))

    def starttls(self, context):
        self.calls.append(("starttls", context is not None))

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, msg):
        self.calls.append(("send", msg["From"], msg["To"], msg["Subject"], msg.get_content().strip()))


def test_smtp_sender_uses_tls_before_login_and_sends_plain_text(monkeypatch):
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    FakeSMTP.instances.clear()
    s = Settings(
        environment="test",
        email_provider="smtp",
        smtp_host="smtp.example.com",
        smtp_port=2525,
        smtp_username="mailer",
        smtp_password="pw-value",
        email_from="PersonalityDNA <hello@example.com>",
    )
    sender = make_email_sender(s)
    assert isinstance(sender, SmtpEmailSender)
    sender.send(OutgoingEmail(to="ada@example.com", subject="Hi", text="Body text", kind="verify_email"))
    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.example.com", 2525, 10)
    assert [c[0] for c in smtp.calls] == ["starttls", "login", "send", "quit"]
    assert smtp.calls[1] == ("login", "mailer", "pw-value")
    assert smtp.calls[2] == (
        "send",
        "PersonalityDNA <hello@example.com>",
        "ada@example.com",
        "Hi",
        "Body text",
    )

    # Without credentials it still uses TLS and skips login.
    FakeSMTP.instances.clear()
    SmtpEmailSender(s.model_copy(update={"smtp_username": None, "smtp_password": None})).send(
        OutgoingEmail(to="b@example.com", subject="S", text="T", kind="k")
    )
    assert [c[0] for c in FakeSMTP.instances[0].calls] == ["starttls", "send", "quit"]


def test_smtp_sender_needs_a_host():
    with pytest.raises(ValueError, match="SMTP_HOST"):
        SmtpEmailSender(Settings(environment="test", email_provider="outbox"))


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_http_send_https_only_and_friendly_errors(monkeypatch):
    seen = {}

    def ok(req, timeout):
        seen.update(
            url=req.full_url, method=req.get_method(), timeout=timeout, auth=req.get_header("Authorization")
        )
        return FakeResponse(json.dumps({"id": "cs_1"}).encode())

    monkeypatch.setattr("urllib.request.urlopen", ok)
    client = gateways.StripeClient("sk_test_x", "https://api.stripe.com/")
    assert client.post("/v1/checkout/sessions", {"mode": "subscription"}, idempotency_key="k1") == {
        "id": "cs_1"
    }
    assert seen == {
        "url": "https://api.stripe.com/v1/checkout/sessions",
        "method": "POST",
        "timeout": 20,
        "auth": "Bearer sk_test_x",
    }
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: FakeResponse(b""))
    assert gateways.http_send("GET", "https://x.example", {}, None) == {}

    with pytest.raises(ApiError) as e:
        gateways.http_send("GET", "http://api.stripe.com/v1/x", {}, None)
    assert "HTTPS" in e.value.message

    def http_error(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 402, "Payment Required", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr("urllib.request.urlopen", http_error)
    with pytest.raises(ApiError) as e:
        gateways.http_send("POST", "https://api.stripe.com/v1/x", {}, b"")
    assert e.value.status == 502 and "sk_" not in e.value.message

    def unreachable(req, timeout):
        raise urllib.error.URLError("down")

    monkeypatch.setattr("urllib.request.urlopen", unreachable)
    with pytest.raises(ApiError) as e:
        gateways.http_send("POST", "https://api.stripe.com/v1/x", {}, b"")
    assert e.value.status == 502 and "couldn't reach" in e.value.message
